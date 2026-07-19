from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from sic_api.modules.providers.models import ProviderProfile

from .models import FavoriteProvider


class FavoriteNotFoundError(LookupError):
    pass


@dataclass(frozen=True)
class FavoriteRecord:
    favorite: FavoriteProvider
    provider_slug: str


class SqlAlchemyFavoriteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def provider_id(self, slug: str) -> UUID | None:
        return await self.session.scalar(select(ProviderProfile.id).where(ProviderProfile.slug == slug))

    async def add(self, client_id: UUID, provider_id: UUID) -> FavoriteProvider:
        statement = insert(FavoriteProvider).values(client_id=client_id, provider_id=provider_id).on_conflict_do_nothing(constraint="uq_favorite_client_provider").returning(FavoriteProvider.id)
        favorite_id = await self.session.scalar(statement)
        if favorite_id is None:
            favorite_id = await self.session.scalar(select(FavoriteProvider.id).where(FavoriteProvider.client_id == client_id, FavoriteProvider.provider_id == provider_id))
        await self.session.commit()
        item = await self.session.get(FavoriteProvider, favorite_id)
        if item is None:
            raise FavoriteNotFoundError
        return item

    async def list(self, client_id: UUID) -> list[FavoriteRecord]:
        rows = (await self.session.execute(
            select(FavoriteProvider, ProviderProfile.slug)
            .join(ProviderProfile, ProviderProfile.id == FavoriteProvider.provider_id)
            .where(FavoriteProvider.client_id == client_id)
            .order_by(FavoriteProvider.created_at.desc())
            .limit(100)
        )).all()
        return [FavoriteRecord(row[0], row[1]) for row in rows]

    async def remove(self, client_id: UUID, slug: str) -> None:
        result = await self.session.execute(
            delete(FavoriteProvider).where(
                FavoriteProvider.client_id == client_id,
                FavoriteProvider.provider_id == select(ProviderProfile.id).where(ProviderProfile.slug == slug).scalar_subquery(),
            )
        )
        await self.session.commit()
        if result.rowcount == 0:
            raise FavoriteNotFoundError
