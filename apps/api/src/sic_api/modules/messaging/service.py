import logging
from uuid import UUID

from sic_api.modules.notifications.models import NotificationType
from sic_api.modules.notifications.service import NotificationService

from .models import Message
from .repository import ConversationRecord, SqlAlchemyMessagingRepository
from .schemas import ConversationSummary, ConversationView, MessageCreate, MessageView

logger = logging.getLogger(__name__)


class MessagingService:
    def __init__(self, repository: SqlAlchemyMessagingRepository, notifications: NotificationService | None = None) -> None:
        self.repository = repository
        self.notifications = notifications

    @staticmethod
    def _message(item: Message, sender_name: str, actor_user_id: UUID) -> MessageView:
        return MessageView(id=item.id, sender_id=item.sender_id, sender_name=sender_name, is_mine=item.sender_id == actor_user_id, body=item.body, moderation_status=item.moderation_status, read_at=item.read_at, created_at=item.created_at)

    @classmethod
    def _summary(cls, record: ConversationRecord, actor_user_id: UUID) -> ConversationSummary:
        last = record.messages[-1][0] if record.messages else None
        counterpart = record.provider_name if record.request.client_id == actor_user_id else record.client_name
        return ConversationSummary(
            id=record.conversation.id, request_id=record.request.id, service_name=record.service_name, request_title=record.request.title,
            counterpart_name=counterpart, request_status=record.request.status.value, booking_id=record.booking_id,
            last_message_at=record.conversation.last_message_at, last_message_preview=last.body[:120] if last else None,
            unread_count=sum(1 for message, _name in record.messages if message.sender_id != actor_user_id and message.read_at is None),
        )

    @classmethod
    def _view(cls, record: ConversationRecord, actor_user_id: UUID) -> ConversationView:
        return ConversationView(conversation=cls._summary(record, actor_user_id), messages=[cls._message(item, name, actor_user_id) for item, name in record.messages])

    async def list(self, actor_user_id: UUID) -> list[ConversationSummary]:
        return [self._summary(item, actor_user_id) for item in await self.repository.list(actor_user_id)]

    async def get(self, actor_user_id: UUID, request_id: UUID) -> ConversationView:
        return self._view(await self.repository.get(request_id, actor_user_id), actor_user_id)

    async def send(self, actor_user_id: UUID, request_id: UUID, payload: MessageCreate) -> ConversationView:
        body = payload.body.strip()
        if not body:
            raise ValueError("Message body cannot be blank")
        record, recipient_id = await self.repository.send(request_id, actor_user_id, body)
        if self.notifications:
            recipient_path = "/prestador/mensajes" if record.request.client_id == actor_user_id else "/cuenta/mensajes"
            try:
                await self.notifications.notify_user(recipient_id, type=NotificationType.MESSAGE_RECEIVED, title="Nuevo mensaje privado", body="Tenés un mensaje nuevo en una conversación de servicio.", link_path=f"{recipient_path}?request={request_id}", resource_type="service_request", resource_id=request_id, email_requested=False)
            except Exception as error:
                await self.repository.session.rollback()
                logger.exception("Could not create message notification", extra={"request_id": str(request_id), "error_type": type(error).__name__})
        return self._view(record, actor_user_id)
