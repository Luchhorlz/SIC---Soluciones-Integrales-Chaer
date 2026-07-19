from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .models import BillingEvent, BillingFrequency, BillingProcessingStatus, ProviderSubscription, ProviderSubscriptionStatus, SubscriptionPlan, SubscriptionProvider
from .schemas import ProviderSubscriptionView, SubscriptionPlanCreate, SubscriptionPlanUpdate, SubscriptionPlanView


class SubscriptionPlanNotFoundError(LookupError):
    pass


class SubscriptionConflictError(ValueError):
    pass


@dataclass(frozen=True)
class SubscriptionRecord:
    id: UUID
    provider_id: UUID
    plan_id: UUID
    external_subscription_id: str | None
    status: ProviderSubscriptionStatus
    checkout_url: str | None


class SubscriptionRepository(Protocol):
    async def list_plans(self) -> list[SubscriptionPlanView]: ...
    async def active_plan(self) -> SubscriptionPlanView | None: ...
    async def create_plan(self, payload: SubscriptionPlanCreate) -> SubscriptionPlanView: ...
    async def update_plan(self, plan_id: UUID, payload: SubscriptionPlanUpdate) -> SubscriptionPlanView: ...
    async def get_for_provider(self, provider_id: UUID) -> ProviderSubscriptionView | None: ...
    async def ensure_pending(self, provider_id: UUID, plan_id: UUID) -> SubscriptionRecord: ...
    async def attach_checkout(self, subscription_id: UUID, external_id: str, checkout_url: str, status: ProviderSubscriptionStatus) -> SubscriptionRecord: ...
    async def apply_external_state(self, external_id: str, external_reference: str | None, status: ProviderSubscriptionStatus, period_start: datetime | None, period_end: datetime | None, payment_status: str | None) -> bool: ...
    async def record_event(self, external_event_id: str, event_type: str, payload_hash: str) -> tuple[UUID, bool]: ...
    async def finish_event(self, event_id: UUID, status: BillingProcessingStatus, error_message: str | None = None) -> None: ...


class SqlAlchemySubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _plan_view(plan: SubscriptionPlan) -> SubscriptionPlanView:
        return SubscriptionPlanView(
            id=plan.id,
            name=plan.name,
            code=plan.code,
            price=Decimal(plan.price),
            currency=plan.currency,
            billing_frequency=plan.billing_frequency,
            is_active=plan.is_active,
            features=list(plan.features_json or []),
            mercado_pago_plan_id=plan.mercado_pago_plan_id,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
        )

    @staticmethod
    def _subscription_view(item: ProviderSubscription) -> ProviderSubscriptionView:
        return ProviderSubscriptionView(
            id=item.id,
            plan_id=item.plan_id,
            provider_name=item.provider_name,
            status=item.status,
            current_period_start=item.current_period_start,
            current_period_end=item.current_period_end,
            cancel_at_period_end=item.cancel_at_period_end,
            last_payment_status=item.last_payment_status,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    @staticmethod
    def _record(item: ProviderSubscription) -> SubscriptionRecord:
        return SubscriptionRecord(item.id, item.provider_id, item.plan_id, item.external_subscription_id, item.status, item.checkout_url)

    async def list_plans(self) -> list[SubscriptionPlanView]:
        plans = (await self.session.scalars(select(SubscriptionPlan).order_by(SubscriptionPlan.created_at.desc()))).all()
        return [self._plan_view(plan) for plan in plans]

    async def active_plan(self) -> SubscriptionPlanView | None:
        plan = await self.session.scalar(select(SubscriptionPlan).where(SubscriptionPlan.is_active.is_(True)))
        return self._plan_view(plan) if plan else None

    async def _deactivate_plans(self) -> None:
        await self.session.execute(update(SubscriptionPlan).where(SubscriptionPlan.is_active.is_(True)).values(is_active=False))

    async def create_plan(self, payload: SubscriptionPlanCreate) -> SubscriptionPlanView:
        if payload.is_active:
            await self._deactivate_plans()
        plan = SubscriptionPlan(
            name=payload.name,
            code=payload.code,
            price=payload.price,
            currency=payload.currency,
            billing_frequency=payload.billing_frequency,
            is_active=payload.is_active,
            features_json=payload.features,
        )
        self.session.add(plan)
        try:
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise SubscriptionConflictError("The plan code already exists") from error
        await self.session.refresh(plan)
        return self._plan_view(plan)

    async def update_plan(self, plan_id: UUID, payload: SubscriptionPlanUpdate) -> SubscriptionPlanView:
        plan = await self.session.get(SubscriptionPlan, plan_id)
        if plan is None:
            raise SubscriptionPlanNotFoundError
        changes = payload.model_dump(exclude_unset=True)
        if changes.get("is_active"):
            await self._deactivate_plans()
        if "features" in changes:
            plan.features_json = changes.pop("features")
        for field, value in changes.items():
            setattr(plan, field, value)
        await self.session.commit()
        await self.session.refresh(plan)
        return self._plan_view(plan)

    async def get_for_provider(self, provider_id: UUID) -> ProviderSubscriptionView | None:
        item = await self.session.scalar(select(ProviderSubscription).where(ProviderSubscription.provider_id == provider_id))
        return self._subscription_view(item) if item else None

    async def ensure_pending(self, provider_id: UUID, plan_id: UUID) -> SubscriptionRecord:
        item = await self.session.scalar(select(ProviderSubscription).where(ProviderSubscription.provider_id == provider_id).with_for_update())
        if item is None:
            item = ProviderSubscription(provider_id=provider_id, plan_id=plan_id, status=ProviderSubscriptionStatus.PENDING)
            self.session.add(item)
        elif item.status in {ProviderSubscriptionStatus.ACTIVE, ProviderSubscriptionStatus.AUTHORIZED, ProviderSubscriptionStatus.PAUSED, ProviderSubscriptionStatus.PAST_DUE}:
            raise SubscriptionConflictError("The provider already has a subscription that must be managed instead of replaced")
        elif item.status != ProviderSubscriptionStatus.PENDING:
            item.plan_id = plan_id
            item.external_subscription_id = None
            item.checkout_url = None
            item.status = ProviderSubscriptionStatus.PENDING
            item.last_payment_status = None
            item.current_period_start = None
            item.current_period_end = None
        await self.session.commit()
        await self.session.refresh(item)
        return self._record(item)

    async def attach_checkout(self, subscription_id: UUID, external_id: str, checkout_url: str, status: ProviderSubscriptionStatus) -> SubscriptionRecord:
        item = await self.session.get(ProviderSubscription, subscription_id)
        if item is None:
            raise SubscriptionConflictError("The pending subscription no longer exists")
        item.external_subscription_id = external_id
        item.checkout_url = checkout_url
        item.status = status
        try:
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise SubscriptionConflictError("The external subscription is already linked") from error
        await self.session.refresh(item)
        return self._record(item)

    async def apply_external_state(self, external_id: str, external_reference: str | None, status: ProviderSubscriptionStatus, period_start: datetime | None, period_end: datetime | None, payment_status: str | None) -> bool:
        item = await self.session.scalar(select(ProviderSubscription).where(ProviderSubscription.external_subscription_id == external_id).with_for_update())
        if item is None and external_reference:
            try:
                internal_id = UUID(external_reference)
            except ValueError:
                return False
            item = await self.session.scalar(select(ProviderSubscription).where(ProviderSubscription.id == internal_id).with_for_update())
        if item is None:
            return False
        if item.external_subscription_id not in {None, external_id}:
            return False
        item.external_subscription_id = external_id
        item.status = status
        item.current_period_start = period_start
        item.current_period_end = period_end
        if payment_status is not None:
            item.last_payment_status = payment_status[:80]
        await self.session.commit()
        return True

    async def record_event(self, external_event_id: str, event_type: str, payload_hash: str) -> tuple[UUID, bool]:
        item = BillingEvent(
            provider_name=SubscriptionProvider.MERCADO_PAGO,
            external_event_id=external_event_id[:255],
            event_type=event_type[:120],
            payload_hash=payload_hash,
            payload_private_reference=f"sha256:{payload_hash}",
        )
        self.session.add(item)
        try:
            await self.session.commit()
            await self.session.refresh(item)
            return item.id, True
        except IntegrityError:
            await self.session.rollback()
            existing = await self.session.scalar(select(BillingEvent).where(BillingEvent.external_event_id == external_event_id[:255]))
            if existing is None:
                raise
            if existing.processing_status == BillingProcessingStatus.FAILED and existing.payload_hash == payload_hash:
                existing.processing_status = BillingProcessingStatus.RECEIVED
                existing.processed_at = None
                existing.error_message = None
                await self.session.commit()
                return existing.id, True
            return existing.id, False

    async def finish_event(self, event_id: UUID, status: BillingProcessingStatus, error_message: str | None = None) -> None:
        item = await self.session.get(BillingEvent, event_id)
        if item is None:
            return
        item.processing_status = status
        item.error_message = error_message[:500] if error_message else None
        item.processed_at = datetime.now(timezone.utc)
        await self.session.commit()
