from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from sic_api.db.base import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(140), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    icon_key: Mapped[str] = mapped_column(String(80))
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Subcategory(Base):
    __tablename__ = "subcategories"
    __table_args__ = (Index("ix_subcategories_category_position", "category_id", "position"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    category_id: Mapped[UUID] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"))
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(140), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    icon_key: Mapped[str] = mapped_column(String(80))
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Service(Base):
    __tablename__ = "services"
    __table_args__ = (Index("ix_services_subcategory_name", "subcategory_id", "name"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    subcategory_id: Mapped[UUID] = mapped_column(ForeignKey("subcategories.id", ondelete="RESTRICT"))
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(140))
    slug: Mapped[str] = mapped_column(String(160), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    icon_key: Mapped[str] = mapped_column(String(80))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    allows_fixed_price: Mapped[bool] = mapped_column(Boolean)
    allows_quote: Mapped[bool] = mapped_column(Boolean)
    allows_urgent: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
