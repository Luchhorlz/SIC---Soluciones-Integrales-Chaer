from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from sic_api.db.session import get_session
from sic_api.modules.addresses.repository import SqlAlchemyAddressRepository
from sic_api.modules.documents.repository import SqlAlchemyDocumentRepository
from sic_api.modules.documents.service import DocumentReadinessService
from sic_api.modules.identity.permissions import ClientPrincipal, ProviderPrincipal
from sic_api.modules.media.repository import DuplicateMediaError, SqlAlchemyMediaRepository
from sic_api.modules.media.storage import ClamAVScanner, FileValidationError, MalwareDetectedError, S3PrivateStorage, StorageUnavailableError
from sic_api.modules.messaging.repository import SqlAlchemyMessagingRepository
from sic_api.modules.notifications.models import NotificationType
from sic_api.modules.notifications.repository import SqlAlchemyNotificationRepository
from sic_api.modules.notifications.service import NotificationService
from sic_api.modules.subscriptions.repository import SqlAlchemySubscriptionRepository
from sic_api.modules.subscriptions.service import SubscriptionVisibilityService
from sic_api.settings import get_settings

from .crypto import AesGcmAddressCipher, AddressEncryptionConfigurationError
from .repository import EngagementConflictError, EngagementNotFoundError, SqlAlchemyEngagementRepository
from .schemas import AttachmentDownloadView, BookingDispute, BookingSchedule, BookingView, QuoteCreate, QuoteDecision, ServiceRequestCreate, ServiceRequestView
from .service import AttachmentInfrastructure, EngagementService
from .state import InvalidTransitionError

client_router = APIRouter(prefix="/v1/client", tags=["client-engagements"])
provider_router = APIRouter(prefix="/v1/provider", tags=["provider-engagements"])
logger = logging.getLogger(__name__)


def workflow(session: AsyncSession) -> EngagementService:
    settings = get_settings()
    cipher = AesGcmAddressCipher(settings.booking_address_encryption_key) if settings.booking_address_encryption_key else None
    return EngagementService(
        SqlAlchemyEngagementRepository(session),
        SqlAlchemyAddressRepository(session),
        DocumentReadinessService(SqlAlchemyDocumentRepository(session)),
        SubscriptionVisibilityService(SqlAlchemySubscriptionRepository(session)),
        cipher=cipher,
        media=SqlAlchemyMediaRepository(session),
        attachments=AttachmentInfrastructure(
            storage=S3PrivateStorage(settings),
            scanner=ClamAVScanner(settings.clamav_host, settings.clamav_port, settings.clamav_timeout_seconds),
            private_bucket=settings.s3_bucket_private,
            max_bytes=settings.document_max_bytes,
            download_ttl_seconds=settings.document_download_ttl_seconds,
        ),
    )


def engagement_error(error: Exception) -> HTTPException:
    if isinstance(error, EngagementNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Private engagement not found")
    if isinstance(error, (FileValidationError, MalwareDetectedError, ValidationError)):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error))
    if isinstance(error, (StorageUnavailableError, AddressEncryptionConfigurationError)):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error))
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


ENGAGEMENT_ERRORS = (
    EngagementConflictError,
    EngagementNotFoundError,
    InvalidTransitionError,
    DuplicateMediaError,
    FileValidationError,
    MalwareDetectedError,
    StorageUnavailableError,
    AddressEncryptionConfigurationError,
    ValidationError,
)


async def notify_provider(session: AsyncSession, view: ServiceRequestView | BookingView, *, notification_type: NotificationType, title: str, body: str, link_path: str, resource_type: str) -> None:
    try:
        await NotificationService(SqlAlchemyNotificationRepository(session)).notify_provider(view.provider_id, type=notification_type, title=title, body=body, link_path=link_path, resource_type=resource_type, resource_id=view.id, email_requested=True)
    except Exception as error:
        await session.rollback()
        logger.warning("provider notification failed", extra={"resource_type": resource_type, "resource_id": str(view.id), "error_type": type(error).__name__})


