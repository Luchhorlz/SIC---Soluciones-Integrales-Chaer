from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from .models import EmailDeliveryStatus, NotificationType


class NotificationView(BaseModel):
    id: UUID
    type: NotificationType
    title: str
    body: str
    link_path: str | None
    resource_type: str | None
    resource_id: UUID | None
    read_at: datetime | None
    email_status: EmailDeliveryStatus
    created_at: datetime


class NotificationPage(BaseModel):
    notifications: list[NotificationView]
    unread_count: int
