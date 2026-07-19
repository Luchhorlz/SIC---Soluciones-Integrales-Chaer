import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select

from sic_api.db.session import SessionFactory
from sic_api.modules.catalog.models import Service
from sic_api.modules.engagements.models import Booking, BookingStatus, ServiceRequest, ServiceRequestStatus
from sic_api.modules.favorites.models import FavoriteProvider
from sic_api.modules.favorites.repository import SqlAlchemyFavoriteRepository
from sic_api.modules.favorites.service import FavoriteService
from sic_api.modules.messaging.models import Conversation, Message
from sic_api.modules.messaging.repository import ConversationNotFoundError, MessagingConflictError, SqlAlchemyMessagingRepository
from sic_api.modules.messaging.schemas import MessageCreate
from sic_api.modules.messaging.service import MessagingService
from sic_api.modules.provider_services.models import PricingType, ProviderModality, ProviderService, ProviderServiceModality, ProviderServiceStatus
from sic_api.modules.providers.models import ProviderProfile, ProviderProfileStatus
from sic_api.modules.reviews.models import Review, ReviewRevision, ReviewStatus
from sic_api.modules.reviews.repository import ReviewConflictError, SqlAlchemyReviewRepository
from sic_api.modules.reviews.schemas import ReviewCreate, ReviewDecision
from sic_api.modules.reviews.service import ReviewService
from sic_api.modules.users.models import User

pytestmark = pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL communication integration runs in CI")


class VisibleProviderReader:
    def __init__(self, profile: ProviderProfile) -> None:
        self.profile_value = SimpleNamespace(
            slug=profile.slug,
            display_name=profile.display_name,
            business_name=profile.business_name,
            rating_average=float(profile.rating_average),
            rating_count=profile.rating_count,
            is_identity_verified=profile.is_identity_verified,
        )

    async def profile(self, slug: str):
        return self.profile_value if slug == self.profile_value.slug else None


