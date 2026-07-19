from datetime import datetime, time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from sic_api.modules.providers.visibility import VisibilityCode

from .models import PricingType, ProviderModality, ProviderServiceStatus


class ServiceAreaInput(BaseModel):
    center_address_id: UUID
    radius_meters: int = Field(ge=100, le=1_000_000)
    urgent_radius_meters: int | None = Field(default=None, ge=100, le=1_000_000)
    travel_fee_policy: str | None = Field(default=None, max_length=40)

    @model_validator(mode="after")
    def urgent_area_fits(self):
        if self.urgent_radius_meters is not None and self.urgent_radius_meters > self.radius_meters:
            raise ValueError("Urgent radius cannot exceed the regular radius")
        return self


class ProviderServiceCreate(BaseModel):
    service_id: UUID
    headline: str = Field(min_length=4, max_length=180)
    description: str = Field(min_length=20, max_length=4000)
    pricing_type: PricingType
    price_amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    estimated_duration_minutes: int | None = Field(default=None, ge=15, le=43_200)
    guarantee_days: int | None = Field(default=None, ge=0, le=3650)
    accepts_urgent: bool = False
    requires_quote_details: bool = True
    modalities: set[ProviderModality] = Field(min_length=1)
    area: ServiceAreaInput | None = None

    @model_validator(mode="after")
    def pricing_is_consistent(self):
        if self.pricing_type == PricingType.QUOTE and self.price_amount is not None:
            raise ValueError("Quote services cannot set a fixed amount")
        if self.pricing_type != PricingType.QUOTE and self.price_amount is None:
            raise ValueError("This pricing type requires an amount")
        return self


class ProviderServiceUpdate(BaseModel):
    headline: str | None = Field(default=None, min_length=4, max_length=180)
    description: str | None = Field(default=None, min_length=20, max_length=4000)
    pricing_type: PricingType | None = None
    price_amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    estimated_duration_minutes: int | None = Field(default=None, ge=15, le=43_200)
    guarantee_days: int | None = Field(default=None, ge=0, le=3650)
    accepts_urgent: bool | None = None
    requires_quote_details: bool | None = None
    modalities: set[ProviderModality] | None = Field(default=None, min_length=1)
    area: ServiceAreaInput | None = None

    @model_validator(mode="after")
    def has_changes(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class ServiceAreaView(BaseModel):
    center_address_id: UUID
    radius_meters: int
    urgent_radius_meters: int | None
    travel_fee_policy: str | None


class ProviderServiceView(BaseModel):
    id: UUID
    service_id: UUID
    status: ProviderServiceStatus
    headline: str
    description: str
    pricing_type: PricingType
    price_amount: Decimal | None
    price_currency: str
    estimated_duration_minutes: int | None
    guarantee_days: int | None
    accepts_urgent: bool
    requires_quote_details: bool
    modalities: list[ProviderModality]
    area: ServiceAreaView | None
    visibility_code: VisibilityCode
    visible: bool


class ProviderServicePauseRequest(BaseModel):
    paused: bool


class AvailabilityRuleInput(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    timezone: str = Field(default="America/Argentina/Buenos_Aires", min_length=3, max_length=64)
    slot_duration_minutes: int = Field(default=60, ge=15, le=480)
    is_active: bool = True

    @model_validator(mode="after")
    def time_range_is_valid(self):
        if self.start_time >= self.end_time:
            raise ValueError("Availability end time must be after start time")
        return self


class AvailabilityRulesReplace(BaseModel):
    rules: list[AvailabilityRuleInput] = Field(max_length=50)

    @model_validator(mode="after")
    def rules_do_not_overlap(self):
        active = sorted((item for item in self.rules if item.is_active), key=lambda item: (item.day_of_week, item.start_time, item.end_time))
        for previous, current in zip(active, active[1:]):
            if previous.day_of_week == current.day_of_week and current.start_time < previous.end_time:
                raise ValueError("Availability rules cannot overlap")
        return self


class AvailabilityRuleView(AvailabilityRuleInput):
    id: UUID


class AvailabilityExceptionCreate(BaseModel):
    starts_at: datetime
    ends_at: datetime
    reason: str | None = Field(default=None, max_length=240)
    is_available_override: bool = False

    @model_validator(mode="after")
    def range_is_valid(self):
        if self.starts_at.tzinfo is None or self.ends_at.tzinfo is None:
            raise ValueError("Availability exceptions require an explicit timezone")
        if self.starts_at >= self.ends_at:
            raise ValueError("Exception end must be after start")
        return self


class AvailabilityExceptionView(AvailabilityExceptionCreate):
    id: UUID
