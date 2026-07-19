from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, time
from decimal import Decimal
from typing import Protocol
from uuid import UUID
from zoneinfo import ZoneInfo

from geoalchemy2 import Geography, Geometry
from sqlalchemy import Float, Numeric, and_, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from sic_api.modules.catalog.models import Category, Service, Subcategory
from sic_api.modules.provider_services.models import AvailabilityException, AvailabilityRule, PricingType, ProviderModality, ProviderService, ProviderServiceArea, ProviderServiceModality, ProviderServiceStatus
from sic_api.modules.providers.models import ProviderPortfolioItem, ProviderProfile, ProviderProfileStatus
from sic_api.modules.users.models import User, UserStatus


@dataclass(frozen=True)
class SearchCandidate:
    offer_id: UUID
    provider_id: UUID
    user_status: UserStatus
    profile_status: ProviderProfileStatus
    profile_paused: bool
    provider_slug: str
    display_name: str
    business_name: str | None
    bio: str | None
    experience_years: int | None
    rating_average: float
    rating_count: int
    completed_services_count: int
    response_rate: float
    average_response_minutes: int | None
    profile_completeness: int
    is_identity_verified: bool
    is_demo: bool
    service_status: ProviderServiceStatus
    service_id: UUID
    service_name: str
    service_slug: str
    subcategory_name: str
    subcategory_slug: str
    category_name: str
    category_slug: str
    headline: str
    description: str
    pricing_type: PricingType
    price_amount: Decimal | None
    price_currency: str
    estimated_duration_minutes: int | None
    guarantee_days: int | None
    accepts_urgent: bool
    modalities: frozenset[ProviderModality] = frozenset()
    has_service_area: bool = False
    coverage_matches: bool = False
    provider_location_matches: bool = False
    distance_meters: float | None = None
    approximate_latitude: float | None = None
    approximate_longitude: float | None = None
    available_today: bool = False


@dataclass(frozen=True)
class PortfolioEntry:
    provider_id: UUID
    title: str
    description: str
    position: int


class SearchRepository(Protocol):
    async def candidates(
        self,
        *,
        terms: tuple[str, ...] = (),
        service_slug: str | None = None,
        category_slug: str | None = None,
        subcategory_slug: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        search_radius_meters: int = 20_000,
        provider_slug: str | None = None,
    ) -> list[SearchCandidate]: ...

    async def portfolio(self, provider_id: UUID) -> list[PortfolioEntry]: ...


