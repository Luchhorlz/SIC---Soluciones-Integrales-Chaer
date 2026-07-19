from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from sic_api.main import app
from sic_api.modules.catalog.schemas import ServiceView
from sic_api.modules.identity.permissions import Principal, get_provider_principal
from sic_api.modules.provider_services.models import PricingType, ProviderModality, ProviderServiceStatus
from sic_api.modules.provider_services.repository import ProviderServiceConflictError
from sic_api.modules.provider_services.schemas import AvailabilityRuleInput, AvailabilityRulesReplace, ProviderServiceCreate
from sic_api.modules.provider_services.service import ProviderOfferService
from sic_api.modules.providers.models import ProviderProfileStatus, SubscriptionVisibilityStatus
from sic_api.modules.providers.repository import provider_slug
from sic_api.modules.providers.schemas import ProviderProfileView
from sic_api.modules.providers.visibility import ProviderVisibilityContext, ProviderVisibilityService, VisibilityCode


def visibility_context(**changes) -> ProviderVisibilityContext:
    values = {
        "user_active": True,
        "profile_status": ProviderProfileStatus.APPROVED,
        "profile_paused": False,
        "subscription_status": SubscriptionVisibilityStatus.ACTIVE,
        "service_status": ProviderServiceStatus.ACTIVE,
        "modalities": frozenset({ProviderModality.REMOTE}),
        "has_service_area": False,
        "documents_ready": True,
        "documents_expired": False,
    }
    values.update(changes)
    return ProviderVisibilityContext(**values)


def provider_profile() -> ProviderProfileView:
    return ProviderProfileView(id=uuid4(), display_name="Prestador de prueba", slug="prestador-prueba", business_name=None, bio="Descripción profesional completa", experience_years=5, base_address_id=uuid4(), profile_status=ProviderProfileStatus.DRAFT, subscription_visibility_status=SubscriptionVisibilityStatus.NOT_CONFIGURED, rating_average=0, rating_count=0, completed_services_count=0, response_rate=0, average_response_minutes=None, profile_completeness=80, is_identity_verified=False, is_paused=False, portfolio=[])


def catalog_service(*, fixed: bool = False, quote: bool = True, urgent: bool = False) -> ServiceView:
    return ServiceView(id=uuid4(), subcategory_id=uuid4(), code="SERVICE_TEST", name="Servicio de prueba", slug="servicio-prueba", description=None, icon_key="catalog-service", is_active=True, allows_fixed_price=fixed, allows_quote=quote, allows_urgent=urgent)


def offer_payload(**changes) -> ProviderServiceCreate:
    values = {"service_id": uuid4(), "headline": "Servicio profesional", "description": "Descripción suficientemente completa del servicio.", "pricing_type": PricingType.QUOTE, "price_amount": None, "modalities": {ProviderModality.REMOTE}}
    values.update(changes)
    return ProviderServiceCreate(**values)


def test_visibility_is_derived_from_every_requirement() -> None:
    evaluator = ProviderVisibilityService()
    assert evaluator.evaluate(visibility_context()).code == VisibilityCode.VISIBLE
    assert evaluator.evaluate(visibility_context(profile_paused=True)).code == VisibilityCode.PROFILE_PAUSED
    assert evaluator.evaluate(visibility_context(subscription_status=SubscriptionVisibilityStatus.NOT_CONFIGURED)).code == VisibilityCode.NO_ACTIVE_SUBSCRIPTION
    assert evaluator.evaluate(visibility_context(modalities=frozenset({ProviderModality.HYBRID}), has_service_area=False)).code == VisibilityCode.NO_SERVICE_AREA
    assert evaluator.evaluate(visibility_context(documents_ready=False)).code == VisibilityCode.DOCUMENT_PENDING


def test_quote_and_direct_price_validation() -> None:
    with pytest.raises(ValidationError):
        offer_payload(price_amount=Decimal("100"))
    with pytest.raises(ValidationError):
        offer_payload(pricing_type=PricingType.FIXED, price_amount=None)


def test_availability_rejects_overlapping_ranges() -> None:
    with pytest.raises(ValidationError):
        AvailabilityRulesReplace(rules=[AvailabilityRuleInput(day_of_week=0, start_time="09:00", end_time="12:00"), AvailabilityRuleInput(day_of_week=0, start_time="11:00", end_time="14:00")])


def test_offer_rules_follow_catalog_capabilities() -> None:
    service = ProviderOfferService(repository=None, catalog=None, addresses=None)  # type: ignore[arg-type]
    with pytest.raises(ProviderServiceConflictError, match="direct prices"):
        service._validate(offer_payload(pricing_type=PricingType.FIXED, price_amount=Decimal("100")), catalog_service(fixed=False), provider_profile())
    with pytest.raises(ProviderServiceConflictError, match="coverage area"):
        service._validate(offer_payload(modalities={ProviderModality.AT_CLIENT_ADDRESS}), catalog_service(), provider_profile())


def test_provider_slug_is_stable_and_not_name_only() -> None:
    user_id = uuid4()
    assert provider_slug("Plomería Ñandú", user_id) == provider_slug("Plomería Ñandú", user_id)
    assert provider_slug("Plomería Ñandú", user_id).startswith("plomeria-nandu-")


@pytest.mark.anyio
async def test_provider_role_is_required() -> None:
    with pytest.raises(HTTPException) as error:
        await get_provider_principal(Principal(user_id=uuid4(), roles=frozenset({"CLIENT"}), session_id="test"))
    assert error.value.status_code == 403


def test_provider_api_denies_anonymous_requests() -> None:
    response = TestClient(app).get("/v1/provider/profile")
    assert response.status_code == 401
