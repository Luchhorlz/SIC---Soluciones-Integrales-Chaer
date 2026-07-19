from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from geoalchemy2.elements import WKTElement
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sic_api.modules.providers.repository import BaseLocation

from .models import AvailabilityException, AvailabilityRule, ProviderService, ProviderServiceArea, ProviderServiceModality, ProviderServiceStatus
from .schemas import AvailabilityExceptionCreate, AvailabilityExceptionView, AvailabilityRuleInput, AvailabilityRuleView, ProviderServiceCreate


class ProviderServiceNotFoundError(LookupError):
    pass


class ProviderServiceConflictError(ValueError):
    pass


@dataclass(frozen=True)
class ProviderServiceConfiguration:
    service: ProviderService
    modalities: tuple[ProviderServiceModality, ...]
    area: ProviderServiceArea | None


class ProviderServiceRepository(Protocol):
    async def list(self, provider_id: UUID) -> list[ProviderServiceConfiguration]: ...
    async def get(self, provider_id: UUID, item_id: UUID) -> ProviderServiceConfiguration: ...
    async def create(self, provider_id: UUID, payload: ProviderServiceCreate, center: BaseLocation | None) -> ProviderServiceConfiguration: ...
    async def update(self, provider_id: UUID, item_id: UUID, payload: ProviderServiceCreate, center: BaseLocation | None) -> ProviderServiceConfiguration: ...
    async def set_paused(self, provider_id: UUID, item_id: UUID, paused: bool) -> ProviderServiceConfiguration: ...
    async def list_availability(self, provider_id: UUID, item_id: UUID) -> list[AvailabilityRuleView]: ...
    async def replace_availability(self, provider_id: UUID, item_id: UUID, rules: list[AvailabilityRuleInput]) -> list[AvailabilityRuleView]: ...
    async def list_exceptions(self, provider_id: UUID) -> list[AvailabilityExceptionView]: ...
    async def add_exception(self, provider_id: UUID, payload: AvailabilityExceptionCreate) -> AvailabilityExceptionView: ...
    async def delete_exception(self, provider_id: UUID, item_id: UUID) -> None: ...


class SqlAlchemyProviderServiceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _service(self, provider_id: UUID, item_id: UUID) -> ProviderService:
        item = await self.session.scalar(select(ProviderService).where(ProviderService.id == item_id, ProviderService.provider_id == provider_id))
        if item is None:
            raise ProviderServiceNotFoundError
        return item

    async def _configuration(self, item: ProviderService) -> ProviderServiceConfiguration:
        modalities = tuple((await self.session.scalars(select(ProviderServiceModality).where(ProviderServiceModality.provider_service_id == item.id, ProviderServiceModality.enabled.is_(True)).order_by(ProviderServiceModality.modality))).all())
        area = await self.session.scalar(select(ProviderServiceArea).where(ProviderServiceArea.provider_service_id == item.id))
        return ProviderServiceConfiguration(item, modalities, area)

    async def _commit(self) -> None:
        try:
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise ProviderServiceConflictError("This catalog service or schedule is already configured") from error

    async def _replace_relations(self, item: ProviderService, payload: ProviderServiceCreate, center: BaseLocation | None) -> None:
        await self.session.execute(delete(ProviderServiceModality).where(ProviderServiceModality.provider_service_id == item.id))
        self.session.add_all(ProviderServiceModality(provider_service_id=item.id, modality=modality, enabled=True) for modality in payload.modalities)
        await self.session.execute(delete(ProviderServiceArea).where(ProviderServiceArea.provider_service_id == item.id))
        if payload.area and center:
            self.session.add(ProviderServiceArea(
                provider_service_id=item.id,
                center_address_id=center.address_id,
                center=WKTElement(f"POINT({center.longitude} {center.latitude})", srid=4326),
                radius_meters=payload.area.radius_meters,
                urgent_radius_meters=payload.area.urgent_radius_meters,
                travel_fee_policy=payload.area.travel_fee_policy.strip() if payload.area.travel_fee_policy else None,
            ))

    @staticmethod
    def _apply(item: ProviderService, payload: ProviderServiceCreate) -> None:
        item.headline = payload.headline.strip()
        item.description = payload.description.strip()
        item.pricing_type = payload.pricing_type
        item.price_amount = payload.price_amount
        item.price_currency = "ARS"
        item.estimated_duration_minutes = payload.estimated_duration_minutes
        item.guarantee_days = payload.guarantee_days
        item.accepts_urgent = payload.accepts_urgent
        item.requires_quote_details = payload.requires_quote_details

    async def list(self, provider_id: UUID) -> list[ProviderServiceConfiguration]:
        items = (await self.session.scalars(select(ProviderService).where(ProviderService.provider_id == provider_id).order_by(ProviderService.created_at))).all()
        return [await self._configuration(item) for item in items]

    async def get(self, provider_id: UUID, item_id: UUID) -> ProviderServiceConfiguration:
        return await self._configuration(await self._service(provider_id, item_id))

    async def create(self, provider_id: UUID, payload: ProviderServiceCreate, center: BaseLocation | None) -> ProviderServiceConfiguration:
        item = ProviderService(provider_id=provider_id, service_id=payload.service_id, status=ProviderServiceStatus.PENDING_DOCUMENTS, headline=payload.headline.strip(), description=payload.description.strip(), pricing_type=payload.pricing_type, price_amount=payload.price_amount, price_currency="ARS", estimated_duration_minutes=payload.estimated_duration_minutes, guarantee_days=payload.guarantee_days, accepts_urgent=payload.accepts_urgent, requires_quote_details=payload.requires_quote_details)
        self.session.add(item)
        await self.session.flush()
        await self._replace_relations(item, payload, center)
        await self._commit()
        await self.session.refresh(item)
        return await self._configuration(item)

    async def update(self, provider_id: UUID, item_id: UUID, payload: ProviderServiceCreate, center: BaseLocation | None) -> ProviderServiceConfiguration:
        item = await self._service(provider_id, item_id)
        self._apply(item, payload)
        if item.status not in {ProviderServiceStatus.PAUSED, ProviderServiceStatus.SUSPENDED, ProviderServiceStatus.REJECTED}:
            item.status = ProviderServiceStatus.PENDING_DOCUMENTS
        await self._replace_relations(item, payload, center)
        await self._commit()
        await self.session.refresh(item)
        return await self._configuration(item)

    async def set_paused(self, provider_id: UUID, item_id: UUID, paused: bool) -> ProviderServiceConfiguration:
        item = await self._service(provider_id, item_id)
        if item.status == ProviderServiceStatus.SUSPENDED:
            raise ProviderServiceConflictError("An administratively suspended service cannot be resumed")
        item.status = ProviderServiceStatus.PAUSED if paused else ProviderServiceStatus.PENDING_DOCUMENTS
        await self._commit()
        return await self._configuration(item)

    @staticmethod
    def _availability_view(item: AvailabilityRule) -> AvailabilityRuleView:
        return AvailabilityRuleView(id=item.id, day_of_week=item.day_of_week, start_time=item.start_time, end_time=item.end_time, timezone=item.timezone, slot_duration_minutes=item.slot_duration_minutes, is_active=item.is_active)

    async def list_availability(self, provider_id: UUID, item_id: UUID) -> list[AvailabilityRuleView]:
        await self._service(provider_id, item_id)
        items = (await self.session.scalars(select(AvailabilityRule).where(AvailabilityRule.provider_id == provider_id, AvailabilityRule.provider_service_id == item_id).order_by(AvailabilityRule.day_of_week, AvailabilityRule.start_time))).all()
        return [self._availability_view(item) for item in items]

    async def replace_availability(self, provider_id: UUID, item_id: UUID, rules: list[AvailabilityRuleInput]) -> list[AvailabilityRuleView]:
        await self._service(provider_id, item_id)
        await self.session.execute(delete(AvailabilityRule).where(AvailabilityRule.provider_id == provider_id, AvailabilityRule.provider_service_id == item_id))
        self.session.add_all(AvailabilityRule(provider_id=provider_id, provider_service_id=item_id, **rule.model_dump()) for rule in rules)
        await self._commit()
        return await self.list_availability(provider_id, item_id)

    @staticmethod
    def _exception_view(item: AvailabilityException) -> AvailabilityExceptionView:
        return AvailabilityExceptionView(id=item.id, starts_at=item.starts_at, ends_at=item.ends_at, reason=item.reason, is_available_override=item.is_available_override)

    async def list_exceptions(self, provider_id: UUID) -> list[AvailabilityExceptionView]:
        items = (await self.session.scalars(select(AvailabilityException).where(AvailabilityException.provider_id == provider_id).order_by(AvailabilityException.starts_at))).all()
        return [self._exception_view(item) for item in items]

    async def add_exception(self, provider_id: UUID, payload: AvailabilityExceptionCreate) -> AvailabilityExceptionView:
        item = AvailabilityException(provider_id=provider_id, starts_at=payload.starts_at, ends_at=payload.ends_at, reason=payload.reason.strip() if payload.reason else None, is_available_override=payload.is_available_override)
        self.session.add(item)
        await self._commit()
        await self.session.refresh(item)
        return self._exception_view(item)

    async def delete_exception(self, provider_id: UUID, item_id: UUID) -> None:
        result = await self.session.execute(delete(AvailabilityException).where(AvailabilityException.id == item_id, AvailabilityException.provider_id == provider_id))
        if not result.rowcount:
            await self.session.rollback()
            raise ProviderServiceNotFoundError
        await self._commit()