async def notify_client(session: AsyncSession, view: ServiceRequestView | BookingView, *, notification_type: NotificationType, title: str, body: str, resource_type: str) -> None:
    try:
        await NotificationService(SqlAlchemyNotificationRepository(session)).notify_user(view.client_id, type=notification_type, title=title, body=body, link_path="/cuenta/contrataciones", resource_type=resource_type, resource_id=view.id, email_requested=True)
    except Exception as error:
        await session.rollback()
        logger.warning("client notification failed", extra={"resource_type": resource_type, "resource_id": str(view.id), "error_type": type(error).__name__})


@client_router.get("/service-requests", response_model=list[ServiceRequestView])
async def client_requests(principal: ClientPrincipal, session: AsyncSession = Depends(get_session)) -> list[ServiceRequestView]:
    try:
        return await workflow(session).list_client_requests(principal.user_id)
    except ENGAGEMENT_ERRORS as error:
        raise engagement_error(error) from error


@client_router.post("/service-requests", response_model=ServiceRequestView, status_code=status.HTTP_201_CREATED)
async def create_request(payload: ServiceRequestCreate, principal: ClientPrincipal, session: AsyncSession = Depends(get_session)) -> ServiceRequestView:
    try:
        view = await workflow(session).create_request(principal.user_id, payload)
        try:
            await SqlAlchemyMessagingRepository(session).ensure(view.id, principal.user_id)
        except Exception as error:
            await session.rollback()
            logger.warning("conversation creation failed", extra={"request_id": str(view.id), "error_type": type(error).__name__})
        await notify_provider(session, view, notification_type=NotificationType.REQUEST_RECEIVED, title="Nueva solicitud privada", body="Un cliente solicitó uno de tus servicios visibles.", link_path="/prestador/solicitudes", resource_type="service_request")
        return view
    except ENGAGEMENT_ERRORS as error:
        raise engagement_error(error) from error


@client_router.get("/service-requests/{request_id}", response_model=ServiceRequestView)
async def client_request(request_id: UUID, principal: ClientPrincipal, session: AsyncSession = Depends(get_session)) -> ServiceRequestView:
    try:
        return await workflow(session).get_request(principal.user_id, request_id)
    except ENGAGEMENT_ERRORS as error:
        raise engagement_error(error) from error


@client_router.post("/service-requests/{request_id}/cancel", response_model=ServiceRequestView)
async def cancel_request(request_id: UUID, principal: ClientPrincipal, session: AsyncSession = Depends(get_session)) -> ServiceRequestView:
    try:
        view = await workflow(session).cancel_request(principal.user_id, request_id)
        await notify_provider(session, view, notification_type=NotificationType.REQUEST_UPDATED, title="Solicitud cancelada", body="El cliente canceló una solicitud privada.", link_path="/prestador/solicitudes", resource_type="service_request")
        return view
    except ENGAGEMENT_ERRORS as error:
        raise engagement_error(error) from error


@client_router.post("/service-requests/{request_id}/quotes/accept", response_model=BookingView)
async def accept_quote(request_id: UUID, payload: QuoteDecision, principal: ClientPrincipal, session: AsyncSession = Depends(get_session)) -> BookingView:
    try:
        view = await workflow(session).accept_quote(principal.user_id, request_id, payload)
        await notify_provider(session, view, notification_type=NotificationType.BOOKING_UPDATED, title="Presupuesto aceptado", body="El cliente aceptó tu presupuesto. Confirmá el horario propuesto.", link_path="/prestador/contrataciones", resource_type="booking")
        return view
    except ENGAGEMENT_ERRORS as error:
        raise engagement_error(error) from error


@client_router.post("/service-requests/{request_id}/quotes/{quote_id}/reject", response_model=ServiceRequestView)
async def reject_quote(request_id: UUID, quote_id: UUID, principal: ClientPrincipal, session: AsyncSession = Depends(get_session)) -> ServiceRequestView:
    try:
        view = await workflow(session).reject_quote(principal.user_id, request_id, quote_id)
        await notify_provider(session, view, notification_type=NotificationType.REQUEST_UPDATED, title="Presupuesto rechazado", body="El cliente rechazó el presupuesto enviado.", link_path="/prestador/solicitudes", resource_type="service_request")
        return view
    except ENGAGEMENT_ERRORS as error:
        raise engagement_error(error) from error


