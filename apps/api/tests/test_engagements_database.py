import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from sic_api.db.session import SessionFactory
from sic_api.modules.addresses.repository import SqlAlchemyAddressRepository
from sic_api.modules.catalog.models import Service
from sic_api.modules.documents.repository import SqlAlchemyDocumentRepository
from sic_api.modules.documents.service import DocumentReadinessService
from sic_api.modules.engagements.models import Booking, BookingStatus, Quote, ServiceRequest, ServiceRequestStatus
from sic_api.modules.engagements.repository import EngagementConflictError, EngagementNotFoundError, SqlAlchemyEngagementRepository
from sic_api.modules.engagements.schemas import BookingSchedule, QuoteCreate, QuoteDecision, ServiceRequestCreate
from sic_api.modules.engagements.service import EngagementService
from sic_api.modules.engagements.state import InvalidTransitionError
from sic_api.modules.provider_services.models import PricingType, ProviderModality, ProviderService, ProviderServiceModality, ProviderServiceStatus
from sic_api.modules.providers.models import ProviderProfile, ProviderProfileStatus
from sic_api.modules.subscriptions.models import BillingFrequency, ProviderSubscription, ProviderSubscriptionStatus, SubscriptionPlan
from sic_api.modules.subscriptions.repository import SqlAlchemySubscriptionRepository
from sic_api.modules.subscriptions.service import SubscriptionVisibilityService
from sic_api.modules.users.models import User

pytestmark = pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL engagement integration runs in CI")


@pytest.mark.anyio
async def test_private_quote_booking_abac_state_and_overlap_protection() -> None:
    provider_user_id, client_id, outsider_id, provider_id, plan_id = uuid4(), uuid4(), uuid4(), uuid4(), uuid4()
    async with SessionFactory() as session:
        try:
            catalog_service = await session.scalar(select(Service).where(Service.is_active.is_(True)).limit(1))
            assert catalog_service is not None
            session.add_all([
                User(id=provider_user_id, google_subject=f"eng-provider-{provider_user_id}", email=f"eng-provider-{provider_user_id}@example.invalid", name="Provider integration"),
                User(id=client_id, google_subject=f"eng-client-{client_id}", email=f"eng-client-{client_id}@example.invalid", name="Client integration"),
                User(id=outsider_id, google_subject=f"eng-outsider-{outsider_id}", email=f"eng-outsider-{outsider_id}@example.invalid", name="Outsider integration"),
            ])
            await session.flush()
            profile = ProviderProfile(id=provider_id, user_id=provider_user_id, display_name="Provider private", slug=f"provider-private-{provider_id.hex}", bio="Profile for private engagement integration.", profile_status=ProviderProfileStatus.APPROVED, profile_completeness=100, is_identity_verified=True)
            plan = SubscriptionPlan(id=plan_id, name="Plan engagements", code=f"ENG_{plan_id.hex.upper()}", price=Decimal("1"), currency="ARS", billing_frequency=BillingFrequency.MONTHLY, is_active=False, features_json=[])
            session.add_all([profile, plan])
            await session.flush()
            session.add(ProviderSubscription(provider_id=provider_id, plan_id=plan_id, status=ProviderSubscriptionStatus.ACTIVE))
            offer = ProviderService(provider_id=provider_id, service_id=catalog_service.id, status=ProviderServiceStatus.ACTIVE, headline="Remote quote integration", description="Private quote offer used only by the database integration suite.", pricing_type=PricingType.QUOTE, price_amount=None, price_currency="ARS", estimated_duration_minutes=60, accepts_urgent=False, requires_quote_details=True)
            session.add(offer)
            await session.flush()
            session.add(ProviderServiceModality(provider_service_id=offer.id, modality=ProviderModality.REMOTE, enabled=True))
            await session.commit()

            engagements = EngagementService(SqlAlchemyEngagementRepository(session), SqlAlchemyAddressRepository(session), DocumentReadinessService(SqlAlchemyDocumentRepository(session)), SubscriptionVisibilityService(SqlAlchemySubscriptionRepository(session)))
            payload = ServiceRequestCreate(provider_service_id=offer.id, selected_modality=ProviderModality.REMOTE, title="Remote service request", description="This is a sufficiently detailed private request for integration testing.")
            first = await engagements.create_request(client_id, payload)
            assert first.status == ServiceRequestStatus.REQUESTED
            with pytest.raises(EngagementNotFoundError):
                await engagements.get_request(outsider_id, first.id)

            viewed = await engagements.view_request(provider_user_id, first.id)
            assert viewed.status == ServiceRequestStatus.VIEWED
            valid_until = datetime.now(timezone.utc) + timedelta(days=2)
            quoted = await engagements.quote_request(provider_user_id, first.id, QuoteCreate(amount=Decimal("12000"), description="Includes remote diagnosis and a written resolution plan.", valid_until=valid_until))
            quote = quoted.quotes[0]
            schedule = BookingSchedule(starts_at=datetime.now(timezone.utc) + timedelta(days=3), ends_at=datetime.now(timezone.utc) + timedelta(days=3, hours=1))
            booking = await engagements.accept_quote(client_id, first.id, QuoteDecision(quote_id=quote.id, schedule=schedule))
            assert booking.status == BookingStatus.PENDING_PROVIDER
            assert booking.address is None
            with pytest.raises(InvalidTransitionError):
                await engagements.booking_action(client_id, booking.id, "start")

            confirmed_booking = await engagements.booking_action(provider_user_id, booking.id, "confirm")
            assert confirmed_booking.status == BookingStatus.CONFIRMED
            second = await engagements.create_request(client_id, payload)
            second_quoted = await engagements.quote_request(provider_user_id, second.id, QuoteCreate(amount=Decimal("15000"), description="Second quote used to verify the schedule exclusion constraint.", valid_until=valid_until))
            second_booking = await engagements.accept_quote(client_id, second.id, QuoteDecision(quote_id=second_quoted.quotes[0].id, schedule=schedule))
            with pytest.raises(EngagementConflictError, match="conflicts"):
                await engagements.booking_action(provider_user_id, second_booking.id, "confirm")

            started = await engagements.booking_action(provider_user_id, booking.id, "start")
            assert started.status == BookingStatus.IN_PROGRESS
            completed = await engagements.booking_action(provider_user_id, booking.id, "complete")
            assert completed.status == BookingStatus.COMPLETED
            confirmed = await engagements.booking_action(client_id, booking.id, "confirm")
            assert confirmed.client_confirmed_at is not None
        finally:
            await session.rollback()
            await session.execute(delete(Booking).where(Booking.provider_id == provider_id))
            await session.execute(delete(Quote).where(Quote.provider_id == provider_id))
            await session.execute(delete(ServiceRequest).where(ServiceRequest.provider_id == provider_id))
            await session.execute(delete(ProviderServiceModality).where(ProviderServiceModality.provider_service_id.in_(select(ProviderService.id).where(ProviderService.provider_id == provider_id))))
            await session.execute(delete(ProviderService).where(ProviderService.provider_id == provider_id))
            await session.execute(delete(ProviderSubscription).where(ProviderSubscription.provider_id == provider_id))
            await session.execute(delete(SubscriptionPlan).where(SubscriptionPlan.id == plan_id))
            await session.execute(delete(ProviderProfile).where(ProviderProfile.id == provider_id))
            await session.execute(delete(User).where(User.id.in_([provider_user_id, client_id, outsider_id])))
            await session.commit()
