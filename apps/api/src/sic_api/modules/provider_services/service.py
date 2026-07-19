from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sic_api.modules.addresses.repository import AddressRepository
from sic_api.modules.catalog.schemas import ServiceView
from sic_api.modules.catalog.service import CatalogService
from sic_api.modules.providers.repository import BaseLocation
from sic_api.modules.providers.models import SubscriptionVisibilityStatus
from sic_api.modules.providers.schemas import ProviderProfileView
from sic_api.modules.providers.visibility import ProviderVisibilityContext, ProviderVisibilityService
from sic_api.modules.documents.repository import RequirementReadiness
from sic_api.modules.documents.service import DocumentReadinessReader

from .models import PricingType, ProviderModality
from .repository import ProviderServiceConfiguration, ProviderServiceConflictError, ProviderServiceRepository
from .schemas import AvailabilityExceptionCreate, AvailabilityExceptionView, AvailabilityRuleView, AvailabilityRulesReplace, ProviderServiceCreate, ProviderServiceUpdate, ProviderServiceView, ServiceAreaView


class PendingDocumentReadiness:
    async def readiness(self, provider_id: UUID, service_id: UUID) -> RequirementReadiness:
        return RequirementReadiness(ready=False, expired=False)


class SubscriptionVisibilityReader(Protocol):
    async def status(self, provider_id: UUID) -> SubscriptionVisibilityStatus: ...


