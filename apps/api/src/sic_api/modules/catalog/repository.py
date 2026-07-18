from typing import Protocol, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Category, Service, Subcategory
from .schemas import CategoryCreate, CategoryUpdate, CategoryView, ServiceCreate, ServiceUpdate, ServiceView, SubcategoryCreate, SubcategoryUpdate, SubcategoryView


class CatalogConflictError(ValueError):
    pass


class CatalogNotFoundError(LookupError):
    pass


class CatalogRepository(Protocol):
    async def list_tree(self, active_only: bool) -> list[CategoryView]: ...
    async def list_services(self, active_only: bool) -> list[ServiceView]: ...
    async def create_category(self, payload: CategoryCreate) -> CategoryView: ...
    async def update_category(self, item_id: UUID, payload: CategoryUpdate) -> CategoryView: ...
    async def create_subcategory(self, payload: SubcategoryCreate) -> SubcategoryView: ...
    async def update_subcategory(self, item_id: UUID, payload: SubcategoryUpdate) -> SubcategoryView: ...
    async def create_service(self, payload: ServiceCreate) -> ServiceView: ...
    async def update_service(self, item_id: UUID, payload: ServiceUpdate) -> ServiceView: ...


ModelType = TypeVar("ModelType", Category, Subcategory, Service)


class SqlAlchemyCatalogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _category_view(item: Category, subcategories: list[SubcategoryView] | None = None) -> CategoryView:
        return CategoryView(id=item.id, code=item.code, name=item.name, slug=item.slug, description=item.description, icon_key=item.icon_key, position=item.position, is_active=item.is_active, subcategories=subcategories or [])

    @staticmethod
    def _subcategory_view(item: Subcategory, services: list[ServiceView] | None = None) -> SubcategoryView:
        return SubcategoryView(id=item.id, category_id=item.category_id, code=item.code, name=item.name, slug=item.slug, description=item.description, icon_key=item.icon_key, position=item.position, is_active=item.is_active, services=services or [])

    @staticmethod
    def _service_view(item: Service) -> ServiceView:
        return ServiceView(id=item.id, subcategory_id=item.subcategory_id, code=item.code, name=item.name, slug=item.slug, description=item.description, icon_key=item.icon_key, is_active=item.is_active, allows_fixed_price=item.allows_fixed_price, allows_quote=item.allows_quote, allows_urgent=item.allows_urgent)

    async def list_tree(self, active_only: bool) -> list[CategoryView]:
        category_query = select(Category).order_by(Category.position, Category.name)
        subcategory_query = select(Subcategory).order_by(Subcategory.position, Subcategory.name)
        service_query = select(Service).order_by(Service.name)
        if active_only:
            category_query = category_query.where(Category.is_active.is_(True))
            subcategory_query = subcategory_query.where(Subcategory.is_active.is_(True))
            service_query = service_query.where(Service.is_active.is_(True))
        categories = (await self.session.scalars(category_query)).all()
        subcategories = (await self.session.scalars(subcategory_query)).all()
        services = (await self.session.scalars(service_query)).all()
        services_by_subcategory: dict[UUID, list[ServiceView]] = {}
        for item in services:
            services_by_subcategory.setdefault(item.subcategory_id, []).append(self._service_view(item))
        subcategories_by_category: dict[UUID, list[SubcategoryView]] = {}
        for item in subcategories:
            subcategories_by_category.setdefault(item.category_id, []).append(self._subcategory_view(item, services_by_subcategory.get(item.id, [])))
        return [self._category_view(item, subcategories_by_category.get(item.id, [])) for item in categories]

    async def list_services(self, active_only: bool) -> list[ServiceView]:
        query = select(Service).order_by(Service.name)
        if active_only:
            query = query.where(Service.is_active.is_(True))
        return [self._service_view(item) for item in (await self.session.scalars(query)).all()]

    async def _commit(self) -> None:
        try:
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise CatalogConflictError("Catalog code or slug already exists") from error

    async def _existing(self, model: type[ModelType], item_id: UUID) -> ModelType:
        item = await self.session.get(model, item_id)
        if item is None:
            raise CatalogNotFoundError
        return item

    async def _require_parent(self, model: type[ModelType], item_id: UUID) -> None:
        if await self.session.get(model, item_id) is None:
            raise CatalogNotFoundError

    @staticmethod
    def _changes(payload: CategoryUpdate | SubcategoryUpdate | ServiceUpdate) -> dict[str, object]:
        changes = payload.model_dump(exclude_unset=True)
        for key, value in changes.items():
            if isinstance(value, str):
                changes[key] = value.strip()
        return changes

    async def create_category(self, payload: CategoryCreate) -> CategoryView:
        item = Category(**payload.model_dump())
        self.session.add(item)
        await self._commit()
        await self.session.refresh(item)
        return self._category_view(item)

    async def update_category(self, item_id: UUID, payload: CategoryUpdate) -> CategoryView:
        item = await self._existing(Category, item_id)
        for key, value in self._changes(payload).items():
            setattr(item, key, value)
        await self._commit()
        await self.session.refresh(item)
        return self._category_view(item)

    async def create_subcategory(self, payload: SubcategoryCreate) -> SubcategoryView:
        await self._require_parent(Category, payload.category_id)
        item = Subcategory(**payload.model_dump())
        self.session.add(item)
        await self._commit()
        await self.session.refresh(item)
        return self._subcategory_view(item)

    async def update_subcategory(self, item_id: UUID, payload: SubcategoryUpdate) -> SubcategoryView:
        item = await self._existing(Subcategory, item_id)
        if payload.category_id is not None:
            await self._require_parent(Category, payload.category_id)
        for key, value in self._changes(payload).items():
            setattr(item, key, value)
        await self._commit()
        await self.session.refresh(item)
        return self._subcategory_view(item)

    async def create_service(self, payload: ServiceCreate) -> ServiceView:
        await self._require_parent(Subcategory, payload.subcategory_id)
        item = Service(**payload.model_dump())
        self.session.add(item)
        await self._commit()
        await self.session.refresh(item)
        return self._service_view(item)

    async def update_service(self, item_id: UUID, payload: ServiceUpdate) -> ServiceView:
        item = await self._existing(Service, item_id)
        if payload.subcategory_id is not None:
            await self._require_parent(Subcategory, payload.subcategory_id)
        for key, value in self._changes(payload).items():
            setattr(item, key, value)
        if not item.allows_fixed_price and not item.allows_quote:
            await self.session.rollback()
            raise CatalogConflictError("A service must allow fixed price or quote")
        await self._commit()
        await self.session.refresh(item)
        return self._service_view(item)
