import enum
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, JSON, Numeric, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from sic_api.db.base import Base


class BillingFrequency(str, enum.Enum):
    MONTHLY = "MONTHLY"


class SubscriptionProvider(str, enum.Enum):
    MERCADO_PAGO = "MERCADO_PAGO"


class ProviderSubscriptionStatus(str, enum.Enum):
    PENDING = "PENDING"
    AUTHORIZED = "AUTHORIZED"
    ACTIVE = "ACTIVE"
    PAST_DUE = "PAST_DUE"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    ERROR = "ERROR"


class BillingProcessingStatus(str, enum.Enum):
    RECEIVED = "RECEIVED"
    PROCESSED = "PROCESSED"
    IGNORED = "IGNORED"
    FAILED = "FAILED"


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"
    __table_args__ = (Index("uq_subscription_plans_one_active", "is_active", unique=True, postgresql_where=text("is_active")),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120))
    code: Mapped[str] = mapped_column(String(80), unique=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3))
    billing_frequency: Mapped[BillingFrequency] = mapped_column(Enum(BillingFrequency, name="billing_frequency"), default=BillingFrequency.MONTHLY)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    features_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    mercado_pago_plan_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ProviderSubscription(Base):
    __tablename__ = "provider_subscriptions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider_id: Mapped[UUID] = mapped_column(ForeignKey("provider_profiles.id", ondelete="RESTRICT"), unique=True)
    plan_id: Mapped[UUID] = mapped_column(ForeignKey("subscription_plans.id", ondelete="RESTRICT"))
    provider_name: Mapped[SubscriptionProvider] = mapped_column(Enum(SubscriptionProvider, name="subscription_provider"), default=SubscriptionProvider.MERCADO_PAGO)
    external_subscription_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    status: Mapped[ProviderSubscriptionStatus] = mapped_column(Enum(ProviderSubscriptionStatus, name="provider_subscription_status"), default=ProviderSubscriptionStatus.PENDING, index=True)
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    last_payment_status: Mapped[str | None] = mapped_column(String(80))
    checkout_url: Mapped[str | None] = mapped_column(String(2048))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BillingEvent(Base):
    __tablename__ = "billing_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider_name: Mapped[SubscriptionProvider] = mapped_column(Enum(SubscriptionProvider, name="subscription_provider"), default=SubscriptionProvider.MERCADO_PAGO)
    external_event_id: Mapped[str] = mapped_column(String(255), unique=True)
    event_type: Mapped[str] = mapped_column(String(120))
    payload_hash: Mapped[str] = mapped_column(String(64))
    payload_private_reference: Mapped[str] = mapped_column(String(255))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_status: Mapped[BillingProcessingStatus] = mapped_column(Enum(BillingProcessingStatus, name="billing_processing_status"), default=BillingProcessingStatus.RECEIVED, index=True)
    error_message: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