class ProviderOfferService:
    coverage_modalities = frozenset({ProviderModality.AT_CLIENT_ADDRESS, ProviderModality.HYBRID, ProviderModality.PICKUP_DELIVERY})
    priced_types = frozenset({PricingType.FIXED, PricingType.FROM, PricingType.HOURLY, PricingType.PER_SESSION, PricingType.PER_UNIT})

    def __init__(self, repository: ProviderServiceRepository, catalog: CatalogService, addresses: AddressRepository, documents: DocumentReadinessReader | None = None, subscriptions: SubscriptionVisibilityReader | None = None) -> None:
        self.repository = repository
        self.catalog = catalog
        self.addresses = addresses
        self.documents = documents or PendingDocumentReadiness()
        self.subscriptions = subscriptions
        self.visibility = ProviderVisibilityService()

    async def _catalog_service(self, service_id: UUID) -> ServiceView:
        item = await self.catalog.get_service(service_id, active_only=True)
        if item is None:
            raise ProviderServiceConflictError("The selected catalog service is not active")
        return item

    async def _center(self, user_id: UUID, payload: ProviderServiceCreate) -> BaseLocation | None:
        if payload.area is None:
            return None
        address = await self.addresses.get(user_id, payload.area.center_address_id)
        return BaseLocation(address_id=address.id, latitude=address.latitude, longitude=address.longitude)

    def _validate(self, payload: ProviderServiceCreate, catalog: ServiceView, profile: ProviderProfileView) -> None:
        if payload.pricing_type == PricingType.QUOTE and not catalog.allows_quote:
            raise ProviderServiceConflictError("The catalog service does not allow quotes")
        if payload.pricing_type in self.priced_types and not catalog.allows_fixed_price:
            raise ProviderServiceConflictError("The catalog service does not allow direct prices")
        if payload.accepts_urgent and not catalog.allows_urgent:
            raise ProviderServiceConflictError("The catalog service does not allow urgent requests")
        needs_area = bool(payload.modalities & self.coverage_modalities)
        if needs_area and payload.area is None:
            raise ProviderServiceConflictError("In-person, hybrid and pickup services require their own coverage area")
        if not needs_area and payload.area is not None:
            raise ProviderServiceConflictError("This modality does not use a client coverage area")
        if ProviderModality.AT_PROVIDER_LOCATION in payload.modalities and profile.base_address_id is None:
            raise ProviderServiceConflictError("Provider-location services require a validated base address")
        if payload.area and payload.area.urgent_radius_meters and not payload.accepts_urgent:
            raise ProviderServiceConflictError("An urgent radius requires urgent requests to be enabled")

    async def _view(self, configuration: ProviderServiceConfiguration, profile: ProviderProfileView) -> ProviderServiceView:
        item = configuration.service
        modalities = [entry.modality for entry in configuration.modalities]
        area = ServiceAreaView(center_address_id=configuration.area.center_address_id, radius_meters=configuration.area.radius_meters, urgent_radius_meters=configuration.area.urgent_radius_meters, travel_fee_policy=configuration.area.travel_fee_policy) if configuration.area else None
        document_state = await self.documents.readiness(profile.id, item.service_id)
        subscription_status = await self.subscriptions.status(profile.id) if self.subscriptions else profile.subscription_visibility_status
        result = self.visibility.evaluate(ProviderVisibilityContext(
            user_active=True,
            profile_status=profile.profile_status,
            profile_paused=profile.is_paused,
            subscription_status=subscription_status,
            service_status=item.status,
            modalities=frozenset(modalities),
            has_service_area=area is not None,
            documents_ready=document_state.ready,
            documents_expired=document_state.expired,
        ))
        return ProviderServiceView(id=item.id, service_id=item.service_id, status=item.status, headline=item.headline, description=item.description, pricing_type=item.pricing_type, price_amount=item.price_amount, price_currency=item.price_currency, estimated_duration_minutes=item.estimated_duration_minutes, guarantee_days=item.guarantee_days, accepts_urgent=item.accepts_urgent, requires_quote_details=item.requires_quote_details, modalities=modalities, area=area, visibility_code=result.code, visible=result.visible)

    async def list(self, profile: ProviderProfileView) -> list[ProviderServiceView]:
        return [await self._view(item, profile) for item in await self.repository.list(profile.id)]

    async def _sync_document_status(self, configuration: ProviderServiceConfiguration) -> ProviderServiceConfiguration:
        state = await self.documents.readiness(configuration.service.provider_id, configuration.service.service_id)
        return await self.repository.set_document_readiness(configuration.service.provider_id, configuration.service.id, state.ready)

    async def create(self, user_id: UUID, profile: ProviderProfileView, payload: ProviderServiceCreate) -> ProviderServiceView:
        catalog = await self._catalog_service(payload.service_id)
        self._validate(payload, catalog, profile)
        configuration = await self.repository.create(profile.id, payload, await self._center(user_id, payload))
        return await self._view(await self._sync_document_status(configuration), profile)

    async def update(self, user_id: UUID, profile: ProviderProfileView, item_id: UUID, payload: ProviderServiceUpdate) -> ProviderServiceView:
        current = await self.repository.get(profile.id, item_id)
        item = current.service
        current_area = ServiceAreaView(center_address_id=current.area.center_address_id, radius_meters=current.area.radius_meters, urgent_radius_meters=current.area.urgent_radius_meters, travel_fee_policy=current.area.travel_fee_policy) if current.area else None
        values = {
            "service_id": item.service_id,
            "headline": item.headline,
            "description": item.description,
            "pricing_type": item.pricing_type,
            "price_amount": item.price_amount,
            "estimated_duration_minutes": item.estimated_duration_minutes,
            "guarantee_days": item.guarantee_days,
            "accepts_urgent": item.accepts_urgent,
            "requires_quote_details": item.requires_quote_details,
            "modalities": {entry.modality for entry in current.modalities},
            "area": current_area.model_dump() if current_area else None,
        }
        values.update(payload.model_dump(exclude_unset=True))
        effective = ProviderServiceCreate.model_validate(values)
        self._validate(effective, await self._catalog_service(item.service_id), profile)
        configuration = await self.repository.update(profile.id, item_id, effective, await self._center(user_id, effective))
        return await self._view(await self._sync_document_status(configuration), profile)

    async def set_paused(self, profile: ProviderProfileView, item_id: UUID, paused: bool) -> ProviderServiceView:
        configuration = await self.repository.set_paused(profile.id, item_id, paused)
        if not paused:
            configuration = await self._sync_document_status(configuration)
        return await self._view(configuration, profile)

    async def list_availability(self, profile: ProviderProfileView, item_id: UUID) -> list[AvailabilityRuleView]:
        return await self.repository.list_availability(profile.id, item_id)

    async def replace_availability(self, profile: ProviderProfileView, item_id: UUID, payload: AvailabilityRulesReplace) -> list[AvailabilityRuleView]:
        return await self.repository.replace_availability(profile.id, item_id, payload.rules)

    async def list_exceptions(self, profile: ProviderProfileView) -> list[AvailabilityExceptionView]:
        return await self.repository.list_exceptions(profile.id)

    async def add_exception(self, profile: ProviderProfileView, payload: AvailabilityExceptionCreate) -> AvailabilityExceptionView:
        return await self.repository.add_exception(profile.id, payload)

    async def delete_exception(self, profile: ProviderProfileView, item_id: UUID) -> None:
        await self.repository.delete_exception(profile.id, item_id)
