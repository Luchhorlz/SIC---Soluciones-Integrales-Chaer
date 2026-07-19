from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, status

from sic_api.settings import get_settings
from sic_api.modules.users.models import UserRoleName


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    roles: frozenset[str]
    session_id: str


@dataclass(frozen=True)
class IdentitySyncPrincipal:
    google_subject: str


def decode_internal_token(token: str) -> Principal:
    secret = get_settings().internal_api_jwt_secret
    if not secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Internal authentication is not configured")
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"], audience="sic-api", options={"require": ["exp", "sub", "aud"]})
        return Principal(user_id=UUID(payload["sub"]), roles=frozenset(payload.get("roles", [])), session_id=str(payload.get("session_id", "")))
    except (jwt.PyJWTError, ValueError, KeyError) as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal token") from error


def decode_identity_sync_token(token: str) -> IdentitySyncPrincipal:
    secret = get_settings().internal_api_jwt_secret
    if not secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Internal authentication is not configured")
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"], audience="sic-api", options={"require": ["exp", "sub", "aud", "purpose"]})
        if payload["purpose"] != "identity-sync" or not str(payload["sub"]).startswith("google:"):
            raise ValueError("Unexpected token purpose")
        return IdentitySyncPrincipal(google_subject=str(payload["sub"]).removeprefix("google:"))
    except (jwt.PyJWTError, ValueError, KeyError) as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid identity sync token") from error


async def get_principal(authorization: Annotated[str | None, Header()] = None) -> Principal:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing internal token")
    return decode_internal_token(authorization.removeprefix("Bearer ").strip())


CurrentPrincipal = Annotated[Principal, Depends(get_principal)]


async def get_admin_principal(principal: CurrentPrincipal) -> Principal:
    if UserRoleName.ADMIN.value not in principal.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator role required")
    return principal


AdminPrincipal = Annotated[Principal, Depends(get_admin_principal)]


async def get_document_reviewer_principal(principal: CurrentPrincipal) -> Principal:
    allowed = {UserRoleName.ADMIN.value, UserRoleName.DOCUMENT_REVIEWER.value}
    if not principal.roles.intersection(allowed):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Document reviewer role required")
    return principal


DocumentReviewerPrincipal = Annotated[Principal, Depends(get_document_reviewer_principal)]


async def get_provider_principal(principal: CurrentPrincipal) -> Principal:
    if UserRoleName.PROVIDER.value not in principal.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Provider role required")
    return principal


ProviderPrincipal = Annotated[Principal, Depends(get_provider_principal)]


async def get_identity_sync_principal(authorization: Annotated[str | None, Header()] = None) -> IdentitySyncPrincipal:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing identity sync token")
    return decode_identity_sync_token(authorization.removeprefix("Bearer ").strip())


CurrentIdentitySyncPrincipal = Annotated[IdentitySyncPrincipal, Depends(get_identity_sync_principal)]
