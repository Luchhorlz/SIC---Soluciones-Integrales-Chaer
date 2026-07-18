from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, status

from sic_api.settings import get_settings


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    roles: frozenset[str]
    session_id: str


def decode_internal_token(token: str) -> Principal:
    secret = get_settings().internal_api_jwt_secret
    if not secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Internal authentication is not configured")
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"], audience="sic-api", options={"require": ["exp", "sub", "aud"]})
        return Principal(user_id=UUID(payload["sub"]), roles=frozenset(payload.get("roles", [])), session_id=str(payload.get("session_id", "")))
    except (jwt.PyJWTError, ValueError, KeyError) as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal token") from error


async def get_principal(authorization: Annotated[str | None, Header()] = None) -> Principal:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing internal token")
    return decode_internal_token(authorization.removeprefix("Bearer ").strip())


CurrentPrincipal = Annotated[Principal, Depends(get_principal)]
