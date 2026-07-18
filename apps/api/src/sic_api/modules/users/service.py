from uuid import UUID

from .models import UserRoleName
from .repository import RoleRepository

SELF_SERVICE_ROLES = {UserRoleName.CLIENT, UserRoleName.PROVIDER}


class InvalidSelfServiceRole(ValueError):
    pass


class RoleService:
    def __init__(self, repository: RoleRepository) -> None:
        self.repository = repository

    async def select_roles(self, user_id: UUID, roles: set[UserRoleName]) -> set[UserRoleName]:
        if not roles or not roles.issubset(SELF_SERVICE_ROLES):
            raise InvalidSelfServiceRole("Only CLIENT and PROVIDER can be selected during onboarding")
        return await self.repository.replace_self_service_roles(user_id, roles)
