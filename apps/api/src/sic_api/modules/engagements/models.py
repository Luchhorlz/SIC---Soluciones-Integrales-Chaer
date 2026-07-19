import enum
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from sic_api.db.base import Base
from sic_api.modules.provider_services.models import ProviderModality


class ServiceRequestStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    REQUESTED = "REQUESTED"
    VIEWED = "VIEWED"
    QUOTED = "QUOTED"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    CONVERTED_TO_BOOKING = "CONVERTED_TO_BOOKING"


class QuoteStatus(str, enum.Enum):
    SENT = "SENT"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    WITHDRAWN = "WITHDRAWN"


class BookingStatus(str, enum.Enum):
    PENDING_PROVIDER = "PENDING_PROVIDER"
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED_BY_CLIENT = "CANCELLED_BY_CLIENT"
    CANCELLED_BY_PROVIDER = "CANCELLED_BY_PROVIDER"
    NO_SHOW = "NO_SHOW"
    DISPUTED = "DISPUTED"


class ServiceRequest(Base):
    __tablename__ = "service_requests"
    __table_args__ = (
        Index("ix_service_requests_client_status", "client_id", "status", "created_at"),
        Index("ix_service_requests_provider_status", "provider_id", "status", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    provider_id: Mapped[UUID] = mapped_column(ForeignKey("provider_profiles.id", ondelete="RESTRICT"))
    provider_service_id: Mapped[UUID] = mapped_column(ForeignKey("provider_services.id", ondelete="RESTRICT"))
    client_address_id: Mapped[UUID | None] = mapped_column(ForeignKey("addresses.id", ondelete="RESTRICT"))
    selected_modality: Mapped[ProviderModality] = mapped_column(Enum(ProviderModality, name="provider_modality"))
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    preferred_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[ServiceRequestStatus] = mapped_column(Enum(ServiceRequestStatus, name="service_request_status"), default=ServiceRequestStatus.REQUESTED)
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RequestAttachment(Base):
    __tablename__ = "request_attachments"
    __table_args__ = (UniqueConstraint("media_file_id", name="uq_request_attachment_media"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    request_id: Mapped[UUID] = mapped_column(ForeignKey("service_requests.id", ondelete="CASCADE"), index=True)
    media_file_id: Mapped[UUID] = mapped_column(ForeignKey("media_files.id", ondelete="RESTRICT"))
    uploaded_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Quote(Base):
    __tablename__ = "quotes"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_quote_amount_positive"),
        Index("ix_quotes_request_status", "request_id", "status", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    request_id: Mapped[UUID] = mapped_column(ForeignKey("service_requests.id", ondelete="RESTRICT"))
    provider_id: Mapped[UUID] = mapped_column(ForeignKey("provider_profiles.id", ondelete="RESTRICT"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="ARS")
    description: Mapped[str] = mapped_column(Text)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[QuoteStatus] = mapped_column(Enum(QuoteStatus, name="quote_status"), default=QuoteStatus.SENT)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint("request_id", name="uq_booking_request"),
        CheckConstraint("ends_at > starts_at", name="ck_booking_valid_schedule"),
        CheckConstraint("agreed_price IS NULL OR agreed_price > 0", name="ck_booking_price_positive"),
        ExcludeConstraint(
            ("provider_id", "="),
            (func.tstzrange(text("starts_at"), text("ends_at"), "[)"), "&&"),
            where=text("status IN ('CONFIRMED', 'IN_PROGRESS')"),
            using="gist",
            name="ex_bookings_provider_schedule",
        ),
        Index("ix_bookings_client_status", "client_id", "status", "starts_at"),
        Index("ix_bookings_provider_status", "provider_id", "status", "starts_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    request_id: Mapped[UUID] = mapped_column(ForeignKey("service_requests.id", ondelete="RESTRICT"))
    client_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    provider_id: Mapped[UUID] = mapped_column(ForeignKey("provider_profiles.id", ondelete="RESTRICT"))
    provider_service_id: Mapped[UUID] = mapped_column(ForeignKey("provider_services.id", ondelete="RESTRICT"))
    modality: Mapped[ProviderModality] = mapped_column(Enum(ProviderModality, name="provider_modality"))
    address_snapshot_encrypted: Mapped[str | None] = mapped_column(Text)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    agreed_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="ARS")
    status: Mapped[BookingStatus] = mapped_column(Enum(BookingStatus, name="booking_status"), default=BookingStatus.CONFIRMED)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    client_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dispute_reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
