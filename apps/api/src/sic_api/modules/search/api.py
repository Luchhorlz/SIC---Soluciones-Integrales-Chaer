from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from sic_api.db.session import get_session
from sic_api.modules.documents.repository import SqlAlchemyDocumentRepository
from sic_api.modules.documents.service import DocumentReadinessService
from sic_api.modules.subscriptions.repository import SqlAlchemySubscriptionRepository
from sic_api.modules.subscriptions.service import SubscriptionVisibilityService

from .repository import SqlAlchemySearchRepository
from .schemas import ProviderSearchPage, PublicProviderOffer, PublicProviderProfile, SearchMode, SearchSort
from .service import InvalidSearchError, ProviderSearchService, SearchRequest

router = APIRouter(prefix="/v1", tags=["public-search"])


def search_service(session: AsyncSession) -> ProviderSearchService:
    return ProviderSearchService(
        SqlAlchemySearchRepository(session),
        DocumentReadinessService(SqlAlchemyDocumentRepository(session)),
        SubscriptionVisibilityService(SqlAlchemySubscriptionRepository(session)),
    )


@router.get("/search/providers", response_model=ProviderSearchPage)
async def search_providers(
    q: str | None = Query(default=None, min_length=2, max_length=160),
    service_slug: str | None = Query(default=None, max_length=160),
    category_slug: str | None = Query(default=None, max_length=140),
    subcategory_slug: str | None = Query(default=None, max_length=140),
    mode: SearchMode = SearchMode.ALL,
    latitude: float | None = Query(default=None, ge=-90, le=90),
    longitude: float | None = Query(default=None, ge=-180, le=180),
    radius_meters: int = Query(default=20_000, ge=500, le=100_000),
    available_today: bool = False,
    sort: SearchSort = SearchSort.RELEVANCE,
    cursor: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=20, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> ProviderSearchPage:
    try:
        return await search_service(session).search(SearchRequest(
            query=q,
            service_slug=service_slug,
            category_slug=category_slug,
            subcategory_slug=subcategory_slug,
            mode=mode,
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_meters,
            available_today=available_today,
            sort=sort,
            cursor=cursor,
            limit=limit,
        ))
    except InvalidSearchError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error


@router.get("/providers/{slug}", response_model=PublicProviderProfile)
async def public_provider(slug: str, session: AsyncSession = Depends(get_session)) -> PublicProviderProfile:
    profile = await search_service(session).profile(slug)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    return profile


@router.get("/providers/{slug}/services", response_model=list[PublicProviderOffer])
async def public_provider_services(slug: str, session: AsyncSession = Depends(get_session)) -> list[PublicProviderOffer]:
    services = await search_service(session).services(slug)
    if services is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    return services
