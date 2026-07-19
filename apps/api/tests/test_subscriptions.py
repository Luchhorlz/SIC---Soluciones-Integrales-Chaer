import hashlib
import hmac
import json
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from sic_api.main import app
from sic_api.modules.providers.models import SubscriptionVisibilityStatus
from sic_api.modules.subscriptions.billing import ExternalAuthorizedPayment, ExternalSubscription, MercadoPagoBillingProvider, SubscriptionCheckoutRequest
from sic_api.modules.subscriptions.models import BillingProcessingStatus, ProviderSubscriptionStatus, SubscriptionProvider
from sic_api.modules.subscriptions.schemas import ProviderSubscriptionView
from sic_api.modules.subscriptions.security import InvalidWebhookSignatureError, validate_mercadopago_signature
from sic_api.modules.subscriptions.service import BillingEventProcessingError, MercadoPagoWebhookService, SubscriptionVisibilityService, normalized_subscription_status


def signed_header(secret: str, data_id: str, request_id: str, timestamp: int) -> str:
    manifest = f"id:{data_id.lower()};request-id:{request_id};ts:{timestamp};"
    signature = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return f"ts={timestamp},v1={signature}"


def test_webhook_signature_uses_official_manifest_and_tolerance() -> None:
    secret = "sandbox-webhook-secret"
    timestamp = 1_725_000_000
    signature = signed_header(secret, "ABC123", "request-1", timestamp)
    validate_mercadopago_signature(signature=signature, request_id="request-1", data_id="ABC123", secret=secret, now=timestamp + 30)
    with pytest.raises(InvalidWebhookSignatureError):
        validate_mercadopago_signature(signature=signature, request_id="request-2", data_id="ABC123", secret=secret, now=timestamp + 30)
    with pytest.raises(InvalidWebhookSignatureError, match="Expired"):
        validate_mercadopago_signature(signature=signature, request_id="request-1", data_id="ABC123", secret=secret, now=timestamp + 301)


@pytest.mark.anyio
async def test_mercadopago_adapter_creates_pending_checkout_without_card_data() -> None:
    captured: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        assert request.headers["authorization"] == "Bearer TEST-token"
        return httpx.Response(201, json={"id": "preapproval-1", "external_reference": captured["external_reference"], "status": "pending", "init_point": "https://www.mercadopago.com.ar/subscriptions/checkout?preapproval_id=preapproval-1"})

    adapter = MercadoPagoBillingProvider("TEST-token", "https://api.mercadopago.com", transport=httpx.MockTransport(handler))
    result = await adapter.create_subscription_checkout(SubscriptionCheckoutRequest(internal_reference=str(uuid4()), payer_email="provider@example.invalid", reason="Plan real", amount=Decimal("1234.50"), currency="ARS", back_url="https://sic.example.invalid/prestador/suscripcion"))
    assert result.external_id == "preapproval-1"
    assert result.status == "pending"
    assert captured["status"] == "pending"
    assert captured["auto_recurring"] == {"frequency": 1, "frequency_type": "months", "transaction_amount": 1234.5, "currency_id": "ARS"}
    assert "card_token_id" not in captured


def test_external_statuses_are_normalized_without_deleting_data() -> None:
    assert normalized_subscription_status("authorized") == ProviderSubscriptionStatus.AUTHORIZED
    assert normalized_subscription_status("authorized", "approved") == ProviderSubscriptionStatus.ACTIVE
    assert normalized_subscription_status("authorized", "rejected") == ProviderSubscriptionStatus.PAST_DUE
    assert normalized_subscription_status("paused") == ProviderSubscriptionStatus.PAUSED
    assert normalized_subscription_status("canceled") == ProviderSubscriptionStatus.CANCELLED
    assert normalized_subscription_status("unexpected") == ProviderSubscriptionStatus.ERROR


