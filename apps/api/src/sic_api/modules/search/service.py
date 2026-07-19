from __future__ import annotations

import base64
import re
import unicodedata
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sic_api.modules.documents.repository import RequirementReadiness
from sic_api.modules.provider_services.models import ProviderModality
from sic_api.modules.providers.models import SubscriptionVisibilityStatus
from sic_api.modules.providers.visibility import ProviderVisibilityContext, ProviderVisibilityService
from sic_api.modules.users.models import UserStatus
from sic_api.settings import get_settings

from .repository import SearchCandidate, SearchRepository
from .schemas import ProviderSearchPage, ProviderSearchResult, PublicPortfolioItem, PublicProviderOffer, PublicProviderProfile, SearchMode, SearchSort


class DocumentReadinessReader(Protocol):
    async def readiness(self, provider_id: UUID, service_id: UUID) -> RequirementReadiness: ...


class SubscriptionVisibilityReader(Protocol):
    async def status(self, provider_id: UUID) -> SubscriptionVisibilityStatus: ...


class InvalidSearchError(ValueError):
    pass


@dataclass(frozen=True)
class SearchRequest:
    query: str | None = None
    service_slug: str | None = None
    category_slug: str | None = None
    subcategory_slug: str | None = None
    mode: SearchMode = SearchMode.ALL
    latitude: float | None = None
    longitude: float | None = None
    radius_meters: int = 20_000
    available_today: bool = False
    sort: SearchSort = SearchSort.RELEVANCE
    cursor: str | None = None
    limit: int = 20


