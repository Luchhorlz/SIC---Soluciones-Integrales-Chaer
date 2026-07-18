from uuid import uuid4

import pytest

from sic_api.modules.users.models import UserRoleName
from sic_api.modules.users.models import UserStatus
from sic_api.modules.users.repository import SyncedIdentity
from sic_api.modules.users.service import IdentityService, InvalidSelfServiceRole, RoleService


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


class FakeUserRepository:
    def __init__(self) -> None:
        self.received_email = ""

    async def sync_google_identity(self, google_subject, email, name, avatar_url):
        self.received_email = email
        return SyncedIdentity(id=uuid4(), email=email, name=name, roles=set(), status=UserStatus.ACTIVE)


@pytest.mark.anyio
async def test_google_identity_is_normalized_before_sync() -> None:
    repository = FakeUserRepository()
    result = await IdentityService(repository).sync_google_identity(" 123 ", " PERSON@EXAMPLE.COM ", " Persona ", None)
    assert repository.received_email == "person@example.com"
    assert result.status == UserStatus.ACTIVE
