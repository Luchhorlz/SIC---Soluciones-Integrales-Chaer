from uuid import UUID

from .repository import AddressRepository
from .schemas import AddressCreate, AddressUpdate, AddressView


class AddressService:
    def __init__(self, repository: AddressRepository) -> None:
        self.repository = repository

    async def create(self, user_id: UUID, payload: AddressCreate) -> AddressView:
        if payload.country_code.upper() != "AR":
            raise ValueError("Only Argentina addresses are supported in the initial release")
        make_default = payload.is_default or not await self.repository.has_addresses(user_id)
        return await self.repository.create(user_id, payload, make_default)

    async def list(self, user_id: UUID) -> list[AddressView]:
        return await self.repository.list(user_id)

    async def update(self, user_id: UUID, address_id: UUID, payload: AddressUpdate) -> AddressView:
        return await self.repository.update(user_id, address_id, payload)

    async def delete(self, user_id: UUID, address_id: UUID) -> None:
        await self.repository.delete(user_id, address_id)
