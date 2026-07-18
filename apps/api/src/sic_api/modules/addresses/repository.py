from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from geoalchemy2 import Geometry
from geoalchemy2.elements import WKTElement
from sqlalchemy import cast, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Address
from .schemas import AddressCreate, AddressUpdate, AddressView


class AddressNotFoundError(LookupError):
    pass


class AddressRepository(Protocol):
    async def has_addresses(self, user_id: UUID) -> bool: ...
    async def create(self, user_id: UUID, payload: AddressCreate, make_default: bool) -> AddressView: ...
    async def list(self, user_id: UUID) -> list[AddressView]: ...
    async def update(self, user_id: UUID, address_id: UUID, payload: AddressUpdate) -> AddressView: ...
    async def delete(self, user_id: UUID, address_id: UUID) -> None: ...


class SqlAlchemyAddressRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def has_addresses(self, user_id: UUID) -> bool:
        return bool(await self.session.scalar(select(func.count(Address.id)).where(Address.user_id == user_id)))

    async def _unset_defaults(self, user_id: UUID) -> None:
        await self.session.execute(update(Address).where(Address.user_id == user_id).values(is_default=False))

    def _view(self, address: Address, latitude: float, longitude: float) -> AddressView:
        return AddressView(id=address.id, label=address.label, formatted_address=address.formatted_address, street=address.street, street_number=address.street_number, unit=address.unit, city=address.city, administrative_area=address.administrative_area, province=address.province, postal_code=address.postal_code, country_code=address.country_code, google_place_id=address.google_place_id, latitude=latitude, longitude=longitude, is_default=address.is_default)

    async def _get_with_coordinates(self, user_id: UUID, address_id: UUID) -> AddressView:
        geometry = cast(Address.point, Geometry(geometry_type="POINT", srid=4326))
        row = (await self.session.execute(select(Address, func.ST_Y(geometry), func.ST_X(geometry)).where(Address.id == address_id, Address.user_id == user_id))).one_or_none()
        if row is None:
            raise AddressNotFoundError
        return self._view(row[0], float(row[1]), float(row[2]))

    async def create(self, user_id: UUID, payload: AddressCreate, make_default: bool) -> AddressView:
        if make_default:
            await self._unset_defaults(user_id)
        address = Address(user_id=user_id, label=payload.label.strip(), formatted_address=payload.formatted_address.strip(), street=payload.street.strip(), street_number=payload.street_number.strip(), unit=payload.unit.strip() if payload.unit else None, city=payload.city.strip(), administrative_area=payload.administrative_area.strip() if payload.administrative_area else None, province=payload.province.strip(), postal_code=payload.postal_code.strip() if payload.postal_code else None, country_code=payload.country_code.upper(), google_place_id=payload.google_place_id, point=WKTElement(f"POINT({payload.longitude} {payload.latitude})", srid=4326), is_default=make_default)
        self.session.add(address)
        await self.session.commit()
        await self.session.refresh(address)
        return self._view(address, payload.latitude, payload.longitude)

    async def list(self, user_id: UUID) -> list[AddressView]:
        geometry = cast(Address.point, Geometry(geometry_type="POINT", srid=4326))
        rows = (await self.session.execute(select(Address, func.ST_Y(geometry), func.ST_X(geometry)).where(Address.user_id == user_id).order_by(Address.is_default.desc(), Address.created_at))).all()
        return [self._view(row[0], float(row[1]), float(row[2])) for row in rows]

    async def update(self, user_id: UUID, address_id: UUID, payload: AddressUpdate) -> AddressView:
        address = await self.session.scalar(select(Address).where(Address.id == address_id, Address.user_id == user_id))
        if address is None:
            raise AddressNotFoundError
        changes = payload.model_dump(exclude_unset=True, exclude={"latitude", "longitude"})
        if changes.pop("is_default", False):
            await self._unset_defaults(user_id)
            address.is_default = True
        for field, value in changes.items():
            setattr(address, field, value.strip() if isinstance(value, str) else value)
        if payload.latitude is not None and payload.longitude is not None:
            address.point = WKTElement(f"POINT({payload.longitude} {payload.latitude})", srid=4326)
        await self.session.commit()
        return await self._get_with_coordinates(user_id, address_id)

    async def delete(self, user_id: UUID, address_id: UUID) -> None:
        address = await self.session.scalar(select(Address).where(Address.id == address_id, Address.user_id == user_id))
        if address is None:
            raise AddressNotFoundError
        was_default = address.is_default
        await self.session.execute(delete(Address).where(Address.id == address_id, Address.user_id == user_id))
        if was_default:
            replacement = await self.session.scalar(select(Address).where(Address.user_id == user_id, Address.id != address_id).order_by(Address.created_at).limit(1))
            if replacement is not None:
                replacement.is_default = True
        await self.session.commit()
