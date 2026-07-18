from uuid import uuid4

import pytest

from sic_api.modules.users.models import UserRoleName
from sic_api.modules.users.service import InvalidSelfServiceRole, RoleService


class FakeRoleRepository:
    def __init__(self) -> None:
        self.roles: set[UserRoleName] = set()

    async def replace_self_service_roles(self, user_id, roles):
        self.roles = set(roles)
        return self.roles


@pytest.mark.anyio
async def test_client_and_provider_can_be_selected_together() -> None:
    repository = FakeRoleRepository()
    result = await RoleService(repository).select_roles(uuid4(), {UserRoleName.CLIENT, UserRoleName.PROVIDER})
    assert result == {UserRoleName.CLIENT, UserRoleName.PROVIDER}


@pytest.mark.anyio
async def test_admin_cannot_be_self_assigned() -> None:
    with pytest.raises(InvalidSelfServiceRole):
        await RoleService(FakeRoleRepository()).select_roles(uuid4(), {UserRoleName.ADMIN})


@pytest.mark.anyio
async def test_at_least_one_role_is_required() -> None:
    with pytest.raises(InvalidSelfServiceRole):
        await RoleService(FakeRoleRepository()).select_roles(uuid4(), set())
