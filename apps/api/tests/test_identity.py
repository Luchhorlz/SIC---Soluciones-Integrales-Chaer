from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from fastapi import HTTPException

from sic_api.modules.identity.permissions import decode_identity_sync_token, decode_internal_token
from sic_api.settings import get_settings


def test_internal_token_requires_configured_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_API_JWT_SECRET", "test-only-secret-at-least-32-bytes-long")
    get_settings.cache_clear()
    user_id = uuid4()
    token = jwt.encode({"sub": str(user_id), "aud": "sic-api", "exp": datetime.now(timezone.utc) + timedelta(seconds=30), "roles": ["CLIENT"], "session_id": "session-test"}, "test-only-secret-at-least-32-bytes-long", algorithm="HS256")
    principal = decode_internal_token(token)
    assert principal.user_id == user_id
    assert principal.roles == {"CLIENT"}


def test_internal_token_rejects_wrong_audience(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_API_JWT_SECRET", "test-only-secret-at-least-32-bytes-long")
    get_settings.cache_clear()
    token = jwt.encode({"sub": str(uuid4()), "aud": "other-api", "exp": datetime.now(timezone.utc) + timedelta(seconds=30)}, "test-only-secret-at-least-32-bytes-long", algorithm="HS256")
    with pytest.raises(HTTPException) as error:
        decode_internal_token(token)
    assert error.value.status_code == 401


def test_identity_sync_token_binds_google_subject(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "test-only-secret-at-least-32-bytes-long"
    monkeypatch.setenv("INTERNAL_API_JWT_SECRET", secret)
    get_settings.cache_clear()
    token = jwt.encode({"sub": "google:123456", "aud": "sic-api", "purpose": "identity-sync", "exp": datetime.now(timezone.utc) + timedelta(seconds=30)}, secret, algorithm="HS256")
    assert decode_identity_sync_token(token).google_subject == "123456"


def test_identity_sync_token_rejects_user_token(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "test-only-secret-at-least-32-bytes-long"
    monkeypatch.setenv("INTERNAL_API_JWT_SECRET", secret)
    get_settings.cache_clear()
    token = jwt.encode({"sub": str(uuid4()), "aud": "sic-api", "purpose": "user", "exp": datetime.now(timezone.utc) + timedelta(seconds=30)}, secret, algorithm="HS256")
    with pytest.raises(HTTPException):
        decode_identity_sync_token(token)
