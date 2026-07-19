import logging
from uuid import UUID

from sic_api.modules.engagements.models import BookingStatus
from sic_api.modules.notifications.models import NotificationType
from sic_api.modules.notifications.service import NotificationService

from .models import ReviewStatus
from .repository import ReviewRecord, SqlAlchemyReviewRepository
from .schemas import PublicReviewView, ReviewCreate, ReviewDecision, ReviewView

logger = logging.getLogger(__name__)


class ReviewService:
    def __init__(self, repository: SqlAlchemyReviewRepository, notifications: NotificationService | None = None) -> None:
        self.repository = repository
        self.notifications = notifications

    @staticmethod
    def view(record: ReviewRecord) -> ReviewView:
        item = record.review
        return ReviewView(id=item.id, booking_id=item.booking_id, client_id=item.client_id, provider_id=item.provider_id, service_name=record.service_name, client_name=record.client_name, provider_name=record.provider_name, rating=item.rating, comment=item.comment, status=item.status, moderation_reason=item.moderation_reason, published_at=item.published_at, created_at=item.created_at, updated_at=item.updated_at)

    async def submit(self, client_id: UUID, booking_id: UUID, payload: ReviewCreate) -> ReviewView:
        context = await self.repository.booking_context(booking_id, client_id)
        if context.booking.status != BookingStatus.COMPLETED or context.booking.client_confirmed_at is None:
            raise ValueError("Only a completed booking confirmed by the client can be reviewed")
        record = await self.repository.create(context, payload)
        if self.notifications:
            try:
                await self.notifications.notify_user(context.provider_user_id, type=NotificationType.REVIEW_RECEIVED, title="Nueva opinión pendiente", body="Un cliente dejó una opinión verificada. Se publicará después de la moderación.", link_path="/prestador/opiniones", resource_type="review", resource_id=record.review.id, email_requested=True)
            except Exception as error:
                await self.repository.session.rollback()
                logger.exception("Could not create review notification", extra={"review_id": str(record.review.id), "error_type": type(error).__name__})
        return self.view(record)

    async def update(self, client_id: UUID, review_id: UUID, payload: ReviewCreate) -> ReviewView:
        return self.view(await self.repository.update(review_id, client_id, payload))

    async def client_reviews(self, client_id: UUID) -> list[ReviewView]:
        return [self.view(item) for item in await self.repository.list_client(client_id)]

    async def provider_reviews(self, provider_user_id: UUID) -> list[ReviewView]:
        return [self.view(item) for item in await self.repository.list_provider(provider_user_id)]

    async def admin_reviews(self, statuses: set[ReviewStatus] | None = None) -> list[ReviewView]:
        return [self.view(item) for item in await self.repository.list_admin(statuses)]

    async def moderate(self, reviewer_id: UUID, review_id: UUID, decision: ReviewDecision) -> ReviewView:
        record = await self.repository.moderate(review_id, reviewer_id, decision)
        if self.notifications:
            published = record.review.status == ReviewStatus.PUBLISHED
            try:
                await self.notifications.notify_user(record.review.client_id, type=NotificationType.REVIEW_MODERATED, title="Tu opinión fue revisada", body="Tu opinión verificada fue publicada." if published else "Tu opinión fue revisada y no está publicada.", link_path="/cuenta/contrataciones", resource_type="review", resource_id=record.review.id, email_requested=True)
            except Exception as error:
                await self.repository.session.rollback()
                logger.exception("Could not create review moderation notification", extra={"review_id": str(record.review.id), "error_type": type(error).__name__})
        return self.view(record)

    async def public_reviews(self, provider_id: UUID) -> list[PublicReviewView]:
        return [PublicReviewView(id=item.review.id, service_name=item.service_name, rating=item.review.rating, comment=item.review.comment, published_at=item.review.published_at) for item in await self.repository.list_public(provider_id) if item.review.published_at]
