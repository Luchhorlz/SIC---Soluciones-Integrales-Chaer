import enum
from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from sic_api.db.base import Base


class DocumentStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    UPLOADED = "UPLOADED"
    SCANNING = "SCANNING"
    PENDING = "PENDING"
    IN_REVIEW = "IN_REVIEW"
    OBSERVED = "OBSERVED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    SUSPENDED = "SUSPENDED"


class ReviewActorKind(str, enum.Enum):
    REVIEWER = "REVIEWER"
    SYSTEM = "SYSTEM"


class ServiceDocumentRequirement(Base):
    __tablename__ = "service_document_requirements"
    __table_args__ = (UniqueConstraint("service_id", "document_type", name="uq_service_document_requirement"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    service_id: Mapped[UUID] = mapped_column(ForeignKey("services.id", ondelete="RESTRICT"), index=True)
    document_type: Mapped[str] = mapped_column(String(80))
    label: Mapped[str] = mapped_column(String(120))
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    jurisdiction_type: Mapped[str] = mapped_column(String(40), default="NONE")
    requires_expiration: Mapped[bool] = mapped_column(Boolean, default=False)
    instructions: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ProviderDocument(Base):
    __tablename__ = "provider_documents"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider_id: Mapped[UUID] = mapped_column(ForeignKey("provider_profiles.id", ondelete="RESTRICT"), index=True)
    document_type: Mapped[str] = mapped_column(String(80), index=True)
    document_number: Mapped[str | None] = mapped_column(String(120))
    holder_name: Mapped[str] = mapped_column(String(180))
    issuer: Mapped[str | None] = mapped_column(String(180))
    jurisdiction: Mapped[str | None] = mapped_column(String(180))
    issued_at: Mapped[date | None] = mapped_column(Date)
    expires_at: Mapped[date | None] = mapped_column(Date)
    media_file_id: Mapped[UUID] = mapped_column(ForeignKey("media_files.id", ondelete="RESTRICT"), unique=True)
    status: Mapped[DocumentStatus] = mapped_column(Enum(DocumentStatus, name="provider_document_status"), default=DocumentStatus.UPLOADED, index=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    internal_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DocumentReview(Base):
    __tablename__ = "document_reviews"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("provider_documents.id", ondelete="RESTRICT"), index=True)
    reviewer_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    actor_kind: Mapped[ReviewActorKind] = mapped_column(Enum(ReviewActorKind, name="document_review_actor_kind"), default=ReviewActorKind.REVIEWER)
    previous_status: Mapped[DocumentStatus] = mapped_column(Enum(DocumentStatus, name="provider_document_status", create_type=False))
    new_status: Mapped[DocumentStatus] = mapped_column(Enum(DocumentStatus, name="provider_document_status", create_type=False))
    reason: Mapped[str | None] = mapped_column(Text)
    administrative_context: Mapped[str | None] = mapped_column(String(240))
    audit_reference: Mapped[UUID] = mapped_column(default=uuid4, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
