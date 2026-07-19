from __future__ import annotations

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


@client_router.get("/service-requests", response_model=list[ServiceRequestView])
async def client_requests(principal: ClientPrincipal, session: AsyncSession = Depends(get_session)) -> list[ServiceRequestView]:
    try:
        return await workflow(session).list_client_requests(principal.user_id)
    except ENGAGEMENT_ERRORS as error:
        raise engagement_error(error) from error


@client_router.post("/service-requests", response_model=ServiceRequestView, status_code=status.HTTP_201_CREATED)
async def create_request(payload: ServiceRequestCreate, principal: ClientPrincipal, session: AsyncSession = Depends(get_session)) -> ServiceRequestView:
    try:
        return await workflow(session).create_request(principal.user_id, payload)
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
        return await workflow(session).cancel_request(principal.user_id, request_id)
    except ENGAGEMENT_ERRORS as error:
        raise engagement_error(error) from error


@client_router.post("/service-requests/{request_id}/quotes/accept", response_model=BookingView)
async def accept_quote(request_id: UUID, payload: QuoteDecision, principal: ClientPrincipal, session: AsyncSession = Depends(get_session)) -> BookingView:
    try:
        return await workflow(session).accept_quote(principal.user_id, request_id, payload)
    except ENGAGEMENT_ERRORS as error:
        raise engagement_error(error) from error


@client_router.post("/service-requests/{request_id}/quotes/{quote_id}/reject", response_model=ServiceRequestView)
async def reject_quote(request_id: UUID, quote_id: UUID, principal: ClientPrincipal, session: AsyncSession = Depends(get_session)) -> ServiceRequestView:
    try:
        return await workflow(session).reject_quote(principal.user_id, request_id, quote_id)
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
        return await workflow(session).booking_action(principal.user_id, booking_id, "confirm")
    except ENGAGEMENT_ERRORS as error:
        raise engagement_error(error) from error


@client_router.post("/bookings/{booking_id}/dispute", response_model=BookingView)
async def dispute_booking(booking_id: UUID, payload: BookingDispute, principal: ClientPrincipal, session: AsyncSession = Depends(get_session)) -> BookingView:
    try:
        return await workflow(session).booking_action(principal.user_id, booking_id, "dispute", payload)
    except ENGAGEMENT_ERRORS as error:
        raise engagement_error(error) from error


@client_router.post("/bookings/{booking_id}/cancel", response_model=BookingView)
async def cancel_booking(booking_id: UUID, principal: ClientPrincipal, session: AsyncSession = Depends(get_session)) -> BookingView:
    try:
        return await workflow(session).booking_action(principal.user_id, booking_id, "cancel")
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
        return await workflow(session).quote_request(principal.user_id, request_id, payload)
    except ENGAGEMENT_ERRORS as error:
        raise engagement_error(error) from error


@provider_router.post("/service-requests/{request_id}/accept", response_model=BookingView)
async def accept_fixed_request(request_id: UUID, payload: BookingSchedule | None, principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> BookingView:
    try:
        return await workflow(session).accept_fixed_request(principal.user_id, request_id, payload)
    except ENGAGEMENT_ERRORS as error:
        raise engagement_error(error) from error


@provider_router.post("/service-requests/{request_id}/decline", response_model=ServiceRequestView)
async def decline_request(request_id: UUID, principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> ServiceRequestView:
    try:
        return await workflow(session).decline_request(principal.user_id, request_id)
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
        return await workflow(session).booking_action(principal.user_id, booking_id, action)
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