class FakeRepository:
    def __init__(self) -> None:
        self.subscription: ProviderSubscriptionView | None = None
        self.events: dict[str, UUID] = {}
        self.event_statuses: dict[str, BillingProcessingStatus] = {}
        self.finished: list[tuple[UUID, BillingProcessingStatus]] = []
        self.applied: list[tuple[str, ProviderSubscriptionStatus, str | None]] = []

    async def get_for_provider(self, provider_id: UUID):
        return self.subscription

    async def record_event(self, external_event_id: str, event_type: str, payload_hash: str):
        if external_event_id in self.events:
            if self.event_statuses.get(external_event_id) == BillingProcessingStatus.FAILED:
                self.event_statuses[external_event_id] = BillingProcessingStatus.RECEIVED
                return self.events[external_event_id], True
            return self.events[external_event_id], False
        event_id = uuid4()
        self.events[external_event_id] = event_id
        self.event_statuses[external_event_id] = BillingProcessingStatus.RECEIVED
        return event_id, True

    async def finish_event(self, event_id: UUID, status: BillingProcessingStatus, error_message: str | None = None):
        self.finished.append((event_id, status))
        for external_id, stored_id in self.events.items():
            if stored_id == event_id:
                self.event_statuses[external_id] = status

    async def apply_external_state(self, external_id: str, external_reference: str | None, status: ProviderSubscriptionStatus, period_start, period_end, payment_status: str | None):
        self.applied.append((external_id, status, payment_status))
        return True


class FakeBilling:
    def __init__(self) -> None:
        self.subscription_calls = 0

    async def get_authorized_payment(self, external_id: str):
        return ExternalAuthorizedPayment(external_id=external_id, subscription_external_id="preapproval-1", status="approved")

    async def get_subscription(self, external_id: str):
        self.subscription_calls += 1
        return ExternalSubscription(external_id=external_id, external_reference=str(uuid4()), status="authorized", checkout_url=None, current_period_start=datetime.now(timezone.utc), current_period_end=None)


@pytest.mark.anyio
async def test_repeated_webhook_does_not_repeat_effects() -> None:
    repository = FakeRepository()
    billing = FakeBilling()
    service = MercadoPagoWebhookService(repository, billing)  # type: ignore[arg-type]
    payload = {"id": 123, "type": "subscription_preapproval", "data": {"id": "preapproval-1"}}
    raw = json.dumps(payload).encode()
    assert await service.process(payload=payload, raw_body=raw, resource_id="preapproval-1", request_id="request-1") == "processed"
    assert await service.process(payload=payload, raw_body=raw, resource_id="preapproval-1", request_id="request-1") == "duplicate"
    assert billing.subscription_calls == 1
    assert len(repository.applied) == 1
    assert repository.applied[0][1] == ProviderSubscriptionStatus.AUTHORIZED


class FlakyBilling(FakeBilling):
    async def get_subscription(self, external_id: str):
        self.subscription_calls += 1
        if self.subscription_calls == 1:
            raise RuntimeError("temporary sandbox outage")
        return ExternalSubscription(external_id=external_id, external_reference=str(uuid4()), status="authorized", checkout_url=None, current_period_start=None, current_period_end=None)


@pytest.mark.anyio
async def test_failed_verified_event_can_be_retried_safely() -> None:
    repository = FakeRepository()
    billing = FlakyBilling()
    service = MercadoPagoWebhookService(repository, billing)  # type: ignore[arg-type]
    payload = {"id": 456, "type": "subscription_preapproval", "data": {"id": "preapproval-2"}}
    raw = json.dumps(payload).encode()
    with pytest.raises(BillingEventProcessingError):
        await service.process(payload=payload, raw_body=raw, resource_id="preapproval-2", request_id="request-2")
    assert await service.process(payload=payload, raw_body=raw, resource_id="preapproval-2", request_id="request-2") == "processed"
    assert billing.subscription_calls == 2
    assert len(repository.applied) == 1


@pytest.mark.anyio
async def test_visibility_reads_normalized_subscription_state() -> None:
    repository = FakeRepository()
    provider_id = uuid4()
    assert await SubscriptionVisibilityService(repository).status(provider_id) == SubscriptionVisibilityStatus.NOT_CONFIGURED  # type: ignore[arg-type]
    repository.subscription = ProviderSubscriptionView(id=uuid4(), plan_id=uuid4(), provider_name=SubscriptionProvider.MERCADO_PAGO, status=ProviderSubscriptionStatus.PAST_DUE, cancel_at_period_end=False, created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    assert await SubscriptionVisibilityService(repository).status(provider_id) == SubscriptionVisibilityStatus.INACTIVE  # type: ignore[arg-type]
    repository.subscription = repository.subscription.model_copy(update={"status": ProviderSubscriptionStatus.ACTIVE})
    assert await SubscriptionVisibilityService(repository).status(provider_id) == SubscriptionVisibilityStatus.ACTIVE  # type: ignore[arg-type]


def test_subscription_endpoints_deny_anonymous_requests() -> None:
    client = TestClient(app)
    assert client.get("/v1/provider/subscription").status_code == 401
    assert client.get("/v1/admin/subscription-plans").status_code == 401
