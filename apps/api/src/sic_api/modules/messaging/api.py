from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sic_api.db.session import get_session
from sic_api.modules.identity.permissions import CurrentPrincipal
from sic_api.modules.notifications.repository import SqlAlchemyNotificationRepository
from sic_api.modules.notifications.service import NotificationService

from .repository import ConversationNotFoundError, MessagingConflictError, SqlAlchemyMessagingRepository
from .schemas import ConversationSummary, ConversationView, MessageCreate
from .service import MessagingService

router = APIRouter(prefix="/v1/me/conversations", tags=["messaging"])


def workflow(session: AsyncSession) -> MessagingService:
    return MessagingService(SqlAlchemyMessagingRepository(session), NotificationService(SqlAlchemyNotificationRepository(session)))


def messaging_error(error: Exception) -> HTTPException:
    if isinstance(error, ConversationNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


@router.get("", response_model=list[ConversationSummary])
async def conversations(principal: CurrentPrincipal, session: AsyncSession = Depends(get_session)) -> list[ConversationSummary]:
    return await workflow(session).list(principal.user_id)


@router.get("/{request_id}", response_model=ConversationView)
async def conversation(request_id: UUID, principal: CurrentPrincipal, session: AsyncSession = Depends(get_session)) -> ConversationView:
    try:
        return await workflow(session).get(principal.user_id, request_id)
    except (ConversationNotFoundError, MessagingConflictError) as error:
        raise messaging_error(error) from error


@router.post("/{request_id}/messages", response_model=ConversationView, status_code=status.HTTP_201_CREATED)
async def send_message(request_id: UUID, payload: MessageCreate, principal: CurrentPrincipal, session: AsyncSession = Depends(get_session)) -> ConversationView:
    try:
        return await workflow(session).send(principal.user_id, request_id, payload)
    except (ConversationNotFoundError, MessagingConflictError, ValueError) as error:
        raise messaging_error(error) from error