@client_router.post("/service-requests/{request_id}/attachments", response_model=ServiceRequestView, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    request_id: UUID,
    file: Annotated[UploadFile, File()],
    principal: ClientPrincipal,
    session: AsyncSession = Depends(get_session),
) -> ServiceRequestView:
    try:
        settings = get_settings()
        content = await file.read(settings.document_max_bytes + 1)
        return await workflow(session).upload_attachment(principal.user_id, request_id, content, file.filename or "attachment", file.content_type)
    except ENGAGEMENT_ERRORS as error:
        raise engagement_error(error) from error
    finally:
        await file.close()


@client_router.get("/service-requests/{request_id}/attachments/{attachment_id}/download-url", response_model=AttachmentDownloadView)
async def client_attachment_download(request_id: UUID, attachment_id: UUID, principal: ClientPrincipal, session: AsyncSession = Depends(get_session)) -> AttachmentDownloadView:
    try:
        return await workflow(session).attachment_download(principal.user_id, request_id, attachment_id)
    except ENGAGEMENT_ERRORS as error:
        raise engagement_error(error) from error


@client_router.get("/bookings", response_model=list[BookingView])
async def client_bookings(principal: ClientPrincipal, session: AsyncSession = Depends(get_session)) -> list[BookingView]:
    try:
        return await workflow(session).list_client_bookings(principal.user_id)
    except ENGAGEMENT_ERRORS as error:
        raise engagement_error(error) from error


@client_router.post("/bookings/{booking_id}/confirm", response_model=BookingView)
async def confirm_booking(booking_id: UUID, principal: ClientPrincipal, session: AsyncSession = Depends(get_session)) -> BookingView:
    try:
        view = await workflow(session).booking_action(principal.user_id, booking_id, "confirm")
        await notify_provider(session, view, notification_type=NotificationType.BOOKING_UPDATED, title="Trabajo confirmado", body="El cliente confirmó la finalización del servicio.", link_path="/prestador/contrataciones", resource_type="booking")
        return view
    except ENGAGEMENT_ERRORS as error:
        raise engagement_error(error) from error


@client_router.post("/bookings/{booking_id}/dispute", response_model=BookingView)
async def dispute_booking(booking_id: UUID, payload: BookingDispute, principal: ClientPrincipal, session: AsyncSession = Depends(get_session)) -> BookingView:
    try:
        view = await workflow(session).booking_action(principal.user_id, booking_id, "dispute", payload)
        await notify_provider(session, view, notification_type=NotificationType.BOOKING_UPDATED, title="Problema reportado", body="El cliente reportó un problema en una contratación.", link_path="/prestador/contrataciones", resource_type="booking")
        return view
    except ENGAGEMENT_ERRORS as error:
        raise engagement_error(error) from error


@client_router.post("/bookings/{booking_id}/cancel", response_model=BookingView)
async def cancel_booking(booking_id: UUID, principal: ClientPrincipal, session: AsyncSession = Depends(get_session)) -> BookingView:
    try:
        view = await workflow(session).booking_action(principal.user_id, booking_id, "cancel")
        await notify_provider(session, view, notification_type=NotificationType.BOOKING_UPDATED, title="Turno cancelado", body="El cliente canceló una contratación.", link_path="/prestador/contrataciones", resource_type="booking")
        return view
    except ENGAGEMENT_ERRORS as error:
        raise engagement_error(error) from error


