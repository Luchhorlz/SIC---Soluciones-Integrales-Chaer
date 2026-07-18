from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from sic_api.db.session import get_session
from sic_api.modules.identity.permissions import CurrentPrincipal

from .repository import AddressNotFoundError, SqlAlchemyAddressRepository
from .schemas import AddressCreate, AddressUpdate, AddressView
from .service import AddressService

router = APIRouter(prefix="/v1/me/addresses", tags=["addresses"])


def service(session: AsyncSession) -> AddressService:
    return AddressService(SqlAlchemyAddressRepository(session))


@router.get("", response_model=list[AddressView])
async def list_addresses(principal: CurrentPrincipal, session: AsyncSession = Depends(get_session)) -> list[AddressView]:
    return await service(session).list(principal.user_id)


@router.post("", response_model=AddressView, status_code=status.HTTP_201_CREATED)
async def create_address(payload: AddressCreate, principal: CurrentPrincipal, session: AsyncSession = Depends(get_session)) -> AddressView:
    try:
        return await service(session).create(principal.user_id, payload)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error


@router.patch("/{address_id}", response_model=AddressView)
async def update_address(address_id: UUID, payload: AddressUpdate, principal: CurrentPrincipal, session: AsyncSession = Depends(get_session)) -> AddressView:
    try:
        return await service(session).update(principal.user_id, address_id, payload)
    except AddressNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found") from error


@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_address(address_id: UUID, principal: CurrentPrincipal, session: AsyncSession = Depends(get_session)) -> Response:
    try:
        await service(session).delete(principal.user_id, address_id)
    except AddressNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found") from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
