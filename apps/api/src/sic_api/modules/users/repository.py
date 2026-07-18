from typing import Protocol
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import UserRole, UserRoleName


class RoleRepository(Protocol):
    async def replace_self_service_roles(self, user_id: UUID, roles: set[UserRoleName]) -> set[UserRoleName]: ...


class SqlAlchemyRoleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def replace_self_service_roles(self, user_id: UUID, roles: set[UserRoleName]) -> set[UserRoleName]:
        await self.session.execute(delete(UserRole).where(UserRole.user_id == user_id, UserRole.role.in_([UserRoleName.CLIENT, UserRoleName.PROVIDER])))
        self.session.add_all(UserRole(user_id=user_id, role=role) for role in roles)
        await self.session.commit()
        result = await self.session.scalars(select(UserRole.role).where(UserRole.user_id == user_id))
        return set(result.all())
