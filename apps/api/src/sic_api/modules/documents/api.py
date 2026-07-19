from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from sic_api.db.session import get_session
from sic_api.modules.catalog.repository import SqlAlchemyCatalogRepository
from sic_api.modules.catalog.service import CatalogService
from sic_api.modules.identity.permissions import AdminPrincipal, DocumentReviewerPrincipal, ProviderPrincipal
from sic_api.modules.media.repository import DuplicateMediaError, SqlAlchemyMediaRepository
from sic_api.modules.media.storage import ClamAVScanner, FileValidationError, MalwareDetectedError, S3PrivateStorage, StorageUnavailableError
from sic_api.modules.provider_services.repository import SqlAlchemyProviderServiceRepository
from sic_api.modules.providers.repository import SqlAlchemyProviderRepository
from sic_api.settings import get_settings

from .models import DocumentStatus
from .repository import DocumentConflictError, DocumentNotFoundError, SqlAlchemyDocumentRepository
from .schemas import AdminDocumentView, DocumentDecision, DocumentDownloadView, DocumentMetadata, ExpirationSummary, ProviderDocumentView, ProviderRequirementView, RequirementUpsert, RequirementView
from .service import DocumentInfrastructure, DocumentWorkflowService

provider_router = APIRouter(prefix="/v1/provider", tags=["provider-documents"])
admin_router = APIRouter(prefix="/v1/admin", tags=["admin-documents"])


def workflow(session: AsyncSession) -> DocumentWorkflowService:
    settings = get_settings()
    return DocumentWorkflowService(
        SqlAlchemyDocumentRepository(session),
        SqlAlchemyMediaRepository(session),
        SqlAlchemyProviderRepository(session),
        SqlAlchemyProviderServiceRepository(session),
        CatalogService(SqlAlchemyCatalogRepository(session)),
        DocumentInfrastructure(
            storage=S3PrivateStorage(settings),
            scanner=ClamAVScanner(settings.clamav_host, settings.clamav_port, settings.clamav_timeout_seconds),
            private_bucket=settings.s3_bucket_private,
            max_bytes=settings.document_max_bytes,
            download_ttl_seconds=settings.document_download_ttl_seconds,
        ),
    )


def document_error(error: Exception) -> HTTPException:
    if isinstance(error, DocumentNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if isinstance(error, (FileValidationError, MalwareDetectedError, ValidationError)):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error))
    if isinstance(error, StorageUnavailableError):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error))
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


