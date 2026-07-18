from datetime import datetime
from uuid import UUID, uuid4

from geoalchemy2 import Geography
from geoalchemy2.elements import WKBElement
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from sic_api.db.base import Base


class Address(Base):
    __tablename__ = "addresses"
    __table_args__ = (
        Index("uq_addresses_one_default_per_user", "user_id", unique=True, postgresql_where=text("is_default")),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(80))
    formatted_address: Mapped[str] = mapped_column(String(500))
    street: Mapped[str] = mapped_column(String(180))
    street_number: Mapped[str] = mapped_column(String(30))
    unit: Mapped[str | None] = mapped_column(String(50))
    city: Mapped[str] = mapped_column(String(120))
    administrative_area: Mapped[str | None] = mapped_column(String(120))
    province: Mapped[str] = mapped_column(String(120))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    country_code: Mapped[str] = mapped_column(String(2), default="AR")
    google_place_id: Mapped[str | None] = mapped_column(String(255))
    point: Mapped[WKBElement] = mapped_column(Geography(geometry_type="POINT", srid=4326, spatial_index=False))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
