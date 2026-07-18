from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from sic_api.main import app
from sic_api.modules.catalog.schemas import CategoryUpdate, ServiceCreate
from sic_api.modules.catalog.seed import SeedCategory, SeedService, SeedSubcategory, TaxonomySeed, apply_taxonomy_seed
from sic_api.modules.identity.permissions import Principal, get_admin_principal


def taxonomy_document() -> TaxonomySeed:
    return TaxonomySeed(categories=[SeedCategory(code="CATEGORY_TEST", name="Categoría de prueba", slug="categoria-prueba", icon_key="test-category", subcategories=[SeedSubcategory(code="SUBCATEGORY_TEST", name="Subcategoría de prueba", slug="subcategoria-prueba", icon_key="test-subcategory", services=[SeedService(code="SERVICE_TEST", name="Servicio de prueba", slug="servicio-prueba", icon_key="test-service", allows_fixed_price=False, allows_quote=True, allows_urgent=False)])])])


class FakeSeedWriter:
    def __init__(self) -> None:
        self.categories: dict[str, UUID] = {}
        self.subcategories: dict[str, UUID] = {}
        self.services: dict[str, UUID] = {}

    async def upsert_category(self, item):
        return self.categories.setdefault(item.code, uuid4())

    async def upsert_subcategory(self, category_id, item):
        return self.subcategories.setdefault(item.code, uuid4())

    async def upsert_service(self, subcategory_id, item):
        return self.services.setdefault(item.code, uuid4())


@pytest.mark.anyio
async def test_taxonomy_seed_is_idempotent() -> None:
    writer = FakeSeedWriter()
    first = await apply_taxonomy_seed(writer, taxonomy_document())
    second = await apply_taxonomy_seed(writer, taxonomy_document())
    assert first == second
    assert len(writer.categories) == len(writer.subcategories) == len(writer.services) == 1


def test_taxonomy_rejects_duplicate_stable_codes() -> None:
    document = taxonomy_document().model_dump()
    document["categories"][0]["subcategories"][0]["code"] = "CATEGORY_TEST"
    with pytest.raises(ValidationError):
        TaxonomySeed.model_validate(document)


def test_canonical_taxonomy_has_the_approved_hierarchy() -> None:
    seed_path = Path(__file__).resolve().parents[3] / "seeds" / "taxonomy.json"
    document = TaxonomySeed.model_validate_json(seed_path.read_text(encoding="utf-8"))
    assert len(document.categories) == 29
    assert sum(len(category.subcategories) for category in document.categories) == 140
    assert sum(len(subcategory.services) for category in document.categories for subcategory in category.subcategories) == 1_392
    assert document.categories[0].name == "Hogar, instalaciones y mantenimiento"
    assert document.categories[-1].name == "Servicios funerarios y conmemorativos"


def test_empty_catalog_patch_is_rejected() -> None:
    with pytest.raises(ValidationError):
        CategoryUpdate()


def test_service_requires_a_pricing_mode() -> None:
    with pytest.raises(ValidationError):
        ServiceCreate(subcategory_id=uuid4(), code="SERVICE_TEST", name="Servicio de prueba", slug="servicio-prueba", icon_key="test-service", allows_fixed_price=False, allows_quote=False, allows_urgent=False)


@pytest.mark.anyio
async def test_admin_role_is_required() -> None:
    with pytest.raises(HTTPException) as error:
        await get_admin_principal(Principal(user_id=uuid4(), roles=frozenset({"CLIENT"}), session_id="test-session"))
    assert error.value.status_code == 403


@pytest.mark.anyio
async def test_admin_role_is_accepted() -> None:
    principal = Principal(user_id=uuid4(), roles=frozenset({"ADMIN"}), session_id="test-session")
    assert await get_admin_principal(principal) is principal


def test_catalog_has_no_delete_endpoints() -> None:
    catalog_paths = {path: methods for path, methods in app.openapi()["paths"].items() if "/catalog" in path}
    assert catalog_paths
    assert all("delete" not in methods for methods in catalog_paths.values())
