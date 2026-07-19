from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID, uuid4

from sic_api.modules.catalog.service import CatalogService
from sic_api.modules.media.models import MediaFile, MediaScanStatus
from sic_api.modules.media.repository import DuplicateMediaError, MediaRepository
from sic_api.modules.media.storage import AntivirusScanner, MalwareDetectedError, PrivateStorage, StorageUnavailableError, document_object_key, validate_private_document
from sic_api.modules.provider_services.repository import ProviderServiceRepository
from sic_api.modules.providers.repository import ProviderRepository

from .models import DocumentStatus, ReviewActorKind, ServiceDocumentRequirement
from .repository import DocumentConflictError, DocumentNotFoundError, DocumentRecord, DocumentRepository, RequirementReadiness
from .schemas import AdminDocumentView, DocumentDecision, DocumentDownloadView, DocumentMetadata, DocumentReviewView, ProviderDocumentView, ProviderRequirementView, RequirementUpsert, RequirementView


class DocumentReadinessReader(Protocol):
    async def readiness(self, provider_id: UUID, service_id: UUID) -> RequirementReadiness: ...


class DocumentReadinessService:
    def __init__(self, repository: DocumentRepository) -> None:
        self.repository = repository

    async def readiness(self, provider_id: UUID, service_id: UUID) -> RequirementReadiness:
        return await self.repository.readiness(provider_id, service_id)


@dataclass(frozen=True)
class DocumentInfrastructure:
    storage: PrivateStorage
    scanner: AntivirusScanner
    private_bucket: str
    max_bytes: int
    download_ttl_seconds: int


