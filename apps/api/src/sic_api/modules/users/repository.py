from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import User, UserRole, UserRoleName, UserStatus


@dataclass(frozen=True)
class SyncedIdentity:
    id: UUID
    email: str
    name: str
    roles: set[UserRoleName]
    status: UserStatus


class IdentityConflictError(ValueError):
    pass


class UserRepository(Protocol):
    async def sync_google_identity(self, google_subject: str, email: str, name: str, avatar_url: str | None) -> SyncedIdentity: ...


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


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def sync_google_identity(self, google_subject: str, email: str, name: str, avatar_url: str | None) -> SyncedIdentity:
        normalized_email = email.strip().lower()
        user = await self.session.scalar(select(User).where(User.google_subject == google_subject))
        if user is None:
            email_owner = await self.session.scalar(select(User).where(User.email == normalized_email))
            if email_owner is not None:
                raise IdentityConflictError("The verified email is already linked to another Google identity")
            user = User(google_subject=google_subject, email=normalized_email, name=name.strip(), avatar_url=avatar_url, last_login_at=datetime.now(timezone.utc))
            self.session.add(user)
        else:
            email_owner = await self.session.scalar(select(User).where(User.email == normalized_email, User.id != user.id))
            if email_owner is not None:
                raise IdentityConflictError("The verified email is already linked to another Google identity")
            user.email = normalized_email
            user.name = name.strip()
            user.avatar_url = avatar_url
            user.last_login_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(user)
        roles = set((await self.session.scalars(select(UserRole.role).where(UserRole.user_id == user.id))).all())
        return SyncedIdentity(id=user.id, email=user.email, name=user.name, roles=roles, status=user.status)
