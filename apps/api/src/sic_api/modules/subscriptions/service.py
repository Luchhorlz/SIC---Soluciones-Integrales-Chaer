import hashlib
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sic_api.modules.providers.models import SubscriptionVisibilityStatus

from .billing import BillingProvider, ExternalSubscription, SubscriptionCheckoutRequest, validate_checkout_url
from .models import BillingProcessingStatus, ProviderSubscriptionStatus
from .repository import SubscriptionConflictError, SubscriptionRepository
from .schemas import ProviderSubscriptionPage, SubscriptionCheckoutView, SubscriptionPlanCreate, SubscriptionPlanUpdate, SubscriptionPlanView


class BillingConfigurationError(RuntimeError):
    pass


class BillingEventProcessingError(RuntimeError):
    pass


@dataclass(frozen=True)
class BillingConfiguration:
    configured: bool
    back_url: str | None


class SubscriptionVisibilityService:
    def __init__(self, repository: SubscriptionRepository) -> None:
        self.repository = repository

    async def status(self, provider_id: UUID) -> SubscriptionVisibilityStatus:
        subscription = await self.repository.get_for_provider(provider_id)
        if subscription is None:
            return SubscriptionVisibilityStatus.NOT_CONFIGURED
        if subscription.status == ProviderSubscriptionStatus.ACTIVE:
            return SubscriptionVisibilityStatus.ACTIVE
        if subscription.status == ProviderSubscriptionStatus.AUTHORIZED:
            return SubscriptionVisibilityStatus.AUTHORIZED
        return SubscriptionVisibilityStatus.INACTIVE


class SubscriptionAdminService:
    def __init__(self, repository: SubscriptionRepository) -> None:
        self.repository = repository

    async def list_plans(self) -> list[SubscriptionPlanView]:
        return await self.repository.list_plans()

    async def create_plan(self, payload: SubscriptionPlanCreate) -> SubscriptionPlanView:
        return await self.repository.create_plan(payload)

    async def update_plan(self, plan_id: UUID, payload: SubscriptionPlanUpdate) -> SubscriptionPlanView:
        return await self.repository.update_plan(plan_id, payload)


class ProviderSubscriptionService:
    blocking_statuses = {
        ProviderSubscriptionStatus.ACTIVE,
        ProviderSubscriptionStatus.AUTHORIZED,
        ProviderSubscriptionStatus.PAUSED,
        ProviderSubscriptionStatus.PAST_DUE,
    }

    def __init__(self, repository: SubscriptionRepository, billing: BillingProvider | None, configuration: BillingConfiguration) -> None:
        self.repository = repository
        self.billing = billing
        self.configuration = configuration

    async def page(self, provider_id: UUID) -> ProviderSubscriptionPage:
        plan = await self.repository.active_plan()
        subscription = await self.repository.get_for_provider(provider_id)
        configured = bool(self.configuration.configured and self.billing and self.configuration.back_url)
        checkout_available = bool(plan and configured and (subscription is None or subscription.status not in self.blocking_statuses))
        if plan is None:
            message = "Administración todavía no configuró el plan mensual."
        elif not configured:
            message = "El plan está listo, pero faltan las credenciales de prueba de Mercado Pago."
        elif subscription and subscription.status in self.blocking_statuses:
            message = "La suscripción ya existe; su estado se actualiza con eventos verificados de Mercado Pago."
        else:
            message = "El checkout se abrirá en Mercado Pago y SIC no recibirá datos de tarjeta."
        return ProviderSubscriptionPage(plan=plan, subscription=subscription, checkout_available=checkout_available, billing_configured=configured, message=message)

    async def checkout(self, provider_id: UUID, payer_email: str) -> SubscriptionCheckoutView:
        plan = await self.repository.active_plan()
        if plan is None:
            raise BillingConfigurationError("No active subscription plan is configured")
        if not self.billing or not self.configuration.configured or not self.configuration.back_url:
            raise BillingConfigurationError("Mercado Pago sandbox is not configured")
        pending = await self.repository.ensure_pending(provider_id, plan.id)
        if pending.external_subscription_id and pending.checkout_url:
            return SubscriptionCheckoutView(checkout_url=validate_checkout_url(pending.checkout_url), status=pending.status)
        external = await self.billing.create_subscription_checkout(SubscriptionCheckoutRequest(
            internal_reference=str(pending.id),
            payer_email=payer_email,
            reason=plan.name,
            amount=plan.price,
            currency=plan.currency,
            back_url=self.configuration.back_url,
        ))
        checkout_url = validate_checkout_url(external.checkout_url)
        status = normalized_subscription_status(external.status)
        linked = await self.repository.attach_checkout(pending.id, external.external_id, checkout_url, status)
        return SubscriptionCheckoutView(checkout_url=checkout_url, status=linked.status)


