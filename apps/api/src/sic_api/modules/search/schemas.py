from __future__ import annotations

import enum
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from sic_api.modules.provider_services.models import PricingType, ProviderModality


class SearchMode(str, enum.Enum):
    ALL = "ALL"
    NEARBY = "NEARBY"
    REMOTE = "REMOTE"
    HYBRID = "HYBRID"
    AT_PROVIDER_LOCATION = "AT_PROVIDER_LOCATION"
    PICKUP_DELIVERY = "PICKUP_DELIVERY"


class SearchSort(str, enum.Enum):
    RELEVANCE = "RELEVANCE"
    RATING = "RATING"
    DISTANCE = "DISTANCE"


class PublicProviderOffer(BaseModel):
    id: UUID
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
    modalities: list[ProviderModality]
    available_today: bool
    distance_meters: int | None = Field(default=None, description="Approximate distance rounded to 100 metres")
    approximate_latitude: float | None = Field(default=None, description="Coarse point rounded to two decimal degrees")
    approximate_longitude: float | None = Field(default=None, description="Coarse point rounded to two decimal degrees")


class ProviderSearchResult(BaseModel):
    provider_slug: str
    display_name: str
    business_name: str | None
    rating_average: float
    rating_count: int
    completed_services_count: int
    response_rate: float
    average_response_minutes: int | None
    profile_completeness: int
    is_identity_verified: bool
    is_demo: bool
    offer: PublicProviderOffer


class ProviderSearchPage(BaseModel):
    results: list[ProviderSearchResult]
    count: int
    next_cursor: str | None
    mode: SearchMode
    location_applied: bool


class PublicPortfolioItem(BaseModel):
    title: str
    description: str
    position: int


class PublicProviderProfile(BaseModel):
    slug: str
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
    documents_verified: bool
    portfolio: list[PublicPortfolioItem]
    services: list[PublicProviderOffer]
