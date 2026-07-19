import os
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete

from sic_api.db.session import SessionFactory
from sic_api.modules.providers.models import ProviderProfile
from sic_api.modules.subscriptions.models import BillingEvent, BillingProcessingStatus, ProviderSubscription, ProviderSubscriptionStatus, SubscriptionPlan
from sic_api.modules.subscriptions.repository import SqlAlchemySubscriptionRepository
from sic_api.modules.subscriptions.schemas import SubscriptionPlanCreate
from sic_api.modules.users.models import User

pytestmark = pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL integration runs in CI")


@pytest.mark.anyio
async def test_subscription_state_and_event_idempotency_round_trip() -> None:
    user_id = uuid4()
    provider_id = uuid4()
    event_external_id = f"subscription_preapproval:{uuid4()}"
    async with SessionFactory() as session:
        try:
            session.add(User(id=user_id, google_subject=f"subscription-test-{user_id}", email=f"subscription-{user_id}@example.invalid", name="Subscription test"))
            await session.flush()
            session.add(ProviderProfile(id=provider_id, user_id=user_id, display_name="Prestador suscripción", slug=f"prestador-suscripcion-{user_id.hex}", profile_completeness=20))
            await session.commit()

            repository = SqlAlchemySubscriptionRepository(session)
            plan = await repository.create_plan(SubscriptionPlanCreate(name="Plan de integración", code=f"PLAN_{user_id.hex.upper()}", price=Decimal("2500.00"), currency="ARS", is_active=True, features=["Visibilidad condicionada"]))
            pending = await repository.ensure_pending(provider_id, plan.id)
            await repository.attach_checkout(pending.id, f"mp-{pending.id}", "https://www.mercadopago.com.ar/subscriptions/checkout?preapproval_id=test", ProviderSubscriptionStatus.PENDING)
            assert await repository.apply_external_state(f"mp-{pending.id}", str(pending.id), ProviderSubscriptionStatus.ACTIVE, None, None, "approved") is True
            current = await repository.get_for_provider(provider_id)
            assert current is not None
            assert current.status == ProviderSubscriptionStatus.ACTIVE
            assert current.last_payment_status == "approved"

            event_id, created = await repository.record_event(event_external_id, "subscription_preapproval", "a" * 64)
            assert created is True
            duplicate_id, duplicate_created = await repository.record_event(event_external_id, "subscription_preapproval", "a" * 64)
            assert duplicate_id == event_id
            assert duplicate_created is False
            await repository.finish_event(event_id, BillingProcessingStatus.PROCESSED)
        finally:
            await session.rollback()
            await session.execute(delete(BillingEvent).where(BillingEvent.external_event_id == event_external_id))
            await session.execute(delete(ProviderSubscription).where(ProviderSubscription.provider_id == provider_id))
            await session.execute(delete(SubscriptionPlan).where(SubscriptionPlan.code == f"PLAN_{user_id.hex.upper()}"))
            await session.execute(delete(ProviderProfile).where(ProviderProfile.id == provider_id))
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()
