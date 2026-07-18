import argparse
import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from sic_api.db.session import SessionFactory

from .models import Category, Service, Subcategory
from .schemas import IconKey, Slug, StableCode


class SeedService(BaseModel):
    code: StableCode
    name: str = Field(min_length=2, max_length=140)
    slug: Slug
    description: str | None = Field(default=None, max_length=2000)
    icon_key: IconKey
    is_active: bool = True
    allows_fixed_price: bool
    allows_quote: bool
    allows_urgent: bool


class SeedSubcategory(BaseModel):
    code: StableCode
    name: str = Field(min_length=2, max_length=120)
    slug: Slug
    description: str | None = Field(default=None, max_length=2000)
    icon_key: IconKey
    position: int = Field(default=0, ge=0, le=10_000)
    is_active: bool = True
    services: list[SeedService] = Field(min_length=1)


class SeedCategory(BaseModel):
    code: StableCode
    name: str = Field(min_length=2, max_length=120)
    slug: Slug
    description: str | None = Field(default=None, max_length=2000)
    icon_key: IconKey
    position: int = Field(default=0, ge=0, le=10_000)
    is_active: bool = True
    subcategories: list[SeedSubcategory] = Field(min_length=1)


class TaxonomySeed(BaseModel):
    version: int = Field(default=1, ge=1)
    categories: list[SeedCategory] = Field(min_length=1)

    @model_validator(mode="after")
    def identifiers_are_unique(self):
        codes: set[str] = set()
        category_slugs: set[str] = set()
        subcategory_slugs: set[str] = set()
        service_slugs: set[str] = set()

        def unique(value: str, values: set[str], label: str) -> None:
            if value in values:
                raise ValueError(f"Duplicate {label}: {value}")
            values.add(value)

        for category in self.categories:
            unique(category.code, codes, "stable code")
            unique(category.slug, category_slugs, "category slug")
            for subcategory in category.subcategories:
                unique(subcategory.code, codes, "stable code")
                unique(subcategory.slug, subcategory_slugs, "subcategory slug")
                for service in subcategory.services:
                    unique(service.code, codes, "stable code")
                    unique(service.slug, service_slugs, "service slug")
        return self


class SeedWriter(Protocol):
    async def upsert_category(self, item: SeedCategory) -> UUID: ...
    async def upsert_subcategory(self, category_id: UUID, item: SeedSubcategory) -> UUID: ...
    async def upsert_service(self, subcategory_id: UUID, item: SeedService) -> UUID: ...


class SqlAlchemySeedWriter:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_category(self, item: SeedCategory) -> UUID:
        values = item.model_dump(exclude={"subcategories"})
        statement = insert(Category).values(**values).on_conflict_do_update(index_elements=[Category.code], set_={**values, "updated_at": func.now()}).returning(Category.id)
        return (await self.session.execute(statement)).scalar_one()

    async def upsert_subcategory(self, category_id: UUID, item: SeedSubcategory) -> UUID:
        values = {"category_id": category_id, **item.model_dump(exclude={"services"})}
        statement = insert(Subcategory).values(**values).on_conflict_do_update(index_elements=[Subcategory.code], set_={**values, "updated_at": func.now()}).returning(Subcategory.id)
        return (await self.session.execute(statement)).scalar_one()

    async def upsert_service(self, subcategory_id: UUID, item: SeedService) -> UUID:
        values = {"subcategory_id": subcategory_id, **item.model_dump()}
        statement = insert(Service).values(**values).on_conflict_do_update(index_elements=[Service.code], set_={**values, "updated_at": func.now()}).returning(Service.id)
        return (await self.session.execute(statement)).scalar_one()


@dataclass(frozen=True)
class SeedSummary:
    categories: int
    subcategories: int
    services: int


async def apply_taxonomy_seed(writer: SeedWriter, document: TaxonomySeed) -> SeedSummary:
    subcategory_count = 0
    service_count = 0
    for category in document.categories:
        category_id = await writer.upsert_category(category)
        for subcategory in category.subcategories:
            subcategory_id = await writer.upsert_subcategory(category_id, subcategory)
            subcategory_count += 1
            for service in subcategory.services:
                await writer.upsert_service(subcategory_id, service)
                service_count += 1
    return SeedSummary(categories=len(document.categories), subcategories=subcategory_count, services=service_count)


async def seed_file(path: Path) -> SeedSummary:
    if not path.is_file():
        raise FileNotFoundError(f"Approved taxonomy file not found: {path}")
    document = TaxonomySeed.model_validate(json.loads(path.read_text(encoding="utf-8")))
    async with SessionFactory() as session:
        try:
            summary = await apply_taxonomy_seed(SqlAlchemySeedWriter(session), document)
            await session.commit()
            return summary
        except Exception:
            await session.rollback()
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the owner-approved SIC taxonomy idempotently.")
    parser.add_argument("--file", type=Path, default=Path("seeds/taxonomy.json"))
    args = parser.parse_args()
    summary = asyncio.run(seed_file(args.file))
    print(f"Seed applied: {summary.categories} categories, {summary.subcategories} subcategories, {summary.services} services")


if __name__ == "__main__":
    main()
