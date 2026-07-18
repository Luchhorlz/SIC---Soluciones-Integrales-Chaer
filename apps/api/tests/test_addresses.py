from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from sic_api.main import app
from sic_api.modules.addresses.schemas import AddressCreate, AddressUpdate, AddressView
from sic_api.modules.addresses.service import AddressService


def address_payload(**overrides) -> AddressCreate:
    values = {"label": "Casa", "formatted_address": "Calle Falsa 123, Moreno, Buenos Aires", "street": "Calle Falsa", "street_number": "123", "city": "Moreno", "province": "Buenos Aires", "latitude": -34.634, "longitude": -58.791}
    values.update(overrides)
    return AddressCreate(**values)


class FakeAddressRepository:
    def __init__(self, has_addresses: bool) -> None:
        self._has_addresses = has_addresses
        self.make_default = False

    async def has_addresses(self, user_id):
        return self._has_addresses

    async def create(self, user_id, payload, make_default):
        self.make_default = make_default
        return AddressView(id=uuid4(), **payload.model_dump(exclude={"is_default"}), is_default=make_default)

    async def list(self, user_id): return []
    async def update(self, user_id, address_id, payload): raise NotImplementedError
    async def delete(self, user_id, address_id): raise NotImplementedError


@pytest.mark.anyio
async def test_first_address_becomes_default() -> None:
    repository = FakeAddressRepository(has_addresses=False)
    result = await AddressService(repository).create(uuid4(), address_payload())
    assert result.is_default is True
    assert repository.make_default is True


@pytest.mark.anyio
async def test_later_address_respects_non_default() -> None:
    repository = FakeAddressRepository(has_addresses=True)
    result = await AddressService(repository).create(uuid4(), address_payload())
    assert result.is_default is False


@pytest.mark.anyio
async def test_initial_release_rejects_non_argentina_address() -> None:
    with pytest.raises(ValueError):
        await AddressService(FakeAddressRepository(False)).create(uuid4(), address_payload(country_code="UY"))


def test_update_requires_both_coordinates() -> None:
    with pytest.raises(ValidationError):
        AddressUpdate(latitude=-34.6)


def test_address_routes_reject_missing_internal_token() -> None:
    response = TestClient(app).get("/v1/me/addresses")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing internal token"
