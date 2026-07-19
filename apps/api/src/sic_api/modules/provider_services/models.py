import enum
from datetime import datetime, time
from decimal import Decimal
from uuid import UUID, uuid4

from geoalchemy2 import Geography
from geoalchemy2.elements import WKBElement
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, Time, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from sic_api.db.base import Base


class ProviderServiceStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_DOCUMENTS = "PENDING_DOCUMENTS"
    PENDING_REVIEW = "PENDING_REVIEW"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


class PricingType(str, enum.Enum):
    FIXED = "FIXED"
    FROM = "FROM"
    QUOTE = "QUOTE"
    HOURLY = "HOURLY"
    PER_SESSION = "PER_SESSION"
    PER_UNIT = "PER_UNIT"


class ProviderModality(str, enum.Enum):
    AT_CLIENT_ADDRESS = "AT_CLIENT_ADDRESS"
    REMOTE = "REMOTE"
    HYBRID = "HYBRID"
    AT_PROVIDER_LOCATION = "AT_PROVIDER_LOCATION"
    PICKUP_DELIVERY = "PICKUP_DELIVERY"


class ProviderService(Base):
    __tablename__ = "provider_services"
    __table_args__ = (UniqueConstraint("provider_id", "service_id", name="uq_provider_catalog_service"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider_id: Mapped[UUID] = mapped_column(ForeignKey("provider_profiles.id", ondelete="CASCADE"), index=True)
    service_id: Mapped[UUID] = mapped_column(ForeignKey("services.id", ondelete="RESTRICT"), index=True)
    status: Mapped[ProviderServiceStatus] = mapped_column(Enum(ProviderServiceStatus, name="provider_service_status"), default=ProviderServiceStatus.PENDING_DOCUMENTS)
    headline: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    pricing_type: Mapped[PricingType] = mapped_column(Enum(PricingType, name="provider_pricing_type"))
    price_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    price_currency: Mapped[str] = mapped_column(String(3), default="ARS")
    estimated_duration_minutes: Mapped[int | None] = mapped_column(Integer)
    guarantee_days: Mapped[int | None] = mapped_column(Integer)
    accepts_urgent: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_quote_details: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ProviderServiceModality(Base):
    __tablename__ = "provider_service_modalities"

    provider_service_id: Mapped[UUID] = mapped_column(ForeignKey("provider_services.id", ondelete="CASCADE"), primary_key=True)
    modality: Mapped[ProviderModality] = mapped_column(Enum(ProviderModality, name="provider_modality"), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class ProviderServiceArea(Base):
    __tablename__ = "provider_service_areas"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider_service_id: Mapped[UUID] = mapped_column(ForeignKey("provider_services.id", ondelete="CASCADE"), unique=True)
    center_address_id: Mapped[UUID] = mapped_column(ForeignKey("addresses.id", ondelete="RESTRICT"))
    center: Mapped[WKBElement] = mapped_column(Geography(geometry_type="POINT", srid=4326, spatial_index=False))
    radius_meters: Mapped[int] = mapped_column(Integer)
    urgent_radius_meters: Mapped[int | None] = mapped_column(Integer)
    travel_fee_policy: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AvailabilityRule(Base):
    __tablename__ = "availability_rules"
    __table_args__ = (UniqueConstraint("provider_service_id", "day_of_week", "start_time", "end_time", name="uq_provider_service_availability_rule"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider_id: Mapped[UUID] = mapped_column(ForeignKey("provider_profiles.id", ondelete="CASCADE"), index=True)
    provider_service_id: Mapped[UUID] = mapped_column(ForeignKey("provider_services.id", ondelete="CASCADE"), index=True)
    day_of_week: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    timezone: Mapped[str] = mapped_column(String(64), default="America/Argentina/Buenos_Aires")
    slot_duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AvailabilityException(Base):
    __tablename__ = "availability_exceptions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider_id: Mapped[UUID] = mapped_column(ForeignKey("provider_profiles.id", ondelete="CASCADE"), index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(String(240))
    is_available_override: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
