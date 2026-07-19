import enum
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from geoalchemy2 import Geography
from geoalchemy2.elements import WKBElement
from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from sic_api.db.base import Base


class ProviderProfileStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    PAUSED = "PAUSED"
    SUSPENDED = "SUSPENDED"
    BLOCKED = "BLOCKED"


class SubscriptionVisibilityStatus(str, enum.Enum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    ACTIVE = "ACTIVE"
    AUTHORIZED = "AUTHORIZED"
    INACTIVE = "INACTIVE"


class ProviderProfile(Base):
    __tablename__ = "provider_profiles"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    display_name: Mapped[str] = mapped_column(String(180))
    slug: Mapped[str] = mapped_column(String(220), unique=True)
    business_name: Mapped[str | None] = mapped_column(String(180))
    bio: Mapped[str | None] = mapped_column(Text)
    experience_years: Mapped[int | None] = mapped_column(Integer)
    base_address_id: Mapped[UUID | None] = mapped_column(ForeignKey("addresses.id", ondelete="RESTRICT"))
    base_point: Mapped[WKBElement | None] = mapped_column(Geography(geometry_type="POINT", srid=4326, spatial_index=False))
    profile_status: Mapped[ProviderProfileStatus] = mapped_column(Enum(ProviderProfileStatus, name="provider_profile_status"), default=ProviderProfileStatus.DRAFT)
    subscription_visibility_status: Mapped[SubscriptionVisibilityStatus] = mapped_column(Enum(SubscriptionVisibilityStatus, name="subscription_visibility_status"), default=SubscriptionVisibilityStatus.NOT_CONFIGURED)
    rating_average: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    completed_services_count: Mapped[int] = mapped_column(Integer, default=0)
    response_rate: Mapped[float] = mapped_column(Float, default=0)
    average_response_minutes: Mapped[int | None] = mapped_column(Integer)
    profile_completeness: Mapped[int] = mapped_column(Integer, default=0)
    is_identity_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ProviderPortfolioItem(Base):
    __tablename__ = "provider_portfolio_items"
    __table_args__ = (UniqueConstraint("provider_id", "position", name="uq_provider_portfolio_position"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider_id: Mapped[UUID] = mapped_column(ForeignKey("provider_profiles.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(140))
    description: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