def normalized_subscription_status(status: str, payment_status: str | None = None) -> ProviderSubscriptionStatus:
    normalized_payment = (payment_status or "").lower()
    if normalized_payment in {"rejected", "cancelled", "canceled", "refunded", "charged_back"}:
        return ProviderSubscriptionStatus.PAST_DUE
    if normalized_payment in {"approved", "accredited"}:
        return ProviderSubscriptionStatus.ACTIVE
    normalized = status.lower()
    return {
        "pending": ProviderSubscriptionStatus.PENDING,
        "authorized": ProviderSubscriptionStatus.AUTHORIZED,
        "active": ProviderSubscriptionStatus.ACTIVE,
        "paused": ProviderSubscriptionStatus.PAUSED,
        "cancelled": ProviderSubscriptionStatus.CANCELLED,
        "canceled": ProviderSubscriptionStatus.CANCELLED,
        "expired": ProviderSubscriptionStatus.EXPIRED,
    }.get(normalized, ProviderSubscriptionStatus.ERROR)


class MercadoPagoWebhookService:
    supported_topics = {"subscription_preapproval", "subscription_authorized_payment"}

    def __init__(self, repository: SubscriptionRepository, billing: BillingProvider) -> None:
        self.repository = repository
        self.billing = billing

    async def _apply_subscription(self, subscription: ExternalSubscription, payment_status: str | None = None) -> bool:
        status = normalized_subscription_status(subscription.status, payment_status)
        return await self.repository.apply_external_state(
            subscription.external_id,
            subscription.external_reference,
            status,
            subscription.current_period_start,
            subscription.current_period_end,
            payment_status,
        )

    async def process(self, *, payload: dict[str, Any], raw_body: bytes, resource_id: str, request_id: str | None) -> str:
        event_type = str(payload.get("type") or payload.get("topic") or "unknown")
        notification_id = payload.get("id")
        payload_hash = hashlib.sha256(raw_body).hexdigest()
        external_event_id = f"{event_type}:{notification_id}" if notification_id is not None else f"{event_type}:{request_id or payload_hash}"
        event_id, created = await self.repository.record_event(external_event_id, event_type, payload_hash)
        if not created:
            return "duplicate"
        if event_type not in self.supported_topics:
            await self.repository.finish_event(event_id, BillingProcessingStatus.IGNORED)
            return "ignored"
        try:
            payment_status: str | None = None
            if event_type == "subscription_authorized_payment":
                payment = await self.billing.get_authorized_payment(resource_id)
                payment_status = payment.status
                external = await self.billing.get_subscription(payment.subscription_external_id)
            else:
                external = await self.billing.get_subscription(resource_id)
            applied = await self._apply_subscription(external, payment_status)
            if not applied:
                await self.repository.finish_event(event_id, BillingProcessingStatus.IGNORED, "Resource is not linked to a SIC subscription")
                return "ignored"
            await self.repository.finish_event(event_id, BillingProcessingStatus.PROCESSED)
            return "processed"
        except Exception as error:
            await self.repository.finish_event(event_id, BillingProcessingStatus.FAILED, "Verified billing resource could not be processed")
            raise BillingEventProcessingError("Verified Mercado Pago event could not be processed") from error
