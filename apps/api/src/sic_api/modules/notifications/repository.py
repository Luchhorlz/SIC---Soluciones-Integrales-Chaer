from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from sic_api.modules.providers.models import ProviderProfile
from sic_api.modules.users.models import User

from .models import EmailDeliveryStatus, Notification, NotificationType


class NotificationNotFoundError(LookupError):
    pass


@dataclass(frozen=True)
class PendingEmail:
    notification: Notification
    recipient_email: str
    recipient_name: str


class SqlAlchemyNotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def provider_user_id(self, provider_id: UUID) -> UUID | None:
        return await self.session.scalar(select(ProviderProfile.user_id).where(ProviderProfile.id == provider_id))

    async def create(self, *, user_id: UUID, type: NotificationType, title: str, body: str, link_path: str | None, resource_type: str | None, resource_id: UUID | None, email_requested: bool) -> Notification:
        item = Notification(user_id=user_id, type=type, title=title, body=body, link_path=link_path, resource_type=resource_type, resource_id=resource_id, email_status=EmailDeliveryStatus.PENDING if email_requested else EmailDeliveryStatus.SKIPPED)
        self.session.add(item)
        await self.session.commit()
        return item

    async def list_for_user(self, user_id: UUID) -> tuple[list[Notification], int]:
        items = list((await self.session.scalars(select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at.desc()).limit(100))).all())
        unread = int(await self.session.scalar(select(func.count(Notification.id)).where(Notification.user_id == user_id, Notification.read_at.is_(None))) or 0)
        return items, unread

    async def mark_read(self, user_id: UUID, notification_id: UUID) -> Notification:
        item = await self.session.scalar(select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id).with_for_update())
        if item is None:
            raise NotificationNotFoundError
        if item.read_at is None:
            item.read_at = datetime.now(timezone.utc)
            await self.session.commit()
        return item

    async def mark_all_read(self, user_id: UUID) -> None:
        await self.session.execute(update(Notification).where(Notification.user_id == user_id, Notification.read_at.is_(None)).values(read_at=datetime.now(timezone.utc)))
        await self.session.commit()

    async def pending_emails(self, limit: int = 50) -> list[PendingEmail]:
        rows = (await self.session.execute(
            select(Notification, User.email, User.name)
            .join(User, User.id == Notification.user_id)
            .where(Notification.email_status == EmailDeliveryStatus.PENDING, Notification.email_attempts < 5)
            .order_by(Notification.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True, of=Notification)
        )).all()
        return [PendingEmail(row[0], row[1], row[2]) for row in rows]

    async def email_sent(self, notification: Notification) -> None:
        notification.email_status = EmailDeliveryStatus.SENT
        notification.email_attempts += 1
        notification.email_last_error = None
        notification.emailed_at = datetime.now(timezone.utc)
        await self.session.commit()

    async def email_failed(self, notification: Notification, reason: str) -> None:
        notification.email_attempts += 1
        notification.email_last_error = reason[:240]
        if notification.email_attempts >= 5:
            notification.email_status = EmailDeliveryStatus.FAILED
        await self.session.commit()
