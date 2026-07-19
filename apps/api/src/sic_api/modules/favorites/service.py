from typing import Protocol
from uuid import UUID

from .repository import FavoriteNotFoundError, SqlAlchemyFavoriteRepository
from .schemas import FavoriteProviderView


class PublicProviderReader(Protocol):
    async def profile(self, slug: str): ...


class FavoriteService:
    def __init__(self, repository: SqlAlchemyFavoriteRepository, public_providers: PublicProviderReader) -> None:
        self.repository = repository
        self.public_providers = public_providers

    async def add(self, client_id: UUID, slug: str) -> FavoriteProviderView:
        profile = await self.public_providers.profile(slug)
        provider_id = await self.repository.provider_id(slug) if profile else None
        if profile is None or provider_id is None:
            raise FavoriteNotFoundError
        item = await self.repository.add(client_id, provider_id)
        return FavoriteProviderView(id=item.id, provider_slug=profile.slug, display_name=profile.display_name, business_name=profile.business_name, rating_average=profile.rating_average, rating_count=profile.rating_count, is_identity_verified=profile.is_identity_verified, created_at=item.created_at)

    async def list(self, client_id: UUID) -> list[FavoriteProviderView]:
        visible: list[FavoriteProviderView] = []
        for record in await self.repository.list(client_id):
            profile = await self.public_providers.profile(record.provider_slug)
            if profile:
                visible.append(FavoriteProviderView(id=record.favorite.id, provider_slug=profile.slug, display_name=profile.display_name, business_name=profile.business_name, rating_average=profile.rating_average, rating_count=profile.rating_count, is_identity_verified=profile.is_identity_verified, created_at=record.favorite.created_at))
        return visible

    async def remove(self, client_id: UUID, slug: str) -> None:
        await self.repository.remove(client_id, slug)
