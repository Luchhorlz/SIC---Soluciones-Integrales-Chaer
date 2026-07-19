from uuid import UUID

from sic_api.modules.addresses.repository import AddressRepository

from .repository import BaseLocation, ProviderRepository
from .schemas import PortfolioItemCreate, ProviderOnboarding, ProviderProfileUpdate, ProviderProfileView


class ProviderProfileService:
    def __init__(self, repository: ProviderRepository, addresses: AddressRepository) -> None:
        self.repository = repository
        self.addresses = addresses

    async def _location(self, user_id: UUID, address_id: UUID | None) -> BaseLocation | None:
        if address_id is None:
            return None
        address = await self.addresses.get(user_id, address_id)
        return BaseLocation(address_id=address.id, latitude=address.latitude, longitude=address.longitude)

    async def get(self, user_id: UUID) -> ProviderProfileView | None:
        return await self.repository.get_by_user(user_id)

    async def onboard(self, user_id: UUID, payload: ProviderOnboarding) -> ProviderProfileView:
        return await self.repository.onboard(user_id, payload, await self._location(user_id, payload.base_address_id))

    async def update(self, user_id: UUID, payload: ProviderProfileUpdate) -> ProviderProfileView:
        update_location = "base_address_id" in payload.model_fields_set
        location = await self._location(user_id, payload.base_address_id) if update_location else None
        return await self.repository.update(user_id, payload, update_location, location)

    async def set_paused(self, user_id: UUID, paused: bool) -> ProviderProfileView:
        return await self.repository.set_paused(user_id, paused)

    async def add_portfolio_item(self, user_id: UUID, payload: PortfolioItemCreate) -> ProviderProfileView:
        return await self.repository.add_portfolio_item(user_id, payload)

    async def delete_portfolio_item(self, user_id: UUID, item_id: UUID) -> ProviderProfileView:
        return await self.repository.delete_portfolio_item(user_id, item_id)
