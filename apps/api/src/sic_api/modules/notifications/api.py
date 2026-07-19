from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from sic_api.db.session import get_session
from sic_api.modules.identity.permissions import CurrentPrincipal

from .repository import NotificationNotFoundError, SqlAlchemyNotificationRepository
from .schemas import NotificationPage, NotificationView
from .service import NotificationService

router = APIRouter(prefix="/v1/me/notifications", tags=["notifications"])


def workflow(session: AsyncSession) -> NotificationService:
    return NotificationService(SqlAlchemyNotificationRepository(session))


@router.get("", response_model=NotificationPage)
async def notifications(principal: CurrentPrincipal, session: AsyncSession = Depends(get_session)) -> NotificationPage:
    return await workflow(session).page(principal.user_id)


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_notifications_read(principal: CurrentPrincipal, session: AsyncSession = Depends(get_session)) -> Response:
    await workflow(session).mark_all_read(principal.user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{notification_id}/read", response_model=NotificationView)
async def mark_notification_read(notification_id: UUID, principal: CurrentPrincipal, session: AsyncSession = Depends(get_session)) -> NotificationView:
    try:
        return await workflow(session).mark_read(principal.user_id, notification_id)
    except NotificationNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found") from error
