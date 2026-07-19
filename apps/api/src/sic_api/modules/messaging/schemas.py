from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from .models import MessageModerationStatus


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class MessageView(BaseModel):
    id: UUID
    sender_id: UUID
    sender_name: str
    is_mine: bool
    body: str
    moderation_status: MessageModerationStatus
    read_at: datetime | None
    created_at: datetime


class ConversationSummary(BaseModel):
    id: UUID
    request_id: UUID
    service_name: str
    request_title: str
    counterpart_name: str
    request_status: str
    booking_id: UUID | None
    last_message_at: datetime | None
    last_message_preview: str | None
    unread_count: int


class ConversationView(BaseModel):
    conversation: ConversationSummary
    messages: list[MessageView]
