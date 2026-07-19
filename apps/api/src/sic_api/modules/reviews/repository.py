from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sic_api.modules.catalog.models import Service
from sic_api.modules.engagements.models import Booking, BookingStatus
from sic_api.modules.provider_services.models import ProviderService
from sic_api.modules.providers.models import ProviderProfile
from sic_api.modules.users.models import User

from .models import Review, ReviewRevision, ReviewStatus
from .schemas import ReviewCreate, ReviewDecision


class ReviewNotFoundError(LookupError):
    pass


class ReviewConflictError(ValueError):
    pass


@dataclass(frozen=True)
class BookingReviewContext:
    booking: Booking
    service_name: str
    client_name: str
    provider_name: str
    provider_user_id: UUID


@dataclass(frozen=True)
class ReviewRecord:
    review: Review
    service_name: str
    client_name: str
    provider_name: str
    provider_user_id: UUID


class SqlAlchemyReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def booking_context(self, booking_id: UUID, client_id: UUID) -> BookingReviewContext:
        row = (await self.session.execute(
            select(Booking, Service.name, User.name, ProviderProfile.display_name, ProviderProfile.user_id)
            .join(ProviderService, ProviderService.id == Booking.provider_service_id)
            .join(Service, Service.id == ProviderService.service_id)
            .join(User, User.id == Booking.client_id)
            .join(ProviderProfile, ProviderProfile.id == Booking.provider_id)
            .where(Booking.id == booking_id, Booking.client_id == client_id)
            .with_for_update(of=Booking)
        )).one_or_none()
        if row is None:
            raise ReviewNotFoundError
        return BookingReviewContext(*row)

    async def _records(self, query) -> list[ReviewRecord]:
        rows = (await self.session.execute(
            query.add_columns(Service.name, User.name, ProviderProfile.display_name, ProviderProfile.user_id)
            .join(Booking, Booking.id == Review.booking_id)
            .join(ProviderService, ProviderService.id == Booking.provider_service_id)
            .join(Service, Service.id == ProviderService.service_id)
            .join(User, User.id == Review.client_id)
            .join(ProviderProfile, ProviderProfile.id == Review.provider_id)
        )).all()
        return [ReviewRecord(row[0], row[1], row[2], row[3], row[4]) for row in rows]

    async def create(self, context: BookingReviewContext, payload: ReviewCreate) -> ReviewRecord:
        item = Review(booking_id=context.booking.id, client_id=context.booking.client_id, provider_id=context.booking.provider_id, rating=payload.rating, comment=payload.comment.strip(), status=ReviewStatus.PENDING)
        self.session.add(item)
        try:
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise ReviewConflictError("This booking already has a review") from error
        return (await self._records(select(Review).where(Review.id == item.id)))[0]

    async def get(self, review_id: UUID, *, client_id: UUID | None = None) -> ReviewRecord:
        query = select(Review).where(Review.id == review_id)
        if client_id is not None:
            query = query.where(Review.client_id == client_id)
        records = await self._records(query)
        if not records:
            raise ReviewNotFoundError
        return records[0]

    async def list_client(self, client_id: UUID) -> list[ReviewRecord]:
        return await self._records(select(Review).where(Review.client_id == client_id).order_by(Review.created_at.desc()).limit(100))

    async def list_provider(self, provider_user_id: UUID) -> list[ReviewRecord]:
        provider_id = await self.session.scalar(select(ProviderProfile.id).where(ProviderProfile.user_id == provider_user_id))
        if provider_id is None:
            return []
        return await self._records(select(Review).where(Review.provider_id == provider_id).order_by(Review.created_at.desc()).limit(100))

    async def provider_id_by_slug(self, slug: str) -> UUID | None:
        return await self.session.scalar(select(ProviderProfile.id).where(ProviderProfile.slug == slug))

    async def list_admin(self, statuses: set[ReviewStatus] | None = None) -> list[ReviewRecord]:
        query = select(Review).order_by(Review.created_at).limit(200)
        if statuses:
            query = query.where(Review.status.in_(statuses))
        return await self._records(query)

    async def list_public(self, provider_id: UUID) -> list[ReviewRecord]:
        return await self._records(select(Review).where(Review.provider_id == provider_id, Review.status == ReviewStatus.PUBLISHED).order_by(Review.published_at.desc()).limit(50))

    async def update(self, review_id: UUID, client_id: UUID, payload: ReviewCreate) -> ReviewRecord:
        item = await self.session.scalar(select(Review).where(Review.id == review_id, Review.client_id == client_id).with_for_update())
        if item is None:
            raise ReviewNotFoundError
        if item.status == ReviewStatus.HIDDEN:
            raise ReviewConflictError("A hidden review cannot be edited")
        self.session.add(ReviewRevision(review_id=item.id, rating=item.rating, comment=item.comment, previous_status=item.status))
        was_published = item.status == ReviewStatus.PUBLISHED
        item.rating = payload.rating
        item.comment = payload.comment.strip()
        item.status = ReviewStatus.PENDING
        item.moderated_by = None
        item.moderation_reason = None
        item.published_at = None
        await self.session.commit()
        if was_published:
            await self.recompute_provider(item.provider_id)
        return await self.get(item.id, client_id=client_id)

    async def moderate(self, review_id: UUID, reviewer_id: UUID, decision: ReviewDecision) -> ReviewRecord:
        item = await self.session.scalar(select(Review).where(Review.id == review_id).with_for_update())
        if item is None:
            raise ReviewNotFoundError
        allowed = {
            "publish": {ReviewStatus.PENDING, ReviewStatus.REJECTED, ReviewStatus.HIDDEN},
            "reject": {ReviewStatus.PENDING, ReviewStatus.PUBLISHED},
            "hide": {ReviewStatus.PUBLISHED},
        }
        if item.status not in allowed[decision.action]:
            raise ReviewConflictError(f"Review cannot perform {decision.action} from {item.status.value}")
        item.status = {"publish": ReviewStatus.PUBLISHED, "reject": ReviewStatus.REJECTED, "hide": ReviewStatus.HIDDEN}[decision.action]
        item.moderated_by = reviewer_id
        item.moderation_reason = decision.reason.strip() if decision.reason else None
        item.published_at = datetime.now(timezone.utc) if item.status == ReviewStatus.PUBLISHED else None
        await self.session.commit()
        await self.recompute_provider(item.provider_id)
        return await self.get(item.id)

    async def recompute_provider(self, provider_id: UUID) -> None:
        count, average = (await self.session.execute(select(func.count(Review.id), func.avg(Review.rating)).where(Review.provider_id == provider_id, Review.status == ReviewStatus.PUBLISHED))).one()
        profile = await self.session.get(ProviderProfile, provider_id)
        if profile:
            profile.rating_count = int(count or 0)
            profile.rating_average = average or 0
            await self.session.commit()
