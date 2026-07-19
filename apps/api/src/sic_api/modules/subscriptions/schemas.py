from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import BillingFrequency, ProviderSubscriptionStatus, SubscriptionProvider


class SubscriptionPlanCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    code: str = Field(min_length=3, max_length=80, pattern=r"^[A-Z][A-Z0-9_]+$")
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="ARS", pattern=r"^[A-Z]{3}$")
    billing_frequency: BillingFrequency = BillingFrequency.MONTHLY
    is_active: bool = True
    features: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("features")
    @classmethod
    def normalize_features(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values if value.strip()]
        if any(len(value) > 160 for value in normalized):
            raise ValueError("Each feature must contain at most 160 characters")
        return list(dict.fromkeys(normalized))


class SubscriptionPlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=120)
    price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    is_active: bool | None = None
    features: list[str] | None = Field(default=None, max_length=20)

    @field_validator("name")
    @classmethod
    def normalize_optional_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("features")
    @classmethod
    def normalize_optional_features(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        normalized = [value.strip() for value in values if value.strip()]
        if any(len(value) > 160 for value in normalized):
            raise ValueError("Each feature must contain at most 160 characters")
        return list(dict.fromkeys(normalized))


class SubscriptionPlanView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str
    price: Decimal
    currency: str
    billing_frequency: BillingFrequency
    is_active: bool
    features: list[str]
    mercado_pago_plan_id: str | None = None
    created_at: datetime
    updated_at: datetime


class ProviderSubscriptionView(BaseModel):
    id: UUID
    plan_id: UUID
    provider_name: SubscriptionProvider
    status: ProviderSubscriptionStatus
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool
    last_payment_status: str | None = None
    created_at: datetime
    updated_at: datetime


class ProviderSubscriptionPage(BaseModel):
    plan: SubscriptionPlanView | None
    subscription: ProviderSubscriptionView | None
    checkout_available: bool
    billing_configured: bool
    message: str


class SubscriptionCheckoutView(BaseModel):
    checkout_url: str
    status: ProviderSubscriptionStatus


class WebhookReceipt(BaseModel):
    status: str