@provider_router.get("/service-requests", response_model=list[ServiceRequestView])
async def provider_requests(principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> list[ServiceRequestView]:
    try:
        return await workflow(session).list_provider_requests(principal.user_id)
    except ENGAGEMENT_ERRORS as error:
        raise engagement_error(error) from error


@provider_router.get("/service-requests/{request_id}", response_model=ServiceRequestView)
async def provider_request(request_id: UUID, principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> ServiceRequestView:
    try:
        return await workflow(session).get_request(principal.user_id, request_id)
    except ENGAGEMENT_ERRORS as error:
        raise engagement_error(error) from error


@provider_router.post("/service-requests/{request_id}/view", response_model=ServiceRequestView)
async def view_request(request_id: UUID, principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> ServiceRequestView:
    try:
        return await workflow(session).view_request(principal.user_id, request_id)
    except ENGAGEMENT_ERRORS as error:
        raise engagement_error(error) from error


@provider_router.post("/service-requests/{request_id}/quotes", response_model=ServiceRequestView, status_code=status.HTTP_201_CREATED)
async def create_quote(request_id: UUID, payload: QuoteCreate, principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> ServiceRequestView:
    try:
        view = await workflow(session).quote_request(principal.user_id, request_id, payload)
        await notify_client(session, view, notification_type=NotificationType.QUOTE_RECEIVED, title="Recibiste un presupuesto", body="El prestador respondió tu solicitud con un presupuesto.", resource_type="service_request")
        return view
    except ENGAGEMENT_ERRORS as error:
        raise engagement_error(error) from error


@provider_router.post("/service-requests/{request_id}/accept", response_model=BookingView)
async def accept_fixed_request(request_id: UUID, payload: BookingSchedule | None, principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> BookingView:
    try:
        view = await workflow(session).accept_fixed_request(principal.user_id, request_id, payload)
        await notify_client(session, view, notification_type=NotificationType.BOOKING_UPDATED, title="Solicitud aceptada", body="El prestador confirmó tu servicio con precio directo.", resource_type="booking")
        return view
    except ENGAGEMENT_ERRORS as error:
        raise engagement_error(error) from error


@provider_router.post("/service-requests/{request_id}/decline", response_model=ServiceRequestView)
async def decline_request(request_id: UUID, principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> ServiceRequestView:
    try:
        view = await workflow(session).decline_request(principal.user_id, request_id)
        await notify_client(session, view, notification_type=NotificationType.REQUEST_UPDATED, title="Solicitud rechazada", body="El prestador no pudo aceptar tu solicitud.", resource_type="service_request")
        return view
    except ENGAGEMENT_ERRORS as error:
        raise engagement_error(error) from error


@provider_router.get("/service-requests/{request_id}/attachments/{attachment_id}/download-url", response_model=AttachmentDownloadView)
async def provider_attachment_download(request_id: UUID, attachment_id: UUID, principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> AttachmentDownloadView:
    try:
        return await workflow(session).attachment_download(principal.user_id, request_id, attachment_id)
    except ENGAGEMENT_ERRORS as error:
        raise engagement_error(error) from error


@provider_router.get("/bookings", response_model=list[BookingView])
async def provider_bookings(principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> list[BookingView]:
    try:
        return await workflow(session).list_provider_bookings(principal.user_id)
    except ENGAGEMENT_ERRORS as error:
        raise engagement_error(error) from error


async def provider_booking_action(action: str, booking_id: UUID, principal: ProviderPrincipal, session: AsyncSession) -> BookingView:
    try:
        view = await workflow(session).booking_action(principal.user_id, booking_id, action)
        titles = {"confirm": "Horario confirmado", "start": "Servicio iniciado", "complete": "Servicio completado", "cancel": "Turno cancelado", "no_show": "Ausencia registrada"}
        await notify_client(session, view, notification_type=NotificationType.BOOKING_UPDATED, title=titles.get(action, "Contratación actualizada"), body="El prestador actualizó el estado de tu contratación.", resource_type="booking")
        return view
    except ENGAGEMENT_ERRORS as error:
        raise engagement_error(error) from error


@provider_router.post("/bookings/{booking_id}/start", response_model=BookingView)
async def start_booking(booking_id: UUID, principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> BookingView:
    return await provider_booking_action("start", booking_id, principal, session)


@provider_router.post("/bookings/{booking_id}/confirm", response_model=BookingView)
async def provider_confirm_booking(booking_id: UUID, principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> BookingView:
    return await provider_booking_action("confirm", booking_id, principal, session)


@provider_router.post("/bookings/{booking_id}/complete", response_model=BookingView)
async def complete_booking(booking_id: UUID, principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> BookingView:
    return await provider_booking_action("complete", booking_id, principal, session)


@provider_router.post("/bookings/{booking_id}/cancel", response_model=BookingView)
async def provider_cancel_booking(booking_id: UUID, principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> BookingView:
    return await provider_booking_action("cancel", booking_id, principal, session)


@provider_router.post("/bookings/{booking_id}/no-show", response_model=BookingView)
async def no_show_booking(booking_id: UUID, principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> BookingView:
    return await provider_booking_action("no_show", booking_id, principal, session)
