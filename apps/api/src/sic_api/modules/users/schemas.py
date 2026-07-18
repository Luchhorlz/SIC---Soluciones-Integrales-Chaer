from pydantic import BaseModel, Field

from .models import UserRoleName


class RoleSelection(BaseModel):
    roles: set[UserRoleName] = Field(min_length=1, max_length=2)


class RoleSelectionResult(BaseModel):
    roles: set[UserRoleName]
