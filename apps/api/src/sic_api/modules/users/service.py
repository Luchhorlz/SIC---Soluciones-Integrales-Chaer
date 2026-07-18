from uuid import UUID

from .models import UserRoleName
from .repository import RoleRepository, SyncedIdentity, UserRepository

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


class IdentityService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    async def sync_google_identity(self, google_subject: str, email: str, name: str, avatar_url: str | None) -> SyncedIdentity:
        if not google_subject.strip() or not email.strip() or not name.strip():
            raise ValueError("Google identity is incomplete")
        return await self.repository.sync_google_identity(google_subject.strip(), email.strip().lower(), name.strip(), avatar_url)
