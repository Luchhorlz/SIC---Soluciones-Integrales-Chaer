from uuid import UUID

from .repository import CatalogRepository
from .schemas import CategoryCreate, CategoryUpdate, CategoryView, ServiceCreate, ServiceUpdate, ServiceView, SubcategoryCreate, SubcategoryUpdate, SubcategoryView


class CatalogService:
    def __init__(self, repository: CatalogRepository) -> None:
        self.repository = repository

    async def public_tree(self) -> list[CategoryView]:
        return await self.repository.list_tree(active_only=True)

    async def public_services(self) -> list[ServiceView]:
        return await self.repository.list_services(active_only=True)

    async def admin_tree(self) -> list[CategoryView]:
        return await self.repository.list_tree(active_only=False)

    async def create_category(self, payload: CategoryCreate) -> CategoryView:
        return await self.repository.create_category(payload)

    async def update_category(self, item_id: UUID, payload: CategoryUpdate) -> CategoryView:
        return await self.repository.update_category(item_id, payload)

    async def create_subcategory(self, payload: SubcategoryCreate) -> SubcategoryView:
        return await self.repository.create_subcategory(payload)

    async def update_subcategory(self, item_id: UUID, payload: SubcategoryUpdate) -> SubcategoryView:
        return await self.repository.update_subcategory(item_id, payload)

    async def create_service(self, payload: ServiceCreate) -> ServiceView:
        return await self.repository.create_service(payload)

    async def update_service(self, item_id: UUID, payload: ServiceUpdate) -> ServiceView:
        return await self.repository.update_service(item_id, payload)
