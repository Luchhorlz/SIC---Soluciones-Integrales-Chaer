from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from .models import UserRoleName


class RoleSelection(BaseModel):
    roles: set[UserRoleName] = Field(min_length=1, max_length=2)


class RoleSelectionResult(BaseModel):
    roles: set[UserRoleName]


class GoogleIdentitySync(BaseModel):
    google_subject: str = Field(min_length=1, max_length=255)
    email: EmailStr
    name: str = Field(min_length=1, max_length=180)
    avatar_url: str | None = Field(default=None, max_length=2048)


class SyncedUser(BaseModel):
    id: UUID
    email: EmailStr
    name: str
    roles: set[UserRoleName]
    status: str
