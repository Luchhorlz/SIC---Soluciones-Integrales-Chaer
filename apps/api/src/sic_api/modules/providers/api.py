from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sic_api.db.session import get_session
from sic_api.modules.addresses.repository import AddressNotFoundError, SqlAlchemyAddressRepository
from sic_api.modules.catalog.repository import SqlAlchemyCatalogRepository
from sic_api.modules.catalog.service import CatalogService
from sic_api.modules.identity.permissions import ProviderPrincipal
from sic_api.modules.provider_services.repository import ProviderServiceConflictError, ProviderServiceNotFoundError, SqlAlchemyProviderServiceRepository
from sic_api.modules.provider_services.schemas import AvailabilityExceptionCreate, AvailabilityExceptionView, AvailabilityRuleView, AvailabilityRulesReplace, ProviderServiceCreate, ProviderServicePauseRequest, ProviderServiceUpdate, ProviderServiceView
from sic_api.modules.provider_services.service import ProviderOfferService
from sic_api.modules.documents.repository import SqlAlchemyDocumentRepository
from sic_api.modules.documents.service import DocumentReadinessService
from sic_api.modules.subscriptions.repository import SqlAlchemySubscriptionRepository
from sic_api.modules.subscriptions.service import SubscriptionVisibilityService

from .repository import ProviderConflictError, ProviderNotFoundError, SqlAlchemyProviderRepository
from .schemas import PortfolioItemCreate, ProviderOnboarding, ProviderPauseRequest, ProviderProfileUpdate, ProviderProfileView
from .service import ProviderProfileService

router = APIRouter(prefix="/v1/provider", tags=["provider"])


def profile_service(session: AsyncSession) -> ProviderProfileService:
    return ProviderProfileService(SqlAlchemyProviderRepository(session), SqlAlchemyAddressRepository(session))


def offer_service(session: AsyncSession) -> ProviderOfferService:
    return ProviderOfferService(
        SqlAlchemyProviderServiceRepository(session),
        CatalogService(SqlAlchemyCatalogRepository(session)),
        SqlAlchemyAddressRepository(session),
        DocumentReadinessService(SqlAlchemyDocumentRepository(session)),
        SubscriptionVisibilityService(SqlAlchemySubscriptionRepository(session)),
    )


