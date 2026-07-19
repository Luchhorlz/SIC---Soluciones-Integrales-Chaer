from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol
from urllib.parse import urlparse

import httpx


class BillingProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class SubscriptionCheckoutRequest:
    internal_reference: str
    payer_email: str
    reason: str
    amount: Decimal
    currency: str
    back_url: str


@dataclass(frozen=True)
class ExternalSubscription:
    external_id: str
    external_reference: str | None
    status: str
    checkout_url: str | None
    current_period_start: datetime | None
    current_period_end: datetime | None


@dataclass(frozen=True)
class ExternalAuthorizedPayment:
    external_id: str
    subscription_external_id: str
    status: str


class BillingProvider(Protocol):
    async def create_subscription_checkout(self, request: SubscriptionCheckoutRequest) -> ExternalSubscription: ...
    async def get_subscription(self, external_id: str) -> ExternalSubscription: ...
    async def get_authorized_payment(self, external_id: str) -> ExternalAuthorizedPayment: ...


def _date(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def validate_checkout_url(value: str | None) -> str:
    if not value:
        raise BillingProviderError("Mercado Pago did not return a checkout URL")
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in {"mercadopago.com.ar", "www.mercadopago.com.ar"}:
        raise BillingProviderError("Mercado Pago returned an unexpected checkout URL")
    return value


class MercadoPagoBillingProvider:
    def __init__(self, access_token: str, api_base_url: str = "https://api.mercadopago.com", timeout_seconds: float = 10.0, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.access_token = access_token
        self.api_base_url = api_base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    async def _request(self, method: str, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, transport=self.transport) as client:
                response = await client.request(method, f"{self.api_base_url}{path}", headers={"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"}, json=json)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise BillingProviderError("Mercado Pago request failed") from error
        if not isinstance(data, dict):
            raise BillingProviderError("Mercado Pago returned an invalid response")
        return data

    @staticmethod
    def _subscription(data: dict[str, Any]) -> ExternalSubscription:
        external_id = data.get("id")
        if not isinstance(external_id, str) or not external_id:
            raise BillingProviderError("Mercado Pago did not return a subscription ID")
        summarized = data.get("summarized") if isinstance(data.get("summarized"), dict) else {}
        return ExternalSubscription(
            external_id=external_id,
            external_reference=str(data["external_reference"]) if data.get("external_reference") is not None else None,
            status=str(data.get("status", "error")).lower(),
            checkout_url=data.get("init_point") if isinstance(data.get("init_point"), str) else None,
            current_period_start=_date(summarized.get("last_charged_date")),
            current_period_end=_date(data.get("next_payment_date")),
        )

    async def create_subscription_checkout(self, request: SubscriptionCheckoutRequest) -> ExternalSubscription:
        data = await self._request("POST", "/preapproval", json={
            "reason": request.reason,
            "external_reference": request.internal_reference,
            "payer_email": request.payer_email,
            "auto_recurring": {"frequency": 1, "frequency_type": "months", "transaction_amount": float(request.amount), "currency_id": request.currency},
            "back_url": request.back_url,
            "status": "pending",
        })
        return self._subscription(data)

    async def get_subscription(self, external_id: str) -> ExternalSubscription:
        return self._subscription(await self._request("GET", f"/preapproval/{external_id}"))

    async def get_authorized_payment(self, external_id: str) -> ExternalAuthorizedPayment:
        data = await self._request("GET", f"/authorized_payments/{external_id}")
        subscription_id = data.get("preapproval_id")
        if not isinstance(subscription_id, str) or not subscription_id:
            raise BillingProviderError("Mercado Pago did not return the related subscription")
        payment = data.get("payment") if isinstance(data.get("payment"), dict) else {}
        status = str(payment.get("status") or data.get("summarized") or data.get("status") or "unknown").lower()
        return ExternalAuthorizedPayment(external_id=str(data.get("id", external_id)), subscription_external_id=subscription_id, status=status)