def normalize_search_terms(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
    tokens = [token for token in re.split(r"[^a-z0-9]+", normalized) if len(token) >= 2]
    return tuple(dict.fromkeys(token[:5] if len(token) >= 5 else token for token in tokens))[:8]


def normalize_search_slug(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", normalized)).strip("-")


class ProviderSearchService:
    def __init__(self, repository: SearchRepository, documents: DocumentReadinessReader, subscriptions: SubscriptionVisibilityReader) -> None:
        self.repository = repository
        self.documents = documents
        self.subscriptions = subscriptions
        self.visibility = ProviderVisibilityService()

    @staticmethod
    def _cursor_offset(cursor: str | None) -> int:
        if not cursor:
            return 0
        try:
            decoded = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("ascii")
            version, offset = decoded.split(":", 1)
            if version != "v1" or int(offset) < 0:
                raise ValueError
            return int(offset)
        except (ValueError, UnicodeError) as error:
            raise InvalidSearchError("Invalid search cursor") from error

    @staticmethod
    def _next_cursor(offset: int) -> str:
        return base64.urlsafe_b64encode(f"v1:{offset}".encode("ascii")).decode("ascii")

    @staticmethod
    def _validate(request: SearchRequest) -> None:
        has_latitude = request.latitude is not None
        has_longitude = request.longitude is not None
        if has_latitude != has_longitude:
            raise InvalidSearchError("Latitude and longitude must be supplied together")
        if request.mode in {SearchMode.NEARBY, SearchMode.HYBRID, SearchMode.AT_PROVIDER_LOCATION, SearchMode.PICKUP_DELIVERY} and not has_latitude:
            raise InvalidSearchError("This search mode requires browser-provided coordinates")
        if request.sort == SearchSort.DISTANCE and not has_latitude:
            raise InvalidSearchError("Distance sorting requires browser-provided coordinates")

    @staticmethod
    def _mode_match(candidate: SearchCandidate, request: SearchRequest) -> bool:
        modalities = candidate.modalities
        has_location = request.latitude is not None
        if request.mode == SearchMode.REMOTE:
            return ProviderModality.REMOTE in modalities
        if request.mode == SearchMode.NEARBY:
            return bool(
                (candidate.coverage_matches and modalities & ProviderVisibilityService.coverage_modalities)
                or (candidate.provider_location_matches and ProviderModality.AT_PROVIDER_LOCATION in modalities)
            )
        if request.mode == SearchMode.HYBRID:
            return ProviderModality.HYBRID in modalities and candidate.coverage_matches
        if request.mode == SearchMode.AT_PROVIDER_LOCATION:
            return ProviderModality.AT_PROVIDER_LOCATION in modalities and candidate.provider_location_matches
        if request.mode == SearchMode.PICKUP_DELIVERY:
            return ProviderModality.PICKUP_DELIVERY in modalities and candidate.coverage_matches
        if not has_location:
            return ProviderModality.REMOTE in modalities
        return bool(
            ProviderModality.REMOTE in modalities
            or (candidate.coverage_matches and modalities & ProviderVisibilityService.coverage_modalities)
            or (candidate.provider_location_matches and ProviderModality.AT_PROVIDER_LOCATION in modalities)
        )

    @staticmethod
    def _public_offer(candidate: SearchCandidate, request: SearchRequest | None = None) -> PublicProviderOffer:
        remote_only = request is not None and request.mode == SearchMode.REMOTE
        has_location = request is not None and request.latitude is not None
        expose_geo = bool(has_location and not remote_only and (candidate.coverage_matches or candidate.provider_location_matches))
        return PublicProviderOffer(
            id=candidate.offer_id,
            service_id=candidate.service_id,
            service_name=candidate.service_name,
            service_slug=candidate.service_slug,
            subcategory_name=candidate.subcategory_name,
            subcategory_slug=candidate.subcategory_slug,
            category_name=candidate.category_name,
            category_slug=candidate.category_slug,
            headline=candidate.headline,
            description=candidate.description,
            pricing_type=candidate.pricing_type,
            price_amount=candidate.price_amount,
            price_currency=candidate.price_currency,
            estimated_duration_minutes=candidate.estimated_duration_minutes,
            guarantee_days=candidate.guarantee_days,
            accepts_urgent=candidate.accepts_urgent,
            modalities=sorted(candidate.modalities, key=lambda item: item.value),
            available_today=candidate.available_today,
            distance_meters=int((candidate.distance_meters + 50) // 100) * 100 if expose_geo and candidate.distance_meters is not None else None,
            approximate_latitude=candidate.approximate_latitude if expose_geo else None,
            approximate_longitude=candidate.approximate_longitude if expose_geo else None,
        )

    @classmethod
    def _result(cls, candidate: SearchCandidate, request: SearchRequest) -> ProviderSearchResult:
        return ProviderSearchResult(
            provider_slug=candidate.provider_slug,
            display_name=candidate.display_name,
            business_name=candidate.business_name,
            rating_average=candidate.rating_average,
            rating_count=candidate.rating_count,
            completed_services_count=candidate.completed_services_count,
            response_rate=candidate.response_rate,
            average_response_minutes=candidate.average_response_minutes,
            profile_completeness=candidate.profile_completeness,
            is_identity_verified=candidate.is_identity_verified,
            is_demo=candidate.is_demo,
            offer=cls._public_offer(candidate, request),
        )

    async def _visible(self, candidates: list[SearchCandidate]) -> list[SearchCandidate]:
        subscriptions: dict[UUID, SubscriptionVisibilityStatus] = {}
        documents: dict[tuple[UUID, UUID], RequirementReadiness] = {}
        visible: list[SearchCandidate] = []
        settings = get_settings()
        for candidate in candidates:
            demo_visible = candidate.is_demo and settings.demo_mode and settings.app_env.lower() != "production"
            if demo_visible:
                subscription_status = SubscriptionVisibilityStatus.ACTIVE
                readiness = RequirementReadiness(ready=True, expired=False)
            else:
                if candidate.provider_id not in subscriptions:
                    subscriptions[candidate.provider_id] = await self.subscriptions.status(candidate.provider_id)
                document_key = (candidate.provider_id, candidate.service_id)
                if document_key not in documents:
                    documents[document_key] = await self.documents.readiness(*document_key)
                subscription_status = subscriptions[candidate.provider_id]
                readiness = documents[document_key]
            result = self.visibility.evaluate(ProviderVisibilityContext(
                user_active=candidate.user_status == UserStatus.ACTIVE,
                profile_status=candidate.profile_status,
                profile_paused=candidate.profile_paused,
                subscription_status=subscription_status,
                service_status=candidate.service_status,
                modalities=candidate.modalities,
                has_service_area=candidate.has_service_area,
                documents_ready=readiness.ready,
                documents_expired=readiness.expired,
            ))
            if result.visible:
                visible.append(candidate)
        return visible

    @staticmethod
    def _rank(candidate: SearchCandidate, request: SearchRequest, terms: tuple[str, ...]) -> tuple:
        requested_slug = request.service_slug or normalize_search_slug(request.query)
        exact = 0 if requested_slug and candidate.service_slug == requested_slug else 1
        relevance = min(
            [0 if term == candidate.service_slug else 1 if term in candidate.service_slug else 2 if term in candidate.subcategory_slug else 3 if term in candidate.category_slug else 4 for term in terms]
            or [0]
        )
        distance = candidate.distance_meters if candidate.distance_meters is not None else float("inf")
        if request.sort == SearchSort.RATING:
            selected = (-candidate.rating_average, relevance, distance)
        elif request.sort == SearchSort.DISTANCE:
            selected = (distance, relevance, -candidate.rating_average)
        else:
            selected = (relevance, not candidate.available_today, -candidate.rating_average)
        return (
            exact,
            *selected,
            -candidate.completed_services_count,
            -candidate.response_rate,
            distance,
            -candidate.profile_completeness,
            candidate.provider_slug,
            candidate.service_slug,
        )

    async def search(self, request: SearchRequest) -> ProviderSearchPage:
        self._validate(request)
        terms = normalize_search_terms(request.query)
        candidates = await self.repository.candidates(
            terms=terms,
            service_slug=request.service_slug,
            category_slug=request.category_slug,
            subcategory_slug=request.subcategory_slug,
            latitude=request.latitude,
            longitude=request.longitude,
            search_radius_meters=request.radius_meters,
        )
        candidates = [item for item in await self._visible(candidates) if self._mode_match(item, request)]
        if request.available_today:
            candidates = [item for item in candidates if item.available_today]
        candidates.sort(key=lambda item: self._rank(item, request, terms))

        # Keep one best matching offer per provider in the provider search.
        unique: list[SearchCandidate] = []
        seen: set[UUID] = set()
        for candidate in candidates:
            if candidate.provider_id not in seen:
                seen.add(candidate.provider_id)
                unique.append(candidate)

        offset = self._cursor_offset(request.cursor)
        page = unique[offset:offset + request.limit]
        next_offset = offset + len(page)
        return ProviderSearchPage(
            results=[self._result(item, request) for item in page],
            count=len(unique),
            next_cursor=self._next_cursor(next_offset) if next_offset < len(unique) else None,
            mode=request.mode,
            location_applied=request.latitude is not None,
        )

    async def profile(self, slug: str) -> PublicProviderProfile | None:
        candidates = await self.repository.candidates(provider_slug=slug)
        visible = await self._visible(candidates)
        if not visible:
            return None
        first = visible[0]
        portfolio = await self.repository.portfolio(first.provider_id)
        return PublicProviderProfile(
            slug=first.provider_slug,
            display_name=first.display_name,
            business_name=first.business_name,
            bio=first.bio,
            experience_years=first.experience_years,
            rating_average=first.rating_average,
            rating_count=first.rating_count,
            completed_services_count=first.completed_services_count,
            response_rate=first.response_rate,
            average_response_minutes=first.average_response_minutes,
            profile_completeness=first.profile_completeness,
            is_identity_verified=first.is_identity_verified,
            is_demo=first.is_demo,
            documents_verified=True,
            portfolio=[PublicPortfolioItem(title=item.title, description=item.description, position=item.position) for item in portfolio],
            services=[self._public_offer(item) for item in visible],
        )

    async def services(self, slug: str) -> list[PublicProviderOffer] | None:
        profile = await self.profile(slug)
        return profile.services if profile else None
