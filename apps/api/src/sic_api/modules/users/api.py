from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sic_api.db.session import get_session
from sic_api.modules.identity.permissions import CurrentPrincipal

from .repository import SqlAlchemyRoleRepository
from .schemas import RoleSelection, RoleSelectionResult
from .service import InvalidSelfServiceRole, RoleService

router = APIRouter(prefix="/v1/me", tags=["users"])


@router.put("/roles", response_model=RoleSelectionResult)
async def select_roles(payload: RoleSelection, principal: CurrentPrincipal, session: AsyncSession = Depends(get_session)) -> RoleSelectionResult:
    service = RoleService(SqlAlchemyRoleRepository(session))
    try:
        roles = await service.select_roles(principal.user_id, payload.roles)
    except InvalidSelfServiceRole as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    return RoleSelectionResult(roles=roles)
