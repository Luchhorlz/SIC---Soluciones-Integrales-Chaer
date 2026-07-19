from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from sic_api.db.session import get_session
from sic_api.modules.documents.repository import SqlAlchemyDocumentRepository
from sic_api.modules.documents.service import DocumentReadinessService
from sic_api.modules.identity.permissions import ClientPrincipal
from sic_api.modules.search.repository import SqlAlchemySearchRepository
from sic_api.modules.search.service import ProviderSearchService
from sic_api.modules.subscriptions.repository import SqlAlchemySubscriptionRepository
from sic_api.modules.subscriptions.service import SubscriptionVisibilityService

from .repository import FavoriteNotFoundError, SqlAlchemyFavoriteRepository
from .schemas import FavoriteProviderView
from .service import FavoriteService

router = APIRouter(prefix="/v1/client/favorites", tags=["client-favorites"])


def workflow(session: AsyncSession) -> FavoriteService:
    search = ProviderSearchService(SqlAlchemySearchRepository(session), DocumentReadinessService(SqlAlchemyDocumentRepository(session)), SubscriptionVisibilityService(SqlAlchemySubscriptionRepository(session)))
    return FavoriteService(SqlAlchemyFavoriteRepository(session), search)


@router.get("", response_model=list[FavoriteProviderView])
async def favorites(principal: ClientPrincipal, session: AsyncSession = Depends(get_session)) -> list[FavoriteProviderView]:
    return await workflow(session).list(principal.user_id)


@router.put("/{provider_slug}", response_model=FavoriteProviderView)
async def add_favorite(provider_slug: str, principal: ClientPrincipal, session: AsyncSession = Depends(get_session)) -> FavoriteProviderView:
    try:
        return await workflow(session).add(principal.user_id, provider_slug)
    except FavoriteNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visible provider not found") from error


@router.delete("/{provider_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(provider_slug: str, principal: ClientPrincipal, session: AsyncSession = Depends(get_session)) -> Response:
    try:
        await workflow(session).remove(principal.user_id, provider_slug)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except FavoriteNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favorite not found") from error
