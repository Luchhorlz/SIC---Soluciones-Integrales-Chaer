from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from .models import ReviewStatus


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(min_length=10, max_length=2000)


class ReviewDecision(BaseModel):
    action: Literal["publish", "reject", "hide"]
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def reason_for_restriction(self):
        if self.action in {"reject", "hide"} and (not self.reason or len(self.reason.strip()) < 5):
            raise ValueError("A moderation reason of at least five characters is required")
        return self


class ReviewView(BaseModel):
    id: UUID
    booking_id: UUID
    client_id: UUID
    provider_id: UUID
    service_name: str
    client_name: str
    provider_name: str
    rating: int
    comment: str
    status: ReviewStatus
    moderation_reason: str | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PublicReviewView(BaseModel):
    id: UUID
    service_name: str
    rating: int
    comment: str
    published_at: datetime
