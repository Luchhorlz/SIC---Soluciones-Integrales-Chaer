import hashlib
import hmac
import time


class InvalidWebhookSignatureError(ValueError):
    pass


def validate_mercadopago_signature(*, signature: str | None, request_id: str | None, data_id: str | None, secret: str, tolerance_seconds: int = 300, now: float | None = None) -> None:
    if not signature or not data_id:
        raise InvalidWebhookSignatureError("Missing Mercado Pago signature data")
    values: dict[str, str] = {}
    for part in signature.split(","):
        key, separator, value = part.strip().partition("=")
        if separator and key and value:
            values[key] = value
    timestamp = values.get("ts")
    received_hash = values.get("v1")
    if not timestamp or not received_hash:
        raise InvalidWebhookSignatureError("Invalid Mercado Pago signature format")

    manifest = f"id:{data_id.lower()};"
    if request_id:
        manifest += f"request-id:{request_id};"
    manifest += f"ts:{timestamp};"
    expected_hash = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash):
        raise InvalidWebhookSignatureError("Mercado Pago signature mismatch")

    try:
        sent_at = float(timestamp)
    except ValueError as error:
        raise InvalidWebhookSignatureError("Invalid Mercado Pago signature timestamp") from error
    if sent_at > 10_000_000_000:
        sent_at /= 1000
    if tolerance_seconds > 0 and abs((now if now is not None else time.time()) - sent_at) > tolerance_seconds:
        raise InvalidWebhookSignatureError("Expired Mercado Pago signature")
