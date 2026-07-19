import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from sic_api.db.base import Base


class NotificationType(str, enum.Enum):
    REQUEST_RECEIVED = "REQUEST_RECEIVED"
    REQUEST_UPDATED = "REQUEST_UPDATED"
    QUOTE_RECEIVED = "QUOTE_RECEIVED"
    BOOKING_UPDATED = "BOOKING_UPDATED"
    MESSAGE_RECEIVED = "MESSAGE_RECEIVED"
    REVIEW_RECEIVED = "REVIEW_RECEIVED"
    REVIEW_MODERATED = "REVIEW_MODERATED"


class EmailDeliveryStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_read", "user_id", "read_at", "created_at"),
        Index("ix_notifications_email_pending", "email_status", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType, name="notification_type"))
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text)
    link_path: Mapped[str | None] = mapped_column(String(500))
    resource_type: Mapped[str | None] = mapped_column(String(80))
    resource_id: Mapped[UUID | None]
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_status: Mapped[EmailDeliveryStatus] = mapped_column(Enum(EmailDeliveryStatus, name="email_delivery_status"), default=EmailDeliveryStatus.PENDING)
    email_attempts: Mapped[int] = mapped_column(Integer, default=0)
    email_last_error: Mapped[str | None] = mapped_column(String(240))
    emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