@pytest.mark.anyio
async def test_contextual_messages_favorites_and_verified_review_lifecycle() -> None:
    provider_user_id, client_id, outsider_id, admin_id, provider_id = uuid4(), uuid4(), uuid4(), uuid4(), uuid4()
    request_id, closed_request_id, booking_id = uuid4(), uuid4(), uuid4()
    async with SessionFactory() as session:
        try:
            catalog_service = await session.scalar(select(Service).where(Service.is_active.is_(True)).limit(1))
            assert catalog_service is not None
            session.add_all([
                User(id=provider_user_id, google_subject=f"comm-provider-{provider_user_id}", email=f"comm-provider-{provider_user_id}@example.invalid", name="Provider messages"),
                User(id=client_id, google_subject=f"comm-client-{client_id}", email=f"comm-client-{client_id}@example.invalid", name="Client messages"),
                User(id=outsider_id, google_subject=f"comm-outsider-{outsider_id}", email=f"comm-outsider-{outsider_id}@example.invalid", name="Outside messages"),
                User(id=admin_id, google_subject=f"comm-admin-{admin_id}", email=f"comm-admin-{admin_id}@example.invalid", name="Review moderator"),
            ])
            await session.flush()
            profile = ProviderProfile(id=provider_id, user_id=provider_user_id, display_name="Provider verified", slug=f"provider-verified-{provider_id.hex}", business_name="SIC Test", bio="Profile used by the communication integration test.", profile_status=ProviderProfileStatus.APPROVED, profile_completeness=100, is_identity_verified=True)
            session.add(profile)
            await session.flush()
            offer = ProviderService(provider_id=provider_id, service_id=catalog_service.id, status=ProviderServiceStatus.ACTIVE, headline="Verified remote service", description="Offer used to verify private messaging and review rules.", pricing_type=PricingType.QUOTE, price_amount=None, price_currency="ARS", estimated_duration_minutes=60, accepts_urgent=False, requires_quote_details=True)
            session.add(offer)
            await session.flush()
            session.add(ProviderServiceModality(provider_service_id=offer.id, modality=ProviderModality.REMOTE, enabled=True))
            now = datetime.now(timezone.utc)
            session.add_all([
                ServiceRequest(id=request_id, client_id=client_id, provider_id=provider_id, provider_service_id=offer.id, selected_modality=ProviderModality.REMOTE, title="Valid contextual request", description="A private request that authorizes a conversation.", status=ServiceRequestStatus.CONVERTED_TO_BOOKING),
                ServiceRequest(id=closed_request_id, client_id=client_id, provider_id=provider_id, provider_service_id=offer.id, selected_modality=ProviderModality.REMOTE, title="Closed contextual request", description="A cancelled request cannot receive new messages.", status=ServiceRequestStatus.CANCELLED),
                Booking(id=booking_id, request_id=request_id, client_id=client_id, provider_id=provider_id, provider_service_id=offer.id, modality=ProviderModality.REMOTE, starts_at=now - timedelta(hours=2), ends_at=now - timedelta(hours=1), agreed_price=None, currency="ARS", status=BookingStatus.COMPLETED, completed_at=now - timedelta(hours=1), client_confirmed_at=now),
            ])
            await session.commit()

            messaging = MessagingService(SqlAlchemyMessagingRepository(session))
            sent = await messaging.send(client_id, request_id, MessageCreate(body="Hola, confirmo que el trabajo ya fue realizado."))
            assert sent.messages[-1].is_mine is True
            assert sent.conversation.booking_id == booking_id
            with pytest.raises(ConversationNotFoundError):
                await messaging.get(outsider_id, request_id)
            received = await messaging.get(provider_user_id, request_id)
            assert received.messages[-1].is_mine is False
            assert received.messages[-1].read_at is not None
            with pytest.raises(MessagingConflictError, match="read-only"):
                await messaging.send(client_id, closed_request_id, MessageCreate(body="Este mensaje no debe persistir."))

            favorites = FavoriteService(SqlAlchemyFavoriteRepository(session), VisibleProviderReader(profile))
            added = await favorites.add(client_id, profile.slug)
            assert added.provider_slug == profile.slug
            assert [item.provider_slug for item in await favorites.list(client_id)] == [profile.slug]
            await favorites.remove(client_id, profile.slug)
            assert await favorites.list(client_id) == []

            reviews = ReviewService(SqlAlchemyReviewRepository(session))
            submitted = await reviews.submit(client_id, booking_id, ReviewCreate(rating=5, comment="Excelente atención, puntualidad y resolución del trabajo."))
            assert submitted.status == ReviewStatus.PENDING
            with pytest.raises(ReviewConflictError, match="already"):
                await reviews.submit(client_id, booking_id, ReviewCreate(rating=4, comment="Una segunda reseña no debe ser aceptada para el mismo turno."))
            published = await reviews.moderate(admin_id, submitted.id, ReviewDecision(action="publish"))
            assert published.status == ReviewStatus.PUBLISHED
            await session.refresh(profile)
            assert profile.rating_count == 1
            assert float(profile.rating_average) == 5.0
            edited = await reviews.update(client_id, submitted.id, ReviewCreate(rating=4, comment="Actualizo el detalle, manteniendo una experiencia positiva."))
            assert edited.status == ReviewStatus.PENDING
            assert await session.scalar(select(func.count(ReviewRevision.id)).where(ReviewRevision.review_id == submitted.id)) == 1
            await session.refresh(profile)
            assert profile.rating_count == 0
            await reviews.moderate(admin_id, submitted.id, ReviewDecision(action="publish"))
            await session.refresh(profile)
            assert profile.rating_count == 1
            assert float(profile.rating_average) == 4.0
        finally:
            await session.rollback()
            await session.execute(delete(ReviewRevision).where(ReviewRevision.review_id.in_(select(Review.id).where(Review.provider_id == provider_id))))
            await session.execute(delete(Review).where(Review.provider_id == provider_id))
            await session.execute(delete(FavoriteProvider).where(FavoriteProvider.provider_id == provider_id))
            await session.execute(delete(Message).where(Message.conversation_id.in_(select(Conversation.id).join(ServiceRequest, ServiceRequest.id == Conversation.request_id).where(ServiceRequest.provider_id == provider_id))))
            await session.execute(delete(Conversation).where(Conversation.request_id.in_(select(ServiceRequest.id).where(ServiceRequest.provider_id == provider_id))))
            await session.execute(delete(Booking).where(Booking.provider_id == provider_id))
            await session.execute(delete(ServiceRequest).where(ServiceRequest.provider_id == provider_id))
            await session.execute(delete(ProviderServiceModality).where(ProviderServiceModality.provider_service_id.in_(select(ProviderService.id).where(ProviderService.provider_id == provider_id))))
            await session.execute(delete(ProviderService).where(ProviderService.provider_id == provider_id))
            await session.execute(delete(ProviderProfile).where(ProviderProfile.id == provider_id))
            await session.execute(delete(User).where(User.id.in_([provider_user_id, client_id, outsider_id, admin_id])))
            await session.commit()
