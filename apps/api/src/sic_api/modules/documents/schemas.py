from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from .models import DocumentStatus, ReviewActorKind


DOCUMENT_TYPE_PATTERN = r"^[A-Z][A-Z0-9_]{2,79}$"


class RequirementUpsert(BaseModel):
    service_id: UUID
    document_type: str = Field(min_length=3, max_length=80, pattern=DOCUMENT_TYPE_PATTERN)
    label: str = Field(min_length=3, max_length=120)
    is_required: bool = True
    jurisdiction_type: str = Field(default="NONE", min_length=2, max_length=40, pattern=r"^[A-Z][A-Z0-9_]{1,39}$")
    requires_expiration: bool = False
    instructions: str | None = Field(default=None, max_length=2000)

    @field_validator("document_type", "jurisdiction_type")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class RequirementView(RequirementUpsert):
    id: UUID
    service_name: str


class DocumentMetadata(BaseModel):
    document_type: str = Field(min_length=3, max_length=80, pattern=DOCUMENT_TYPE_PATTERN)
    document_number: str | None = Field(default=None, max_length=120)
    holder_name: str = Field(min_length=2, max_length=180)
    issuer: str | None = Field(default=None, max_length=180)
    jurisdiction: str | None = Field(default=None, max_length=180)
    issued_at: date | None = None
    expires_at: date | None = None

    @field_validator("document_type")
    @classmethod
    def normalize_document_type(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def dates_are_consistent(self):
        if self.issued_at and self.expires_at and self.expires_at <= self.issued_at:
            raise ValueError("Expiration must be after issue date")
        return self


class DocumentReviewView(BaseModel):
    id: UUID
    actor_kind: ReviewActorKind
    previous_status: DocumentStatus
    new_status: DocumentStatus
    reason: str | None
    audit_reference: UUID
    created_at: datetime


class ProviderDocumentView(BaseModel):
    id: UUID
    document_type: str
    document_number: str | None
    holder_name: str
    issuer: str | None
    jurisdiction: str | None
    issued_at: date | None
    expires_at: date | None
    status: DocumentStatus
    submitted_at: datetime
    reviewed_at: datetime | None
    rejection_reason: str | None
    filename: str
    mime_type: str
    byte_size: int
    reviews: list[DocumentReviewView]


class AdminDocumentView(ProviderDocumentView):
    provider_id: UUID
    provider_display_name: str
    reviewed_by: UUID | None
    internal_notes: str | None


class ProviderRequirementView(RequirementView):
    provider_service_ids: list[UUID]
    satisfied: bool
    expired: bool
    latest_document: ProviderDocumentView | None


class DocumentDecision(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)
    internal_notes: str | None = Field(default=None, max_length=4000)


class DocumentDownloadView(BaseModel):
    url: str
    expires_in_seconds: int


class ExpirationSummary(BaseModel):
    expired_documents: int
