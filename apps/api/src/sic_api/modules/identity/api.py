from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sic_api.db.session import get_session
from sic_api.modules.identity.permissions import CurrentIdentitySyncPrincipal
from sic_api.modules.users.repository import IdentityConflictError, SqlAlchemyUserRepository
from sic_api.modules.users.schemas import GoogleIdentitySync, SyncedUser
from sic_api.modules.users.service import IdentityService

router = APIRouter(prefix="/v1/identity", tags=["identity"])


@router.post("/sync-google", response_model=SyncedUser)
async def sync_google_identity(payload: GoogleIdentitySync, principal: CurrentIdentitySyncPrincipal, session: AsyncSession = Depends(get_session)) -> SyncedUser:
    if payload.google_subject != principal.google_subject:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Google identity does not match signed token")
    try:
        synced = await IdentityService(SqlAlchemyUserRepository(session)).sync_google_identity(payload.google_subject, payload.email, payload.name, payload.avatar_url)
    except IdentityConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return SyncedUser(id=synced.id, email=synced.email, name=synced.name, roles=synced.roles, status=synced.status.value)
