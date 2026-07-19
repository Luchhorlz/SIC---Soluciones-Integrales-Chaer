from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sic_api.modules.catalog.models import Service
from sic_api.modules.engagements.models import Booking, ServiceRequest, ServiceRequestStatus
from sic_api.modules.providers.models import ProviderProfile
from sic_api.modules.provider_services.models import ProviderService
from sic_api.modules.users.models import User

from .models import Conversation, Message, MessageModerationStatus


class ConversationNotFoundError(LookupError):
    pass


class MessagingConflictError(ValueError):
    pass


@dataclass(frozen=True)
class ConversationRecord:
    conversation: Conversation
    request: ServiceRequest
    service_name: str
    client_name: str
    provider_name: str
    provider_user_id: UUID
    booking_id: UUID | None
    messages: tuple[tuple[Message, str], ...] = ()


class SqlAlchemyMessagingRepository:
    closed_request_statuses = {ServiceRequestStatus.DECLINED, ServiceRequestStatus.CANCELLED, ServiceRequestStatus.EXPIRED}

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _context(self, request_id: UUID, actor_user_id: UUID) -> tuple[ServiceRequest, str, str, str, UUID, UUID | None]:
        row = (await self.session.execute(
            select(ServiceRequest, Service.name, User.name, ProviderProfile.display_name, ProviderProfile.user_id, Booking.id)
            .join(ProviderService, ProviderService.id == ServiceRequest.provider_service_id)
            .join(Service, Service.id == ProviderService.service_id)
            .join(User, User.id == ServiceRequest.client_id)
            .join(ProviderProfile, ProviderProfile.id == ServiceRequest.provider_id)
            .outerjoin(Booking, Booking.request_id == ServiceRequest.id)
            .where(ServiceRequest.id == request_id, or_(ServiceRequest.client_id == actor_user_id, ProviderProfile.user_id == actor_user_id))
        )).one_or_none()
        if row is None:
            raise ConversationNotFoundError
        return row

    async def ensure(self, request_id: UUID, actor_user_id: UUID) -> Conversation:
        await self._context(request_id, actor_user_id)
        item = await self.session.scalar(select(Conversation).where(Conversation.request_id == request_id))
        if item:
            return item
        item = Conversation(request_id=request_id)
        self.session.add(item)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            item = await self.session.scalar(select(Conversation).where(Conversation.request_id == request_id))
            if item is None:
                raise
        return item

    async def _record(self, conversation: Conversation, actor_user_id: UUID, *, include_messages: bool) -> ConversationRecord:
        request, service_name, client_name, provider_name, provider_user_id, booking_id = await self._context(conversation.request_id, actor_user_id)
        messages: tuple[tuple[Message, str], ...] = ()
        if include_messages:
            rows = list((await self.session.execute(
                select(Message, User.name)
                .join(User, User.id == Message.sender_id)
                .where(Message.conversation_id == conversation.id, Message.moderation_status != MessageModerationStatus.HIDDEN)
                .order_by(Message.created_at.desc(), Message.id.desc())
                .limit(300)
            )).all())
            rows.reverse()
            messages = tuple((row[0], row[1]) for row in rows)
        return ConversationRecord(conversation, request, service_name, client_name, provider_name, provider_user_id, booking_id, messages)

    async def get(self, request_id: UUID, actor_user_id: UUID, *, mark_read: bool = True) -> ConversationRecord:
        conversation = await self.ensure(request_id, actor_user_id)
        if mark_read:
            await self.session.execute(update(Message).where(Message.conversation_id == conversation.id, Message.sender_id != actor_user_id, Message.read_at.is_(None)).values(read_at=datetime.now(timezone.utc)))
            await self.session.commit()
        return await self._record(conversation, actor_user_id, include_messages=True)

    async def list(self, actor_user_id: UUID) -> list[ConversationRecord]:
        conversations = list((await self.session.scalars(
            select(Conversation)
            .join(ServiceRequest, ServiceRequest.id == Conversation.request_id)
            .join(ProviderProfile, ProviderProfile.id == ServiceRequest.provider_id)
            .where(or_(ServiceRequest.client_id == actor_user_id, ProviderProfile.user_id == actor_user_id))
            .order_by(Conversation.last_message_at.desc().nullslast(), Conversation.created_at.desc())
            .limit(100)
        )).all())
        return [await self._record(item, actor_user_id, include_messages=True) for item in conversations]

    async def send(self, request_id: UUID, sender_id: UUID, body: str) -> tuple[ConversationRecord, UUID]:
        conversation = await self.ensure(request_id, sender_id)
        conversation = await self.session.scalar(select(Conversation).where(Conversation.id == conversation.id).with_for_update())
        if conversation is None:
            raise ConversationNotFoundError
        request, _service_name, _client_name, _provider_name, provider_user_id, booking_id = await self._context(request_id, sender_id)
        if request.status in self.closed_request_statuses and booking_id is None:
            raise MessagingConflictError("This conversation is read-only because the request is closed")
        since = datetime.now(timezone.utc) - timedelta(minutes=1)
        recent = int(await self.session.scalar(select(func.count(Message.id)).where(Message.sender_id == sender_id, Message.created_at >= since)) or 0)
        if recent >= 20:
            raise MessagingConflictError("Message rate limit exceeded; try again in one minute")
        item = Message(conversation_id=conversation.id, sender_id=sender_id, body=body.strip(), moderation_status=MessageModerationStatus.VISIBLE)
        self.session.add(item)
        conversation.last_message_at = datetime.now(timezone.utc)
        await self.session.commit()
        recipient_id = provider_user_id if sender_id == request.client_id else request.client_id
        return await self._record(conversation, sender_id, include_messages=True), recipient_id
