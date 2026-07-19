import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID

from geoalchemy2.elements import WKTElement
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ProviderPortfolioItem, ProviderProfile
from .schemas import PortfolioItemCreate, PortfolioItemView, ProviderOnboarding, ProviderProfileUpdate, ProviderProfileView


class ProviderNotFoundError(LookupError):
    pass


class ProviderConflictError(ValueError):
    pass


@dataclass(frozen=True)
class BaseLocation:
    address_id: UUID
    latitude: float
    longitude: float


class ProviderRepository(Protocol):
    async def get_by_user(self, user_id: UUID) -> ProviderProfileView | None: ...
    async def get_by_id(self, provider_id: UUID) -> ProviderProfileView | None: ...
    async def onboard(self, user_id: UUID, payload: ProviderOnboarding, location: BaseLocation | None) -> ProviderProfileView: ...
    async def update(self, user_id: UUID, payload: ProviderProfileUpdate, update_location: bool, location: BaseLocation | None) -> ProviderProfileView: ...
    async def set_paused(self, user_id: UUID, paused: bool) -> ProviderProfileView: ...
    async def add_portfolio_item(self, user_id: UUID, payload: PortfolioItemCreate) -> ProviderProfileView: ...
    async def delete_portfolio_item(self, user_id: UUID, item_id: UUID) -> ProviderProfileView: ...


def provider_slug(display_name: str, user_id: UUID) -> str:
    normalized = unicodedata.normalize("NFKD", display_name).encode("ascii", "ignore").decode("ascii").lower()
    name = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", normalized)).strip("-") or "prestador"
    return f"{name[:180].rstrip('-')}-{user_id.hex[:12]}"


class SqlAlchemyProviderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _portfolio_view(item: ProviderPortfolioItem) -> PortfolioItemView:
        return PortfolioItemView(id=item.id, title=item.title, description=item.description, position=item.position)

    async def _profile(self, user_id: UUID) -> ProviderProfile:
        profile = await self.session.scalar(select(ProviderProfile).where(ProviderProfile.user_id == user_id))
        if profile is None:
            raise ProviderNotFoundError
        return profile

    async def _portfolio(self, provider_id: UUID) -> list[ProviderPortfolioItem]:
        return list((await self.session.scalars(select(ProviderPortfolioItem).where(ProviderPortfolioItem.provider_id == provider_id).order_by(ProviderPortfolioItem.position, ProviderPortfolioItem.created_at))).all())

    async def _view(self, profile: ProviderProfile) -> ProviderProfileView:
        portfolio = await self._portfolio(profile.id)
        return ProviderProfileView(
            id=profile.id,
            display_name=profile.display_name,
            slug=profile.slug,
            business_name=profile.business_name,
            bio=profile.bio,
            experience_years=profile.experience_years,
            base_address_id=profile.base_address_id,
            profile_status=profile.profile_status,
            subscription_visibility_status=profile.subscription_visibility_status,
            rating_average=float(profile.rating_average),
            rating_count=profile.rating_count,
            completed_services_count=profile.completed_services_count,
            response_rate=profile.response_rate,
            average_response_minutes=profile.average_response_minutes,
            profile_completeness=profile.profile_completeness,
            is_identity_verified=profile.is_identity_verified,
            is_paused=profile.paused_at is not None,
            portfolio=[self._portfolio_view(item) for item in portfolio],
        )

    async def _refresh_completeness(self, profile: ProviderProfile) -> None:
        portfolio_count = int(await self.session.scalar(select(func.count(ProviderPortfolioItem.id)).where(ProviderPortfolioItem.provider_id == profile.id)) or 0)
        profile.profile_completeness = min(100, 20 + (25 if profile.bio else 0) + (10 if profile.experience_years is not None else 0) + (25 if profile.base_address_id else 0) + (20 if portfolio_count else 0))

    async def _commit(self) -> None:
        try:
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise ProviderConflictError("Provider profile or portfolio position already exists") from error

    @staticmethod
    def _apply_location(profile: ProviderProfile, location: BaseLocation | None) -> None:
        profile.base_address_id = location.address_id if location else None
        profile.base_point = WKTElement(f"POINT({location.longitude} {location.latitude})", srid=4326) if location else None

    async def get_by_user(self, user_id: UUID) -> ProviderProfileView | None:
        profile = await self.session.scalar(select(ProviderProfile).where(ProviderProfile.user_id == user_id))
        return await self._view(profile) if profile else None

    async def get_by_id(self, provider_id: UUID) -> ProviderProfileView | None:
        profile = await self.session.get(ProviderProfile, provider_id)
        return await self._view(profile) if profile else None

    async def onboard(self, user_id: UUID, payload: ProviderOnboarding, location: BaseLocation | None) -> ProviderProfileView:
        existing = await self.session.scalar(select(ProviderProfile).where(ProviderProfile.user_id == user_id))
        if existing:
            return await self._view(existing)
        profile = ProviderProfile(
            user_id=user_id,
            display_name=payload.display_name.strip(),
            slug=provider_slug(payload.display_name, user_id),
            business_name=payload.business_name.strip() if payload.business_name else None,
            bio=payload.bio.strip() if payload.bio else None,
            experience_years=payload.experience_years,
        )
        self._apply_location(profile, location)
        self.session.add(profile)
        await self.session.flush()
        await self._refresh_completeness(profile)
        await self._commit()
        await self.session.refresh(profile)
        return await self._view(profile)

    async def update(self, user_id: UUID, payload: ProviderProfileUpdate, update_location: bool, location: BaseLocation | None) -> ProviderProfileView:
        profile = await self._profile(user_id)
        changes = payload.model_dump(exclude_unset=True, exclude={"base_address_id"})
        for key, value in changes.items():
            setattr(profile, key, value.strip() if isinstance(value, str) else value)
        if update_location:
            self._apply_location(profile, location)
        await self._refresh_completeness(profile)
        await self._commit()
        await self.session.refresh(profile)
        return await self._view(profile)

    async def set_paused(self, user_id: UUID, paused: bool) -> ProviderProfileView:
        profile = await self._profile(user_id)
        profile.paused_at = datetime.now(timezone.utc) if paused else None
        await self._commit()
        return await self._view(profile)

    async def add_portfolio_item(self, user_id: UUID, payload: PortfolioItemCreate) -> ProviderProfileView:
        profile = await self._profile(user_id)
        count = int(await self.session.scalar(select(func.count(ProviderPortfolioItem.id)).where(ProviderPortfolioItem.provider_id == profile.id)) or 0)
        if count >= 12:
            raise ProviderConflictError("A provider can keep up to 12 portfolio items")
        position = payload.position
        if position == 0 and count:
            position = int(await self.session.scalar(select(func.max(ProviderPortfolioItem.position)).where(ProviderPortfolioItem.provider_id == profile.id)) or 0) + 1
        self.session.add(ProviderPortfolioItem(provider_id=profile.id, title=payload.title.strip(), description=payload.description.strip(), position=position))
        await self.session.flush()
        await self._refresh_completeness(profile)
        await self._commit()
        return await self._view(profile)

    async def delete_portfolio_item(self, user_id: UUID, item_id: UUID) -> ProviderProfileView:
        profile = await self._profile(user_id)
        removed = await self.session.execute(delete(ProviderPortfolioItem).where(ProviderPortfolioItem.id == item_id, ProviderPortfolioItem.provider_id == profile.id))
        if not removed.rowcount:
            await self.session.rollback()
            raise ProviderNotFoundError
        await self._refresh_completeness(profile)
        await self._commit()
        return await self._view(profile)
