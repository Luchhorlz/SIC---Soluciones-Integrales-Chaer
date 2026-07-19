import os
from uuid import uuid4

import pytest
from geoalchemy2.elements import WKTElement
from sqlalchemy import delete, select

from sic_api.db.session import SessionFactory
from sic_api.modules.addresses.models import Address
from sic_api.modules.addresses.repository import SqlAlchemyAddressRepository
from sic_api.modules.catalog.models import Service
from sic_api.modules.catalog.repository import SqlAlchemyCatalogRepository
from sic_api.modules.catalog.service import CatalogService
from sic_api.modules.provider_services.models import PricingType, ProviderModality, ProviderServiceStatus
from sic_api.modules.provider_services.repository import SqlAlchemyProviderServiceRepository
from sic_api.modules.provider_services.schemas import AvailabilityRuleInput, AvailabilityRulesReplace, ProviderServiceCreate
from sic_api.modules.provider_services.service import ProviderOfferService
from sic_api.modules.providers.repository import SqlAlchemyProviderRepository
from sic_api.modules.providers.schemas import ProviderOnboarding
from sic_api.modules.providers.service import ProviderProfileService
from sic_api.modules.providers.visibility import VisibilityCode
from sic_api.modules.users.models import User, UserRole, UserRoleName

pytestmark = pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL/PostGIS integration runs in CI")


@pytest.mark.anyio
async def test_provider_offer_round_trip_on_postgis() -> None:
    user_id = uuid4()
    async with SessionFactory() as session:
        try:
            user = User(id=user_id, google_subject=f"provider-test-{user_id}", email=f"provider-{user_id}@example.invalid", name="Provider integration test")
            session.add_all([user, UserRole(user_id=user_id, role=UserRoleName.PROVIDER)])
            address = Address(user_id=user_id, label="Base", formatted_address="Dirección de prueba", street="Calle de prueba", street_number="1", unit=None, city="Buenos Aires", administrative_area=None, province="Buenos Aires", postal_code=None, country_code="AR", google_place_id=f"test-{user_id}", point=WKTElement("POINT(-58.3816 -34.6037)", srid=4326), is_default=True)
            session.add(address)
            await session.commit()
            await session.refresh(address)

            profile_service = ProviderProfileService(SqlAlchemyProviderRepository(session), SqlAlchemyAddressRepository(session))
            profile = await profile_service.onboard(user_id, ProviderOnboarding(display_name="Prestador de integración", bio="Perfil creado para validar la integración real.", experience_years=5, base_address_id=address.id))
            catalog_item = await session.scalar(select(Service).where(Service.is_active.is_(True), Service.allows_quote.is_(True)).limit(1))
            assert catalog_item is not None

            offer_service = ProviderOfferService(SqlAlchemyProviderServiceRepository(session), CatalogService(SqlAlchemyCatalogRepository(session)), SqlAlchemyAddressRepository(session))
            offer = await offer_service.create(user_id, profile, ProviderServiceCreate(service_id=catalog_item.id, headline="Servicio de integración", description="Oferta creada para verificar el flujo completo sobre PostGIS.", pricing_type=PricingType.QUOTE, modalities={ProviderModality.REMOTE}))
            assert offer.status == ProviderServiceStatus.PENDING_DOCUMENTS
            assert offer.visible is False
            assert offer.visibility_code == VisibilityCode.PROFILE_NOT_APPROVED

            rules = await offer_service.replace_availability(profile, offer.id, AvailabilityRulesReplace(rules=[AvailabilityRuleInput(day_of_week=0, start_time="09:00", end_time="13:00")]))
            assert len(rules) == 1
        finally:
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()