class DocumentWorkflowService:
    def __init__(
        self,
        repository: DocumentRepository,
        media: MediaRepository,
        providers: ProviderRepository,
        provider_services: ProviderServiceRepository,
        catalog: CatalogService,
        infrastructure: DocumentInfrastructure,
    ) -> None:
        self.repository = repository
        self.media = media
        self.providers = providers
        self.provider_services = provider_services
        self.catalog = catalog
        self.infrastructure = infrastructure

    @staticmethod
    def _review_view(item) -> DocumentReviewView:
        return DocumentReviewView(id=item.id, actor_kind=item.actor_kind, previous_status=item.previous_status, new_status=item.new_status, reason=item.reason, audit_reference=item.audit_reference, created_at=item.created_at)

    @classmethod
    def _provider_document_view(cls, record: DocumentRecord) -> ProviderDocumentView:
        item = record.document
        return ProviderDocumentView(
            id=item.id,
            document_type=item.document_type,
            document_number=item.document_number,
            holder_name=item.holder_name,
            issuer=item.issuer,
            jurisdiction=item.jurisdiction,
            issued_at=item.issued_at,
            expires_at=item.expires_at,
            status=item.status,
            submitted_at=item.submitted_at,
            reviewed_at=item.reviewed_at,
            rejection_reason=item.rejection_reason,
            filename=record.media.original_filename,
            mime_type=record.media.mime_type,
            byte_size=record.media.byte_size,
            reviews=[cls._review_view(review) for review in record.reviews],
        )

    async def _admin_document_view(self, record: DocumentRecord) -> AdminDocumentView:
        public = self._provider_document_view(record)
        profile = await self.providers.get_by_id(record.document.provider_id)
        return AdminDocumentView(
            **public.model_dump(),
            provider_id=record.document.provider_id,
            provider_display_name=profile.display_name if profile else "Prestador no disponible",
            reviewed_by=record.document.reviewed_by,
            internal_notes=record.document.internal_notes,
        )

    async def _requirement_view(self, item: ServiceDocumentRequirement) -> RequirementView:
        service = await self.catalog.get_service(item.service_id, active_only=False)
        return RequirementView(
            id=item.id,
            service_id=item.service_id,
            service_name=service.name if service else "Servicio no disponible",
            document_type=item.document_type,
            label=item.label,
            is_required=item.is_required,
            jurisdiction_type=item.jurisdiction_type,
            requires_expiration=item.requires_expiration,
            instructions=item.instructions,
        )

    async def _sync_provider_services(self, provider_id: UUID) -> None:
        for configuration in await self.provider_services.list(provider_id):
            state = await self.repository.readiness(provider_id, configuration.service.service_id)
            await self.provider_services.set_document_readiness(provider_id, configuration.service.id, state.ready)

    async def _sync_catalog_service(self, service_id: UUID) -> None:
        for configuration in await self.provider_services.list_by_catalog_service(service_id):
            state = await self.repository.readiness(configuration.service.provider_id, service_id)
            await self.provider_services.set_document_readiness(configuration.service.provider_id, configuration.service.id, state.ready)

    async def expire_documents(self, on_date: date | None = None) -> int:
        provider_ids = await self.repository.expire_approved(on_date)
        for provider_id in set(provider_ids):
            await self._sync_provider_services(provider_id)
        return len(provider_ids)

    async def list_requirements(self) -> list[RequirementView]:
        return [await self._requirement_view(item) for item in await self.repository.list_requirements()]

    async def upsert_requirement(self, payload: RequirementUpsert) -> RequirementView:
        if await self.catalog.get_service(payload.service_id, active_only=False) is None:
            raise DocumentConflictError("The selected catalog service does not exist")
        item = await self.repository.upsert_requirement(payload)
        await self._sync_catalog_service(item.service_id)
        return await self._requirement_view(item)

    async def list_provider_requirements(self, provider_id: UUID) -> list[ProviderRequirementView]:
        await self.expire_documents()
        configurations = await self.provider_services.list(provider_id)
        by_service: dict[UUID, list[UUID]] = {}
        for configuration in configurations:
            by_service.setdefault(configuration.service.service_id, []).append(configuration.service.id)
        requirements = await self.repository.list_requirements(list(by_service), required_only=True)
        views: list[ProviderRequirementView] = []
        for item in requirements:
            base = await self._requirement_view(item)
            record = await self.repository.best_document(provider_id, item.document_type)
            document = record.document if record else None
            satisfied = bool(
                document
                and document.status == DocumentStatus.APPROVED
                and (document.expires_at is None or document.expires_at >= date.today())
                and (not item.requires_expiration or document.expires_at is not None)
            )
            expired = bool(document and (document.status == DocumentStatus.EXPIRED or (document.expires_at is not None and document.expires_at < date.today())))
            views.append(ProviderRequirementView(
                **base.model_dump(),
                provider_service_ids=by_service[item.service_id],
                satisfied=satisfied,
                expired=expired,
                latest_document=self._provider_document_view(record) if record else None,
            ))
        return views

    async def list_provider_documents(self, provider_id: UUID) -> list[ProviderDocumentView]:
        await self.expire_documents()
        return [self._provider_document_view(item) for item in await self.repository.list_provider_documents(provider_id)]

    async def submit_document(self, owner_user_id: UUID, provider_id: UUID, metadata: DocumentMetadata, content: bytes, filename: str, declared_mime: str | None) -> ProviderDocumentView:
        configurations = await self.provider_services.list(provider_id)
        service_ids = [item.service.service_id for item in configurations]
        requirements = await self.repository.list_requirements(service_ids)
        matching = [item for item in requirements if item.document_type == metadata.document_type and item.is_required]
        if not matching:
            raise DocumentConflictError("This document type is not required by any configured service")
        if any(item.jurisdiction_type != "NONE" for item in matching) and not metadata.jurisdiction:
            raise DocumentConflictError("This requirement needs a jurisdiction")
        if any(item.requires_expiration for item in matching) and metadata.expires_at is None:
            raise DocumentConflictError("This requirement needs an expiration date")
        validated = validate_private_document(content, filename, declared_mime, self.infrastructure.max_bytes)
        if await self.media.find_duplicate(owner_user_id, validated.sha256):
            raise DuplicateMediaError("This exact file was already uploaded")
        media_id = uuid4()
        key = document_object_key(owner_user_id, media_id, validated.extension)
        await self.infrastructure.storage.put(key, validated.content, validated.mime_type)
        media = await self.media.create(MediaFile(
            id=media_id,
            owner_user_id=owner_user_id,
            storage_bucket=self.infrastructure.private_bucket,
            object_key=key,
            original_filename=validated.original_filename,
            mime_type=validated.mime_type,
            byte_size=len(validated.content),
            sha256=validated.sha256,
            scan_status=MediaScanStatus.PENDING,
        ))
        record = await self.repository.create_document(provider_id, media.id, metadata)
        try:
            message = await self.infrastructure.scanner.scan(validated.content)
        except MalwareDetectedError:
            await self.media.set_scan_status(media.id, MediaScanStatus.INFECTED, "Malware detected")
            await self.repository.set_processing_status(record.document.id, DocumentStatus.REJECTED, "El archivo fue rechazado por el antivirus")
            await self.infrastructure.storage.delete(key)
            await self._sync_provider_services(provider_id)
            raise
        except StorageUnavailableError:
            await self.media.set_scan_status(media.id, MediaScanStatus.ERROR, "Scanner unavailable")
            raise
        await self.media.set_scan_status(media.id, MediaScanStatus.CLEAN, message)
        record = await self.repository.set_processing_status(record.document.id, DocumentStatus.PENDING)
        await self._sync_provider_services(provider_id)
        return self._provider_document_view(record)

    async def rescan_document(self, document_id: UUID) -> AdminDocumentView:
        record = await self.repository.get(document_id)
        if record.document.status != DocumentStatus.SCANNING:
            raise DocumentConflictError("Only documents waiting for antivirus can be rescanned")
        content = await self.infrastructure.storage.get(record.media.object_key)
        try:
            message = await self.infrastructure.scanner.scan(content)
        except MalwareDetectedError:
            await self.media.set_scan_status(record.media.id, MediaScanStatus.INFECTED, "Malware detected")
            record = await self.repository.set_processing_status(document_id, DocumentStatus.REJECTED, "El archivo fue rechazado por el antivirus")
            await self.infrastructure.storage.delete(record.media.object_key)
            await self._sync_provider_services(record.document.provider_id)
            return await self._admin_document_view(record)
        await self.media.set_scan_status(record.media.id, MediaScanStatus.CLEAN, message)
        record = await self.repository.set_processing_status(document_id, DocumentStatus.PENDING)
        return await self._admin_document_view(record)

    async def list_queue(self, statuses: set[DocumentStatus] | None = None) -> list[AdminDocumentView]:
        await self.expire_documents()
        records = await self.repository.list_queue(statuses)
        return [await self._admin_document_view(item) for item in records]

    async def start_review(self, document_id: UUID, reviewer_user_id: UUID, context: str) -> AdminDocumentView:
        record = await self.repository.get(document_id)
        if record.document.status != DocumentStatus.PENDING:
            raise DocumentConflictError("Only pending documents can enter review")
        updated = await self.repository.transition(document_id, DocumentStatus.IN_REVIEW, reviewer_user_id, ReviewActorKind.REVIEWER, "Revisión iniciada", context)
        return await self._admin_document_view(updated)

    async def decide(self, document_id: UUID, reviewer_user_id: UUID, target: DocumentStatus, payload: DocumentDecision, context: str) -> AdminDocumentView:
        record = await self.repository.get(document_id)
        if target == DocumentStatus.SUSPENDED:
            if record.document.status not in {DocumentStatus.APPROVED, DocumentStatus.IN_REVIEW, DocumentStatus.PENDING}:
                raise DocumentConflictError("This document cannot be suspended from its current state")
        elif record.document.status != DocumentStatus.IN_REVIEW:
            raise DocumentConflictError("The document must be in review before a decision")
        if target in {DocumentStatus.OBSERVED, DocumentStatus.REJECTED, DocumentStatus.SUSPENDED} and not payload.reason:
            raise DocumentConflictError("A reason is required for this decision")
        if target == DocumentStatus.APPROVED:
            configurations = await self.provider_services.list(record.document.provider_id)
            service_ids = [item.service.service_id for item in configurations]
            requirements = await self.repository.list_requirements(service_ids, required_only=True)
            matching = [item for item in requirements if item.document_type == record.document.document_type]
            if any(item.requires_expiration for item in matching) and record.document.expires_at is None:
                raise DocumentConflictError("An expiration date is required before approval")
            if record.document.expires_at is not None and record.document.expires_at < date.today():
                raise DocumentConflictError("An expired document cannot be approved")
        updated = await self.repository.transition(document_id, target, reviewer_user_id, ReviewActorKind.REVIEWER, payload.reason, context, payload.internal_notes)
        await self._sync_provider_services(updated.document.provider_id)
        return await self._admin_document_view(updated)

    async def provider_download(self, provider_id: UUID, document_id: UUID) -> DocumentDownloadView:
        return await self._download(await self.repository.get(document_id, provider_id))

    async def reviewer_download(self, document_id: UUID) -> DocumentDownloadView:
        return await self._download(await self.repository.get(document_id))

    async def _download(self, record: DocumentRecord) -> DocumentDownloadView:
        if record.media.scan_status != MediaScanStatus.CLEAN or record.document.status in {DocumentStatus.SCANNING, DocumentStatus.REJECTED}:
            raise DocumentConflictError("The private file is not available for download")
        url = await self.infrastructure.storage.presigned_download(record.media.object_key, record.media.original_filename, self.infrastructure.download_ttl_seconds)
        return DocumentDownloadView(url=url, expires_in_seconds=self.infrastructure.download_ttl_seconds)
