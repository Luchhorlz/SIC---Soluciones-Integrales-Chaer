from dataclasses import replace
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from sic_api.modules.documents.repository import RequirementReadiness
from sic_api.modules.provider_services.models import PricingType, ProviderModality, ProviderServiceStatus
from sic_api.modules.providers.models import ProviderProfileStatus, SubscriptionVisibilityStatus
from sic_api.modules.search.repository import PortfolioEntry, SearchCandidate
from sic_api.modules.search.schemas import SearchMode
from sic_api.modules.search.service import InvalidSearchError, ProviderSearchService, SearchRequest, normalize_search_slug, normalize_search_terms
from sic_api.modules.users.models import UserStatus


class FakeSearchRepository:
    def __init__(self, candidates: list[SearchCandidate]) -> None:
        self.items = candidates

    async def candidates(self, **filters) -> list[SearchCandidate]:
        slug = filters.get("provider_slug")
        return [item for item in self.items if not slug or item.provider_slug == slug]

    async def portfolio(self, provider_id: UUID) -> list[PortfolioEntry]:
        return [PortfolioEntry(provider_id, "Trabajo documentado", "Descripción pública del trabajo.", 0)]


class ReadyDocuments:
    async def readiness(self, provider_id: UUID, service_id: UUID) -> RequirementReadiness:
        return RequirementReadiness(ready=True, expired=False)


class Subscriptions:
    def __init__(self, status: SubscriptionVisibilityStatus = SubscriptionVisibilityStatus.ACTIVE) -> None:
        self.value = status

    async def status(self, provider_id: UUID) -> SubscriptionVisibilityStatus:
        return self.value


def candidate(*, modalities: frozenset[ProviderModality] = frozenset({ProviderModality.REMOTE}), coverage_matches: bool = False, profile_status: ProviderProfileStatus = ProviderProfileStatus.APPROVED) -> SearchCandidate:
    provider_id = uuid4()
    return SearchCandidate(
        offer_id=uuid4(), provider_id=provider_id, user_status=UserStatus.ACTIVE, profile_status=profile_status,
        profile_paused=False, provider_slug=f"prestador-{provider_id.hex}", display_name="Prestador de prueba", business_name=None,
        bio="Perfil público de prueba", experience_years=4, rating_average=4.8, rating_count=12, completed_services_count=20,
        response_rate=95, average_response_minutes=25, profile_completeness=90, is_identity_verified=True,
        service_status=ProviderServiceStatus.ACTIVE, service_id=uuid4(), service_name="Reparación de pérdidas", service_slug="reparacion-de-perdidas",
        subcategory_name="Plomería", subcategory_slug="plomeria", category_name="Hogar, instalaciones y mantenimiento",
        category_slug="hogar-instalaciones-y-mantenimiento", headline="Reparación de pérdidas", description="Servicio de prueba visible.",
        pricing_type=PricingType.QUOTE, price_amount=Decimal("0"), price_currency="ARS", estimated_duration_minutes=60,
        guarantee_days=None, accepts_urgent=False, modalities=modalities, has_service_area=bool(modalities & {ProviderModality.AT_CLIENT_ADDRESS, ProviderModality.HYBRID, ProviderModality.PICKUP_DELIVERY}),
        coverage_matches=coverage_matches, distance_meters=850 if coverage_matches else None, approximate_latitude=-34.60 if coverage_matches else None,
        approximate_longitude=-58.38 if coverage_matches else None, available_today=True,
    )


@pytest.mark.anyio
async def test_remote_provider_does_not_need_location_or_expose_distance() -> None:
    item = replace(candidate(), distance_meters=321, approximate_latitude=-34.6037, approximate_longitude=-58.3816)
    result = await ProviderSearchService(FakeSearchRepository([item]), ReadyDocuments(), Subscriptions()).search(SearchRequest(query="plomero", mode=SearchMode.REMOTE))
    assert result.count == 1
    assert result.results[0].offer.distance_meters is None
    assert result.results[0].offer.approximate_latitude is None


@pytest.mark.anyio
async def test_nearby_search_excludes_provider_outside_coverage() -> None:
    inside = candidate(modalities=frozenset({ProviderModality.AT_CLIENT_ADDRESS}), coverage_matches=True)
    outside = candidate(modalities=frozenset({ProviderModality.AT_CLIENT_ADDRESS}), coverage_matches=False)
    result = await ProviderSearchService(FakeSearchRepository([inside, outside]), ReadyDocuments(), Subscriptions()).search(SearchRequest(query="plomería", mode=SearchMode.NEARBY, latitude=-34.60, longitude=-58.38))
    assert [entry.provider_slug for entry in result.results] == [inside.provider_slug]
    assert result.results[0].offer.distance_meters == 900
    assert result.results[0].offer.approximate_latitude == -34.60


@pytest.mark.anyio
async def test_invisible_provider_is_hidden_from_search_and_direct_profile() -> None:
    hidden = candidate(profile_status=ProviderProfileStatus.PAUSED)
    service = ProviderSearchService(FakeSearchRepository([hidden]), ReadyDocuments(), Subscriptions())
    assert (await service.search(SearchRequest(query="plomería", mode=SearchMode.REMOTE))).results == []
    assert await service.profile(hidden.provider_slug) is None


@pytest.mark.anyio
async def test_inactive_subscription_is_hidden() -> None:
    item = candidate()
    service = ProviderSearchService(FakeSearchRepository([item]), ReadyDocuments(), Subscriptions(SubscriptionVisibilityStatus.INACTIVE))
    assert (await service.search(SearchRequest(query="plomería", mode=SearchMode.REMOTE))).count == 0


@pytest.mark.anyio
async def test_profile_never_exposes_location() -> None:
    item = candidate(modalities=frozenset({ProviderModality.AT_CLIENT_ADDRESS}), coverage_matches=True)
    profile = await ProviderSearchService(FakeSearchRepository([item]), ReadyDocuments(), Subscriptions()).profile(item.provider_slug)
    assert profile is not None
    assert profile.services[0].distance_meters is None
    assert profile.services[0].approximate_latitude is None
    assert profile.portfolio[0].title == "Trabajo documentado"


def test_search_validation_and_normalization() -> None:
    assert normalize_search_terms("Plomería urgente") == ("plome", "urgen")
    assert normalize_search_slug("Reparación de pérdidas") == "reparacion-de-perdidas"
    with pytest.raises(InvalidSearchError):
        ProviderSearchService._validate(SearchRequest(mode=SearchMode.NEARBY))