async def provider_id_for(principal: ProviderPrincipal, session: AsyncSession) -> UUID:
    profile = await SqlAlchemyProviderRepository(session).get_by_user(principal.user_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider onboarding is required")
    return profile.id


@provider_router.get("/document-requirements", response_model=list[ProviderRequirementView])
async def provider_requirements(principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> list[ProviderRequirementView]:
    return await workflow(session).list_provider_requirements(await provider_id_for(principal, session))


@provider_router.get("/documents", response_model=list[ProviderDocumentView])
async def provider_documents(principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> list[ProviderDocumentView]:
    return await workflow(session).list_provider_documents(await provider_id_for(principal, session))


@provider_router.post("/documents", response_model=ProviderDocumentView, status_code=status.HTTP_201_CREATED)
async def upload_provider_document(
    principal: ProviderPrincipal,
    document_type: Annotated[str, Form()],
    holder_name: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    document_number: Annotated[str | None, Form()] = None,
    issuer: Annotated[str | None, Form()] = None,
    jurisdiction: Annotated[str | None, Form()] = None,
    issued_at: Annotated[date | None, Form()] = None,
    expires_at: Annotated[date | None, Form()] = None,
    session: AsyncSession = Depends(get_session),
) -> ProviderDocumentView:
    try:
        settings = get_settings()
        content = await file.read(settings.document_max_bytes + 1)
        metadata = DocumentMetadata(document_type=document_type, document_number=document_number or None, holder_name=holder_name, issuer=issuer or None, jurisdiction=jurisdiction or None, issued_at=issued_at, expires_at=expires_at)
        provider_id = await provider_id_for(principal, session)
        return await workflow(session).submit_document(principal.user_id, provider_id, metadata, content, file.filename or "document", file.content_type)
    except (DocumentConflictError, DocumentNotFoundError, DuplicateMediaError, FileValidationError, MalwareDetectedError, StorageUnavailableError, ValidationError) as error:
        raise document_error(error) from error
    finally:
        await file.close()


@provider_router.get("/documents/{document_id}/download-url", response_model=DocumentDownloadView)
async def provider_document_download(document_id: UUID, principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> DocumentDownloadView:
    try:
        return await workflow(session).provider_download(await provider_id_for(principal, session), document_id)
    except (DocumentConflictError, DocumentNotFoundError, StorageUnavailableError) as error:
        raise document_error(error) from error


@admin_router.get("/document-requirements", response_model=list[RequirementView])
async def admin_requirements(_principal: DocumentReviewerPrincipal, session: AsyncSession = Depends(get_session)) -> list[RequirementView]:
    return await workflow(session).list_requirements()


@admin_router.post("/document-requirements", response_model=RequirementView)
async def upsert_document_requirement(payload: RequirementUpsert, _principal: AdminPrincipal, session: AsyncSession = Depends(get_session)) -> RequirementView:
    try:
        return await workflow(session).upsert_requirement(payload)
    except (DocumentConflictError, DocumentNotFoundError) as error:
        raise document_error(error) from error


@admin_router.get("/documents", response_model=list[AdminDocumentView])
async def review_queue(
    _principal: DocumentReviewerPrincipal,
    statuses: Annotated[list[DocumentStatus] | None, Query()] = None,
    session: AsyncSession = Depends(get_session),
) -> list[AdminDocumentView]:
    return await workflow(session).list_queue(set(statuses) if statuses else None)


def review_context(request: Request, session_id: str) -> str:
    request_id = request.headers.get("x-request-id", "unknown")
    return f"request:{request_id};session:{session_id[:64]}"


@admin_router.post("/documents/{document_id}/review", response_model=AdminDocumentView)
async def begin_document_review(document_id: UUID, request: Request, principal: DocumentReviewerPrincipal, session: AsyncSession = Depends(get_session)) -> AdminDocumentView:
    try:
        return await workflow(session).start_review(document_id, principal.user_id, review_context(request, principal.session_id))
    except (DocumentConflictError, DocumentNotFoundError) as error:
        raise document_error(error) from error


async def apply_decision(document_id: UUID, target: DocumentStatus, payload: DocumentDecision, request: Request, principal, session: AsyncSession) -> AdminDocumentView:
    try:
        return await workflow(session).decide(document_id, principal.user_id, target, payload, review_context(request, principal.session_id))
    except (DocumentConflictError, DocumentNotFoundError) as error:
        raise document_error(error) from error


@admin_router.post("/documents/{document_id}/approve", response_model=AdminDocumentView)
async def approve_document(document_id: UUID, payload: DocumentDecision, request: Request, principal: DocumentReviewerPrincipal, session: AsyncSession = Depends(get_session)) -> AdminDocumentView:
    return await apply_decision(document_id, DocumentStatus.APPROVED, payload, request, principal, session)


@admin_router.post("/documents/{document_id}/observe", response_model=AdminDocumentView)
async def observe_document(document_id: UUID, payload: DocumentDecision, request: Request, principal: DocumentReviewerPrincipal, session: AsyncSession = Depends(get_session)) -> AdminDocumentView:
    return await apply_decision(document_id, DocumentStatus.OBSERVED, payload, request, principal, session)


@admin_router.post("/documents/{document_id}/reject", response_model=AdminDocumentView)
async def reject_document(document_id: UUID, payload: DocumentDecision, request: Request, principal: DocumentReviewerPrincipal, session: AsyncSession = Depends(get_session)) -> AdminDocumentView:
    return await apply_decision(document_id, DocumentStatus.REJECTED, payload, request, principal, session)


@admin_router.post("/documents/{document_id}/suspend", response_model=AdminDocumentView)
async def suspend_document(document_id: UUID, payload: DocumentDecision, request: Request, principal: DocumentReviewerPrincipal, session: AsyncSession = Depends(get_session)) -> AdminDocumentView:
    return await apply_decision(document_id, DocumentStatus.SUSPENDED, payload, request, principal, session)


@admin_router.post("/documents/{document_id}/rescan", response_model=AdminDocumentView)
async def rescan_document(document_id: UUID, _principal: DocumentReviewerPrincipal, session: AsyncSession = Depends(get_session)) -> AdminDocumentView:
    try:
        return await workflow(session).rescan_document(document_id)
    except (DocumentConflictError, DocumentNotFoundError, MalwareDetectedError, StorageUnavailableError) as error:
        raise document_error(error) from error


@admin_router.get("/documents/{document_id}/download-url", response_model=DocumentDownloadView)
async def reviewer_document_download(document_id: UUID, _principal: DocumentReviewerPrincipal, session: AsyncSession = Depends(get_session)) -> DocumentDownloadView:
    try:
        return await workflow(session).reviewer_download(document_id)
    except (DocumentConflictError, DocumentNotFoundError, StorageUnavailableError) as error:
        raise document_error(error) from error


@admin_router.post("/documents/expire", response_model=ExpirationSummary)
async def expire_documents(_principal: AdminPrincipal, session: AsyncSession = Depends(get_session)) -> ExpirationSummary:
    return ExpirationSummary(expired_documents=await workflow(session).expire_documents())
