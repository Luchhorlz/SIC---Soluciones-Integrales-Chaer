from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from sic_api.modules.media.models import MediaFile

from .models import DocumentReview, DocumentStatus, ProviderDocument, ReviewActorKind, ServiceDocumentRequirement
from .schemas import DocumentMetadata, RequirementUpsert


class DocumentNotFoundError(LookupError):
    pass


class DocumentConflictError(ValueError):
    pass


@dataclass(frozen=True)
class DocumentRecord:
    document: ProviderDocument
    media: MediaFile
    reviews: tuple[DocumentReview, ...]


@dataclass(frozen=True)
class RequirementReadiness:
    ready: bool
    expired: bool


class DocumentRepository(Protocol):
    async def list_requirements(self, service_ids: list[UUID] | None = None, required_only: bool = False) -> list[ServiceDocumentRequirement]: ...
    async def upsert_requirement(self, payload: RequirementUpsert) -> ServiceDocumentRequirement: ...
    async def list_provider_documents(self, provider_id: UUID) -> list[DocumentRecord]: ...
    async def list_queue(self, statuses: set[DocumentStatus] | None = None) -> list[DocumentRecord]: ...
    async def get(self, document_id: UUID, provider_id: UUID | None = None) -> DocumentRecord: ...
    async def create_document(self, provider_id: UUID, media_file_id: UUID, metadata: DocumentMetadata) -> DocumentRecord: ...
    async def set_processing_status(self, document_id: UUID, status: DocumentStatus, reason: str | None = None) -> DocumentRecord: ...
    async def transition(self, document_id: UUID, new_status: DocumentStatus, reviewer_user_id: UUID | None, actor_kind: ReviewActorKind, reason: str | None, context: str | None, internal_notes: str | None = None) -> DocumentRecord: ...
    async def readiness(self, provider_id: UUID, service_id: UUID, on_date: date | None = None) -> RequirementReadiness: ...
    async def best_document(self, provider_id: UUID, document_type: str) -> DocumentRecord | None: ...
    async def expire_approved(self, on_date: date | None = None) -> list[UUID]: ...


class SqlAlchemyDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_requirements(self, service_ids: list[UUID] | None = None, required_only: bool = False) -> list[ServiceDocumentRequirement]:
        query = select(ServiceDocumentRequirement).order_by(ServiceDocumentRequirement.label)
        if service_ids is not None:
            if not service_ids:
                return []
            query = query.where(ServiceDocumentRequirement.service_id.in_(service_ids))
        if required_only:
            query = query.where(ServiceDocumentRequirement.is_required.is_(True))
        return list((await self.session.scalars(query)).all())

    async def upsert_requirement(self, payload: RequirementUpsert) -> ServiceDocumentRequirement:
        values = payload.model_dump()
        statement = insert(ServiceDocumentRequirement).values(**values).on_conflict_do_update(
            constraint="uq_service_document_requirement",
            set_={key: value for key, value in values.items() if key not in {"service_id", "document_type"}},
        ).returning(ServiceDocumentRequirement.id)
        requirement_id = await self.session.scalar(statement)
        await self.session.commit()
        item = await self.session.get(ServiceDocumentRequirement, requirement_id)
        if item is None:
            raise DocumentNotFoundError
        return item

    async def _record(self, document: ProviderDocument) -> DocumentRecord:
        media = await self.session.get(MediaFile, document.media_file_id)
        if media is None:
            raise DocumentNotFoundError
        reviews = tuple((await self.session.scalars(select(DocumentReview).where(DocumentReview.document_id == document.id).order_by(DocumentReview.created_at))).all())
        return DocumentRecord(document=document, media=media, reviews=reviews)

    async def list_provider_documents(self, provider_id: UUID) -> list[DocumentRecord]:
        items = (await self.session.scalars(select(ProviderDocument).where(ProviderDocument.provider_id == provider_id).order_by(ProviderDocument.submitted_at.desc()))).all()
        return [await self._record(item) for item in items]

    async def list_queue(self, statuses: set[DocumentStatus] | None = None) -> list[DocumentRecord]:
        query = select(ProviderDocument).order_by(ProviderDocument.submitted_at)
        if statuses:
            query = query.where(ProviderDocument.status.in_(statuses))
        items = (await self.session.scalars(query)).all()
        return [await self._record(item) for item in items]

    async def get(self, document_id: UUID, provider_id: UUID | None = None) -> DocumentRecord:
        query = select(ProviderDocument).where(ProviderDocument.id == document_id)
        if provider_id is not None:
            query = query.where(ProviderDocument.provider_id == provider_id)
        item = await self.session.scalar(query)
        if item is None:
            raise DocumentNotFoundError
        return await self._record(item)

    async def create_document(self, provider_id: UUID, media_file_id: UUID, metadata: DocumentMetadata) -> DocumentRecord:
        item = ProviderDocument(provider_id=provider_id, media_file_id=media_file_id, status=DocumentStatus.SCANNING, **metadata.model_dump())
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return await self._record(item)

    async def set_processing_status(self, document_id: UUID, status: DocumentStatus, reason: str | None = None) -> DocumentRecord:
        item = await self.session.get(ProviderDocument, document_id)
        if item is None:
            raise DocumentNotFoundError
        if status not in {DocumentStatus.SCANNING, DocumentStatus.PENDING, DocumentStatus.REJECTED}:
            raise DocumentConflictError("Invalid processing status")
        item.status = status
        item.rejection_reason = reason
        if status == DocumentStatus.PENDING:
            item.submitted_at = datetime.now(timezone.utc)
        await self.session.commit()
        return await self._record(item)

    async def transition(self, document_id: UUID, new_status: DocumentStatus, reviewer_user_id: UUID | None, actor_kind: ReviewActorKind, reason: str | None, context: str | None, internal_notes: str | None = None) -> DocumentRecord:
        item = await self.session.get(ProviderDocument, document_id)
        if item is None:
            raise DocumentNotFoundError
        previous = item.status
        if previous == new_status:
            raise DocumentConflictError("The document already has this status")
        item.status = new_status
        item.reviewed_at = datetime.now(timezone.utc)
        item.reviewed_by = reviewer_user_id
        if new_status in {DocumentStatus.OBSERVED, DocumentStatus.REJECTED, DocumentStatus.SUSPENDED}:
            item.rejection_reason = reason
        elif new_status == DocumentStatus.APPROVED:
            item.rejection_reason = None
        if internal_notes is not None:
            item.internal_notes = internal_notes.strip() or None
        self.session.add(DocumentReview(
            document_id=item.id,
            reviewer_user_id=reviewer_user_id,
            actor_kind=actor_kind,
            previous_status=previous,
            new_status=new_status,
            reason=reason.strip() if reason else None,
            administrative_context=context[:240] if context else None,
        ))
        await self.session.commit()
        return await self._record(item)

    async def readiness(self, provider_id: UUID, service_id: UUID, on_date: date | None = None) -> RequirementReadiness:
        today = on_date or date.today()
        requirements = await self.list_requirements([service_id], required_only=True)
        if not requirements:
            return RequirementReadiness(ready=True, expired=False)
        types = {item.document_type for item in requirements}
        documents = list((await self.session.scalars(select(ProviderDocument).where(ProviderDocument.provider_id == provider_id, ProviderDocument.document_type.in_(types)))).all())
        expired = False
        for requirement in requirements:
            matching = [item for item in documents if item.document_type == requirement.document_type]
            valid = any(
                item.status == DocumentStatus.APPROVED
                and (item.expires_at is None or item.expires_at >= today)
                and (not requirement.requires_expiration or item.expires_at is not None)
                for item in matching
            )
            if not valid:
                expired = expired or any(item.status == DocumentStatus.EXPIRED or (item.expires_at is not None and item.expires_at < today) for item in matching)
                return RequirementReadiness(ready=False, expired=expired)
        return RequirementReadiness(ready=True, expired=False)

    async def best_document(self, provider_id: UUID, document_type: str) -> DocumentRecord | None:
        priority = {
            DocumentStatus.APPROVED: 0,
            DocumentStatus.IN_REVIEW: 1,
            DocumentStatus.PENDING: 2,
            DocumentStatus.OBSERVED: 3,
            DocumentStatus.SCANNING: 4,
            DocumentStatus.EXPIRED: 5,
            DocumentStatus.REJECTED: 6,
            DocumentStatus.SUSPENDED: 7,
            DocumentStatus.UPLOADED: 8,
            DocumentStatus.DRAFT: 9,
        }
        items = (await self.session.scalars(select(ProviderDocument).where(ProviderDocument.provider_id == provider_id, ProviderDocument.document_type == document_type).order_by(ProviderDocument.submitted_at.desc()))).all()
        if not items:
            return None
        best = min(items, key=lambda item: (priority[item.status], -item.submitted_at.timestamp()))
        return await self._record(best)

    async def expire_approved(self, on_date: date | None = None) -> list[UUID]:
        today = on_date or date.today()
        items = (await self.session.scalars(select(ProviderDocument).where(ProviderDocument.status == DocumentStatus.APPROVED, ProviderDocument.expires_at < today))).all()
        provider_ids: list[UUID] = []
        for item in items:
            previous = item.status
            item.status = DocumentStatus.EXPIRED
            item.reviewed_at = datetime.now(timezone.utc)
            item.reviewed_by = None
            self.session.add(DocumentReview(document_id=item.id, reviewer_user_id=None, actor_kind=ReviewActorKind.SYSTEM, previous_status=previous, new_status=DocumentStatus.EXPIRED, reason="Vencimiento automático", administrative_context="scheduled-expiration"))
            provider_ids.append(item.provider_id)
        if items:
            await self.session.commit()
        return provider_ids