def provider_error(error: Exception) -> HTTPException:
    if isinstance(error, (ProviderNotFoundError, ProviderServiceNotFoundError, AddressNotFoundError)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider resource or owned address not found")
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


async def required_profile(principal: ProviderPrincipal, session: AsyncSession) -> ProviderProfileView:
    profile = await profile_service(session).get(principal.user_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider onboarding is required")
    return profile


@router.post("/onboarding", response_model=ProviderProfileView)
async def onboard_provider(payload: ProviderOnboarding, principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> ProviderProfileView:
    try:
        return await profile_service(session).onboard(principal.user_id, payload)
    except (ProviderConflictError, AddressNotFoundError) as error:
        raise provider_error(error) from error


@router.get("/profile", response_model=ProviderProfileView)
async def get_provider_profile(principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> ProviderProfileView:
    return await required_profile(principal, session)


@router.patch("/profile", response_model=ProviderProfileView)
async def update_provider_profile(payload: ProviderProfileUpdate, principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> ProviderProfileView:
    try:
        return await profile_service(session).update(principal.user_id, payload)
    except (ProviderConflictError, ProviderNotFoundError, AddressNotFoundError) as error:
        raise provider_error(error) from error


@router.post("/profile/pause", response_model=ProviderProfileView)
async def pause_provider_profile(payload: ProviderPauseRequest, principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> ProviderProfileView:
    try:
        return await profile_service(session).set_paused(principal.user_id, payload.paused)
    except ProviderNotFoundError as error:
        raise provider_error(error) from error


@router.post("/portfolio", response_model=ProviderProfileView, status_code=status.HTTP_201_CREATED)
async def add_portfolio_item(payload: PortfolioItemCreate, principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> ProviderProfileView:
    try:
        return await profile_service(session).add_portfolio_item(principal.user_id, payload)
    except (ProviderConflictError, ProviderNotFoundError) as error:
        raise provider_error(error) from error


@router.delete("/portfolio/{item_id}", response_model=ProviderProfileView)
async def delete_portfolio_item(item_id: UUID, principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> ProviderProfileView:
    try:
        return await profile_service(session).delete_portfolio_item(principal.user_id, item_id)
    except ProviderNotFoundError as error:
        raise provider_error(error) from error


@router.get("/services", response_model=list[ProviderServiceView])
async def list_provider_services(principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> list[ProviderServiceView]:
    profile = await required_profile(principal, session)
    return await offer_service(session).list(profile)


@router.post("/services", response_model=ProviderServiceView, status_code=status.HTTP_201_CREATED)
async def create_provider_service(payload: ProviderServiceCreate, principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> ProviderServiceView:
    try:
        profile = await required_profile(principal, session)
        return await offer_service(session).create(principal.user_id, profile, payload)
    except (ProviderServiceConflictError, AddressNotFoundError) as error:
        raise provider_error(error) from error


@router.patch("/services/{item_id}", response_model=ProviderServiceView)
async def update_provider_service(item_id: UUID, payload: ProviderServiceUpdate, principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> ProviderServiceView:
    try:
        profile = await required_profile(principal, session)
        return await offer_service(session).update(principal.user_id, profile, item_id, payload)
    except (ProviderServiceConflictError, ProviderServiceNotFoundError, AddressNotFoundError) as error:
        raise provider_error(error) from error


@router.post("/services/{item_id}/pause", response_model=ProviderServiceView)
async def pause_provider_service(item_id: UUID, payload: ProviderServicePauseRequest, principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> ProviderServiceView:
    try:
        profile = await required_profile(principal, session)
        return await offer_service(session).set_paused(profile, item_id, payload.paused)
    except (ProviderServiceConflictError, ProviderServiceNotFoundError) as error:
        raise provider_error(error) from error


@router.get("/services/{item_id}/availability", response_model=list[AvailabilityRuleView])
async def list_provider_availability(item_id: UUID, principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> list[AvailabilityRuleView]:
    try:
        profile = await required_profile(principal, session)
        return await offer_service(session).list_availability(profile, item_id)
    except ProviderServiceNotFoundError as error:
        raise provider_error(error) from error


@router.put("/services/{item_id}/availability", response_model=list[AvailabilityRuleView])
async def replace_provider_availability(item_id: UUID, payload: AvailabilityRulesReplace, principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> list[AvailabilityRuleView]:
    try:
        profile = await required_profile(principal, session)
        return await offer_service(session).replace_availability(profile, item_id, payload)
    except (ProviderServiceConflictError, ProviderServiceNotFoundError) as error:
        raise provider_error(error) from error


@router.get("/availability/exceptions", response_model=list[AvailabilityExceptionView])
async def list_provider_exceptions(principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> list[AvailabilityExceptionView]:
    profile = await required_profile(principal, session)
    return await offer_service(session).list_exceptions(profile)


@router.post("/availability/exceptions", response_model=AvailabilityExceptionView, status_code=status.HTTP_201_CREATED)
async def add_provider_exception(payload: AvailabilityExceptionCreate, principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> AvailabilityExceptionView:
    profile = await required_profile(principal, session)
    return await offer_service(session).add_exception(profile, payload)


@router.delete("/availability/exceptions/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider_exception(item_id: UUID, principal: ProviderPrincipal, session: AsyncSession = Depends(get_session)) -> None:
    try:
        profile = await required_profile(principal, session)
        await offer_service(session).delete_exception(profile, item_id)
    except ProviderServiceNotFoundError as error:
        raise provider_error(error) from error
