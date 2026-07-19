from uuid import UUID

from .models import Notification, NotificationType
from .repository import SqlAlchemyNotificationRepository
from .schemas import NotificationPage, NotificationView


class NotificationService:
    def __init__(self, repository: SqlAlchemyNotificationRepository) -> None:
        self.repository = repository

    @staticmethod
    def view(item: Notification) -> NotificationView:
        return NotificationView.model_validate(item, from_attributes=True)

    async def notify_user(self, user_id: UUID, *, type: NotificationType, title: str, body: str, link_path: str | None, resource_type: str | None, resource_id: UUID | None, email_requested: bool = True) -> NotificationView:
        if link_path is not None and (not link_path.startswith("/") or link_path.startswith("//")):
            raise ValueError("Notification links must be local application paths")
        item = await self.repository.create(user_id=user_id, type=type, title=title[:160], body=body[:1000], link_path=link_path, resource_type=resource_type, resource_id=resource_id, email_requested=email_requested)
        return self.view(item)

    async def notify_provider(self, provider_id: UUID, **kwargs) -> NotificationView | None:
        user_id = await self.repository.provider_user_id(provider_id)
        return await self.notify_user(user_id, **kwargs) if user_id else None

    async def page(self, user_id: UUID) -> NotificationPage:
        items, unread = await self.repository.list_for_user(user_id)
        return NotificationPage(notifications=[self.view(item) for item in items], unread_count=unread)

    async def mark_read(self, user_id: UUID, notification_id: UUID) -> NotificationView:
        return self.view(await self.repository.mark_read(user_id, notification_id))

    async def mark_all_read(self, user_id: UUID) -> None:
        await self.repository.mark_all_read(user_id)
