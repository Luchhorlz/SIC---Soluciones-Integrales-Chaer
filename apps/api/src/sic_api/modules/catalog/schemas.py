from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, model_validator

StableCode = Annotated[str, StringConstraints(pattern=r"^[A-Z][A-Z0-9_]{1,63}$")]
Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", min_length=2, max_length=160)]
IconKey = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", min_length=2, max_length=80)]


class CategoryCreate(BaseModel):
    code: StableCode
    name: str = Field(min_length=2, max_length=120)
    slug: Slug
    description: str | None = Field(default=None, max_length=2000)
    icon_key: IconKey
    position: int = Field(default=0, ge=0, le=10_000)
    is_active: bool = True


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    slug: Slug | None = None
    description: str | None = Field(default=None, max_length=2000)
    icon_key: IconKey | None = None
    position: int | None = Field(default=None, ge=0, le=10_000)
    is_active: bool | None = None

    @model_validator(mode="after")
    def has_changes(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class SubcategoryCreate(CategoryCreate):
    category_id: UUID


class SubcategoryUpdate(CategoryUpdate):
    category_id: UUID | None = None


class ServiceCreate(BaseModel):
    subcategory_id: UUID
    code: StableCode
    name: str = Field(min_length=2, max_length=140)
    slug: Slug
    description: str | None = Field(default=None, max_length=2000)
    icon_key: IconKey
    is_active: bool = True
    allows_fixed_price: bool
    allows_quote: bool
    allows_urgent: bool

    @model_validator(mode="after")
    def has_pricing_mode(self):
        if not self.allows_fixed_price and not self.allows_quote:
            raise ValueError("A service must allow fixed price or quote")
        return self


class ServiceUpdate(BaseModel):
    subcategory_id: UUID | None = None
    name: str | None = Field(default=None, min_length=2, max_length=140)
    slug: Slug | None = None
    description: str | None = Field(default=None, max_length=2000)
    icon_key: IconKey | None = None
    is_active: bool | None = None
    allows_fixed_price: bool | None = None
    allows_quote: bool | None = None
    allows_urgent: bool | None = None

    @model_validator(mode="after")
    def has_changes(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class ServiceView(BaseModel):
    id: UUID
    subcategory_id: UUID
    code: str
    name: str
    slug: str
    description: str | None
    icon_key: str
    is_active: bool
    allows_fixed_price: bool
    allows_quote: bool
    allows_urgent: bool


class SubcategoryView(BaseModel):
    id: UUID
    category_id: UUID
    code: str
    name: str
    slug: str
    description: str | None
    icon_key: str
    position: int
    is_active: bool
    services: list[ServiceView]


class CategoryView(BaseModel):
    id: UUID
    code: str
    name: str
    slug: str
    description: str | None
    icon_key: str
    position: int
    is_active: bool
    subcategories: list[SubcategoryView]