class SqlAlchemySearchRepository:
    """Read-only projection for public discovery.

    This repository is the single deliberate cross-module join used by search. It
    returns candidates only; final visibility remains owned by
    ProviderVisibilityService.
    """

    candidate_limit = 500

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _base_candidate(row) -> SearchCandidate:
        offer, profile, user_status, service, subcategory, category = row
        return SearchCandidate(
            offer_id=offer.id,
            provider_id=profile.id,
            user_status=user_status,
            profile_status=profile.profile_status,
            profile_paused=profile.paused_at is not None,
            provider_slug=profile.slug,
            display_name=profile.display_name,
            business_name=profile.business_name,
            bio=profile.bio,
            experience_years=profile.experience_years,
            rating_average=float(profile.rating_average),
            rating_count=profile.rating_count,
            completed_services_count=profile.completed_services_count,
            response_rate=profile.response_rate,
            average_response_minutes=profile.average_response_minutes,
            profile_completeness=profile.profile_completeness,
            is_identity_verified=profile.is_identity_verified,
            is_demo=profile.is_demo,
            service_status=offer.status,
            service_id=service.id,
            service_name=service.name,
            service_slug=service.slug,
            subcategory_name=subcategory.name,
            subcategory_slug=subcategory.slug,
            category_name=category.name,
            category_slug=category.slug,
            headline=offer.headline,
            description=offer.description,
            pricing_type=offer.pricing_type,
            price_amount=offer.price_amount,
            price_currency=offer.price_currency,
            estimated_duration_minutes=offer.estimated_duration_minutes,
            guarantee_days=offer.guarantee_days,
            accepts_urgent=offer.accepts_urgent,
        )

    async def candidates(
        self,
        *,
        terms: tuple[str, ...] = (),
        service_slug: str | None = None,
        category_slug: str | None = None,
        subcategory_slug: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        search_radius_meters: int = 20_000,
        provider_slug: str | None = None,
    ) -> list[SearchCandidate]:
        query = (
            select(ProviderService, ProviderProfile, User.status, Service, Subcategory, Category)
            .join(ProviderProfile, ProviderProfile.id == ProviderService.provider_id)
            .join(User, User.id == ProviderProfile.user_id)
            .join(Service, Service.id == ProviderService.service_id)
            .join(Subcategory, Subcategory.id == Service.subcategory_id)
            .join(Category, Category.id == Subcategory.category_id)
            .where(Service.is_active.is_(True), Subcategory.is_active.is_(True), Category.is_active.is_(True))
            .order_by(ProviderService.created_at, ProviderService.id)
        )
        if provider_slug:
            query = query.where(ProviderProfile.slug == provider_slug)
        else:
            query = query.limit(self.candidate_limit)
        if service_slug:
            query = query.where(Service.slug == service_slug)
        if category_slug:
            query = query.where(Category.slug == category_slug)
        if subcategory_slug:
            query = query.where(Subcategory.slug == subcategory_slug)
        if terms:
            matches = []
            for term in terms:
                pattern = f"%{term}%"
                matches.extend((Service.slug.ilike(pattern), Subcategory.slug.ilike(pattern), Category.slug.ilike(pattern)))
            query = query.where(or_(*matches))

        candidates = [self._base_candidate(row) for row in (await self.session.execute(query)).all()]
        if not candidates:
            return []
        offer_ids = [item.offer_id for item in candidates]

        modalities: dict[UUID, set[ProviderModality]] = {item_id: set() for item_id in offer_ids}
        modality_rows = await self.session.execute(
            select(ProviderServiceModality.provider_service_id, ProviderServiceModality.modality).where(
                ProviderServiceModality.provider_service_id.in_(offer_ids), ProviderServiceModality.enabled.is_(True)
            )
        )
        for offer_id, modality in modality_rows:
            modalities[offer_id].add(modality)

        area_ids = set((await self.session.scalars(
            select(ProviderServiceArea.provider_service_id).where(ProviderServiceArea.provider_service_id.in_(offer_ids))
        )).all())
        areas: dict[UUID, tuple[bool, float | None, float | None, float | None]] = {
            offer_id: (False, None, None, None) for offer_id in area_ids
        }
        base_locations: dict[UUID, tuple[bool, float | None, float | None, float | None]] = {}
        if latitude is not None and longitude is not None:
            client_point = cast(func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326), Geography(geometry_type="POINT", srid=4326))
            area_geometry = cast(ProviderServiceArea.center, Geometry(geometry_type="POINT", srid=4326))
            area_match = and_(
                func.ST_DWithin(ProviderServiceArea.center, client_point, ProviderServiceArea.radius_meters),
                func.ST_DWithin(ProviderServiceArea.center, client_point, search_radius_meters),
            )
            area_rows = await self.session.execute(
                select(
                    ProviderServiceArea.provider_service_id,
                    func.ST_Distance(ProviderServiceArea.center, client_point),
                    cast(func.round(cast(func.ST_Y(area_geometry), Numeric), 2), Float),
                    cast(func.round(cast(func.ST_X(area_geometry), Numeric), 2), Float),
                ).where(ProviderServiceArea.provider_service_id.in_(offer_ids), area_match)
            )
            for offer_id, distance, approximate_latitude, approximate_longitude in area_rows:
                areas[offer_id] = (True, float(distance), approximate_latitude, approximate_longitude)

            provider_ids = list({item.provider_id for item in candidates})
            base_geometry = cast(ProviderProfile.base_point, Geometry(geometry_type="POINT", srid=4326))
            base_rows = await self.session.execute(
                select(
                    ProviderProfile.id,
                    func.ST_Distance(ProviderProfile.base_point, client_point),
                    cast(func.round(cast(func.ST_Y(base_geometry), Numeric), 2), Float),
                    cast(func.round(cast(func.ST_X(base_geometry), Numeric), 2), Float),
                ).where(
                    ProviderProfile.id.in_(provider_ids),
                    ProviderProfile.base_point.is_not(None),
                    func.ST_DWithin(ProviderProfile.base_point, client_point, search_radius_meters),
                )
            )
            for provider_id, distance, approximate_latitude, approximate_longitude in base_rows:
                base_locations[provider_id] = (True, float(distance), approximate_latitude, approximate_longitude)

        now = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))
        available_ids = set((await self.session.scalars(
            select(AvailabilityRule.provider_service_id).where(
                AvailabilityRule.provider_service_id.in_(offer_ids),
                AvailabilityRule.day_of_week == now.weekday(),
                AvailabilityRule.is_active.is_(True),
            ).distinct()
        )).all())
        start_of_day = datetime.combine(now.date(), time.min, tzinfo=now.tzinfo)
        end_of_day = datetime.combine(now.date(), time.max, tzinfo=now.tzinfo)
        provider_ids = list({item.provider_id for item in candidates})
        exception_rows = await self.session.execute(
            select(AvailabilityException.provider_id, AvailabilityException.is_available_override).where(
                AvailabilityException.provider_id.in_(provider_ids),
                AvailabilityException.starts_at <= end_of_day,
                AvailabilityException.ends_at >= start_of_day,
            )
        )
        unavailable_providers: set[UUID] = set()
        override_providers: set[UUID] = set()
        for provider_id, is_available_override in exception_rows:
            if is_available_override:
                override_providers.add(provider_id)
            else:
                unavailable_providers.add(provider_id)

        enriched: list[SearchCandidate] = []
        for candidate in candidates:
            area = areas.get(candidate.offer_id)
            base = base_locations.get(candidate.provider_id)
            coverage_matches = bool(area and area[0])
            provider_location_matches = bool(base and base[0])
            selected = area if coverage_matches else base if provider_location_matches else None
            enriched.append(replace(
                candidate,
                modalities=frozenset(modalities[candidate.offer_id]),
                has_service_area=area is not None,
                coverage_matches=coverage_matches,
                provider_location_matches=provider_location_matches,
                distance_meters=selected[1] if selected else None,
                approximate_latitude=selected[2] if selected else None,
                approximate_longitude=selected[3] if selected else None,
                available_today=(candidate.offer_id in available_ids and candidate.provider_id not in unavailable_providers) or candidate.provider_id in override_providers,
            ))
        return enriched

    async def portfolio(self, provider_id: UUID) -> list[PortfolioEntry]:
        items = (await self.session.scalars(
            select(ProviderPortfolioItem).where(ProviderPortfolioItem.provider_id == provider_id).order_by(ProviderPortfolioItem.position, ProviderPortfolioItem.created_at)
        )).all()
        return [PortfolioEntry(provider_id=item.provider_id, title=item.title, description=item.description, position=item.position) for item in items]
