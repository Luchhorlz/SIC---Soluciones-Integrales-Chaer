from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from sic_api.db.session import get_session
from sic_api.modules.documents.repository import SqlAlchemyDocumentRepository
from sic_api.modules.documents.service import DocumentReadinessService
from sic_api.modules.identity.permissions import AdminPrincipal, ClientPrincipal, ProviderPrincipal
from sic_api.modules.notifications.repository import SqlAlchemyNotificationRepository
from sic_api.modules.notifications.service import NotificationService
from sic_api.modules.search.repository import SqlAlchemySearchRepository
from sic_api.modules.search.service import ProviderSearchService
from sic_api.modules.subscriptions.repository import SqlAlchemySubscriptionRepository
from sic_api.modules.subscriptions.service import SubscriptionVisibilityService

from .models import ReviewStatus
from .repository import ReviewConflictError, ReviewNotFoundError, SqlAlchemyReviewRepository
from .schemas import PublicReviewView, ReviewCreate, ReviewDecision, ReviewView
from .service import ReviewService

client_router = APIRouter(prefix="/v1/client/reviews", tags=["client-reviews"])
provider_router = APIRouter(prefix="/v1/provider/reviews", tags=["provider-reviews"])
admin_router = APIRouter(prefix="/v1/admin/reviews", tags=["admin-reviews"])
public_router = APIRouter(prefix="/v1/providers", tags=["public-reviews"])


def workflow(session: AsyncSession) -> ReviewService:
    return ReviewService(SqlAlchemyReviewRepository(session), NotificationService(SqlAlchemyNotificationRepository(session)))


def review_error(error: Exception) -> HTTPException:
    if isinstance(error, ReviewNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review or eligible booking not found")
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


@client_router.get("", response_model=list[ReviewView])
async def client_reviews(principal: ClientPrincipal, session: AsyncSession = Depends(get_session)) -> list[ReviewView]:
    return await workflow(session).client_reviews(principal.user_id)


@client_router.post("/bookings/{booking_id}", response_model=ReviewView, status_code=status.HTTP_201_CREATED)
async def submit_review(booking_id: UUID, payload: ReviewCreate, principal: ClientPrincipal, session: AsyncSession = Depends(get_session)) -> ReviewView:
    try:
        return await workflow(session).submit(principal.user_id, booking_id, payload)
    except (ReviewConflictError, ReviewNotFoundError, ValueError) as error:
        raise review_error(error) from error


@client_router.patch("/{review_id}", response_model=ReviewView)
async def update_review(review_id: UUID, payload: ReviewCreate, principal: ClientPrincipal, session: AsyncSession = Depends(get_session)) -> ReviewView:
    try:
        return await workflow(session).update(principal.user_id, review_id, payload)
    except (ReviewConflictError, ReviewNotFoundError, ValueError) as error:
        raise review_error(error) from error


@provider_router.get("", response_model=list[ReviewView])
async def provider_reviews(principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> list[ReviewView]:
    return await workflow(session).provider_reviews(principal.user_id)


@admin_router.get("", response_model=list[ReviewView])
async def admin_reviews(_principal: AdminPrincipal, statuses: Annotated[list[ReviewStatus] | None, Query()] = None, session: AsyncSession = Depends(get_session)) -> list[ReviewView]:
    return await workflow(session).admin_reviews(set(statuses) if statuses else None)


@admin_router.post("/{review_id}/moderate", response_model=ReviewView)
async def moderate_review(review_id: UUID, payload: ReviewDecision, principal: AdminPrincipal, session: AsyncSession = Depends(get_session)) -> ReviewView:
    try:
        return await workflow(session).moderate(principal.user_id, review_id, payload)
    except (ReviewConflictError, ReviewNotFoundError, ValueError) as error:
        raise review_error(error) from error


@public_router.get("/{provider_slug}/reviews", response_model=list[PublicReviewView])
async def public_reviews(provider_slug: str, session: AsyncSession = Depends(get_session)) -> list[PublicReviewView]:
    search = ProviderSearchService(SqlAlchemySearchRepository(session), DocumentReadinessService(SqlAlchemyDocumentRepository(session)), SubscriptionVisibilityService(SqlAlchemySubscriptionRepository(session)))
    if await search.profile(provider_slug) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visible provider not found")
    provider_id = await SqlAlchemyReviewRepository(session).provider_id_by_slug(provider_slug)
    if provider_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visible provider not found")
    return await workflow(session).public_reviews(provider_id)
