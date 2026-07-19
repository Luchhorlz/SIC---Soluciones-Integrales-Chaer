from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from sic_api.modules.provider_services.models import PricingType, ProviderModality

from .models import BookingStatus, QuoteStatus, ServiceRequestStatus


class ServiceRequestCreate(BaseModel):
    provider_service_id: UUID
    selected_modality: ProviderModality
    client_address_id: UUID | None = None
    title: str = Field(min_length=4, max_length=180)
    description: str = Field(min_length=20, max_length=5000)
    preferred_start_at: datetime | None = None

    @model_validator(mode="after")
    def future_preference(self):
        if self.preferred_start_at is not None:
            if self.preferred_start_at.tzinfo is None:
                raise ValueError("preferred_start_at must include a timezone")
            if self.preferred_start_at <= datetime.now(timezone.utc):
                raise ValueError("preferred_start_at must be in the future")
        return self


class QuoteCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="ARS", pattern=r"^[A-Z]{3}$")
    description: str = Field(min_length=10, max_length=3000)
    valid_until: datetime

    @model_validator(mode="after")
    def future_validity(self):
        if self.valid_until.tzinfo is None:
            raise ValueError("valid_until must include a timezone")
        if self.valid_until <= datetime.now(timezone.utc):
            raise ValueError("valid_until must be in the future")
        return self


class BookingSchedule(BaseModel):
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def valid_schedule(self):
        if self.starts_at.tzinfo is None or self.ends_at.tzinfo is None:
            raise ValueError("Booking dates must include a timezone")
        if self.starts_at <= datetime.now(timezone.utc):
            raise ValueError("The booking must start in the future")
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        if (self.ends_at - self.starts_at).total_seconds() > 7 * 24 * 3600:
            raise ValueError("A booking cannot span more than seven days")
        return self


class QuoteDecision(BaseModel):
    quote_id: UUID
    schedule: BookingSchedule | None = None


class BookingDispute(BaseModel):
    reason: str = Field(min_length=10, max_length=500)


class RequestAttachmentView(BaseModel):
    id: UUID
    filename: str
    mime_type: str
    byte_size: int
    created_at: datetime


class QuoteView(BaseModel):
    id: UUID
    amount: Decimal
    currency: str
    description: str
    valid_until: datetime
    status: QuoteStatus
    created_at: datetime


class ServiceRequestView(BaseModel):
    id: UUID
    client_id: UUID
    provider_id: UUID
    provider_service_id: UUID
    service_name: str
    offer_headline: str
    pricing_type: PricingType
    configured_price: Decimal | None
    price_currency: str
    client_name: str
    provider_name: str
    selected_modality: ProviderModality
    client_address_label: str | None
    title: str
    description: str
    preferred_start_at: datetime | None
    status: ServiceRequestStatus
    viewed_at: datetime | None
    created_at: datetime
    attachments: list[RequestAttachmentView]
    quotes: list[QuoteView]
    booking_id: UUID | None


class BookingAddressView(BaseModel):
    label: str
    formatted_address: str
    street: str
    street_number: str
    unit: str | None
    city: str
    province: str
    postal_code: str | None


class BookingView(BaseModel):
    id: UUID
    request_id: UUID
    client_id: UUID
    provider_id: UUID
    provider_service_id: UUID
    service_name: str
    offer_headline: str
    client_name: str
    provider_name: str
    modality: ProviderModality
    address: BookingAddressView | None
    starts_at: datetime
    ends_at: datetime
    agreed_price: Decimal | None
    currency: str
    status: BookingStatus
    completed_at: datetime | None
    client_confirmed_at: datetime | None
    cancelled_at: datetime | None
    dispute_reason: str | None
    created_at: datetime


class AttachmentDownloadView(BaseModel):
    url: str
    expires_in_seconds: int
