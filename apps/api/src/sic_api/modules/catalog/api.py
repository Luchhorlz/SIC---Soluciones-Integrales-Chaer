from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sic_api.db.session import get_session
from sic_api.modules.identity.permissions import AdminPrincipal

from .repository import CatalogConflictError, CatalogNotFoundError, SqlAlchemyCatalogRepository
from .schemas import CategoryCreate, CategoryUpdate, CategoryView, ServiceCreate, ServiceUpdate, ServiceView, SubcategoryCreate, SubcategoryUpdate, SubcategoryView
from .service import CatalogService

public_router = APIRouter(prefix="/v1/catalog", tags=["catalog"])
admin_router = APIRouter(prefix="/v1/admin/catalog", tags=["admin-catalog"])


def catalog_service(session: AsyncSession) -> CatalogService:
    return CatalogService(SqlAlchemyCatalogRepository(session))


def catalog_error(error: Exception) -> HTTPException:
    if isinstance(error, CatalogNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog item or parent not found")
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


@public_router.get("/categories", response_model=list[CategoryView])
async def list_categories(session: AsyncSession = Depends(get_session)) -> list[CategoryView]:
    return await catalog_service(session).public_tree()


@public_router.get("/services", response_model=list[ServiceView])
async def list_services(session: AsyncSession = Depends(get_session)) -> list[ServiceView]:
    return await catalog_service(session).public_services()


@admin_router.get("", response_model=list[CategoryView])
async def admin_catalog(_principal: AdminPrincipal, session: AsyncSession = Depends(get_session)) -> list[CategoryView]:
    return await catalog_service(session).admin_tree()


@admin_router.post("/categories", response_model=CategoryView, status_code=status.HTTP_201_CREATED)
async def create_category(payload: CategoryCreate, _principal: AdminPrincipal, session: AsyncSession = Depends(get_session)) -> CategoryView:
    try:
        return await catalog_service(session).create_category(payload)
    except (CatalogConflictError, CatalogNotFoundError) as error:
        raise catalog_error(error) from error


@admin_router.patch("/categories/{item_id}", response_model=CategoryView)
async def update_category(item_id: UUID, payload: CategoryUpdate, _principal: AdminPrincipal, session: AsyncSession = Depends(get_session)) -> CategoryView:
    try:
        return await catalog_service(session).update_category(item_id, payload)
    except (CatalogConflictError, CatalogNotFoundError) as error:
        raise catalog_error(error) from error


@admin_router.post("/subcategories", response_model=SubcategoryView, status_code=status.HTTP_201_CREATED)
async def create_subcategory(payload: SubcategoryCreate, _principal: AdminPrincipal, session: AsyncSession = Depends(get_session)) -> SubcategoryView:
    try:
        return await catalog_service(session).create_subcategory(payload)
    except (CatalogConflictError, CatalogNotFoundError) as error:
        raise catalog_error(error) from error


@admin_router.patch("/subcategories/{item_id}", response_model=SubcategoryView)
async def update_subcategory(item_id: UUID, payload: SubcategoryUpdate, _principal: AdminPrincipal, session: AsyncSession = Depends(get_session)) -> SubcategoryView:
    try:
        return await catalog_service(session).update_subcategory(item_id, payload)
    except (CatalogConflictError, CatalogNotFoundError) as error:
        raise catalog_error(error) from error


@admin_router.post("/services", response_model=ServiceView, status_code=status.HTTP_201_CREATED)
async def create_service(payload: ServiceCreate, _principal: AdminPrincipal, session: AsyncSession = Depends(get_session)) -> ServiceView:
    try:
        return await catalog_service(session).create_service(payload)
    except (CatalogConflictError, CatalogNotFoundError) as error:
        raise catalog_error(error) from error


@admin_router.patch("/services/{item_id}", response_model=ServiceView)
async def update_service(item_id: UUID, payload: ServiceUpdate, _principal: AdminPrincipal, session: AsyncSession = Depends(get_session)) -> ServiceView:
    try:
        return await catalog_service(session).update_service(item_id, payload)
    except (CatalogConflictError, CatalogNotFoundError) as error:
        raise catalog_error(error) from error
