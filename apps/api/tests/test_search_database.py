import os
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from geoalchemy2 import Geography
from geoalchemy2.elements import WKTElement
from sqlalchemy import cast, delete, func, select

from sic_api.db.session import SessionFactory
from sic_api.modules.addresses.models import Address
from sic_api.modules.catalog.models import Service
from sic_api.modules.documents.repository import SqlAlchemyDocumentRepository
from sic_api.modules.documents.service import DocumentReadinessService
from sic_api.modules.provider_services.models import PricingType, ProviderModality, ProviderService, ProviderServiceArea, ProviderServiceModality, ProviderServiceStatus
from sic_api.modules.providers.models import ProviderProfile, ProviderProfileStatus
from sic_api.modules.search.repository import SqlAlchemySearchRepository
from sic_api.modules.search.schemas import SearchMode
from sic_api.modules.search.service import ProviderSearchService, SearchRequest
from sic_api.modules.subscriptions.models import BillingFrequency, ProviderSubscription, ProviderSubscriptionStatus, SubscriptionPlan
from sic_api.modules.subscriptions.repository import SqlAlchemySubscriptionRepository
from sic_api.modules.subscriptions.service import SubscriptionVisibilityService
from sic_api.modules.users.models import User

pytestmark = pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="PostgreSQL/PostGIS search integration runs in CI")


@pytest.mark.anyio
async def test_postgis_search_coverage_boundary_and_public_privacy() -> None:
    user_id = uuid4()
    provider_id = uuid4()
    plan_id = uuid4()
    async with SessionFactory() as session:
        try:
            catalog_service = await session.scalar(select(Service).where(Service.is_active.is_(True)).limit(1))
            assert catalog_service is not None
            session.add(User(id=user_id, google_subject=f"search-test-{user_id}", email=f"search-{user_id}@example.invalid", name="Search integration"))
            await session.flush()
            address = Address(user_id=user_id, label="Centro privado", formatted_address="Dirección reservada", street="Calle de prueba", street_number="1", unit=None, city="Buenos Aires", administrative_area=None, province="Buenos Aires", postal_code=None, country_code="AR", google_place_id=f"search-place-{user_id}", point=WKTElement("POINT(-58.3816 -34.6037)", srid=4326), is_default=True)
            session.add(address)
            await session.flush()
            profile = ProviderProfile(id=provider_id, user_id=user_id, display_name="Prestador geográfico", slug=f"prestador-geografico-{user_id.hex}", bio="Perfil de integración geográfica.", base_address_id=address.id, base_point=WKTElement("POINT(-58.3816 -34.6037)", srid=4326), profile_status=ProviderProfileStatus.APPROVED, profile_completeness=90, is_identity_verified=True)
            session.add(profile)
            plan = SubscriptionPlan(id=plan_id, name="Plan búsqueda", code=f"SEARCH_{user_id.hex.upper()}", price=Decimal("1"), currency="ARS", billing_frequency=BillingFrequency.MONTHLY, is_active=False, features_json=[])
            session.add(plan)
            await session.flush()
            session.add(ProviderSubscription(provider_id=provider_id, plan_id=plan_id, status=ProviderSubscriptionStatus.ACTIVE))
            offer = ProviderService(provider_id=provider_id, service_id=catalog_service.id, status=ProviderServiceStatus.ACTIVE, headline="Servicio geográfico", description="Oferta de integración para validar cobertura sin exponer el domicilio.", pricing_type=PricingType.QUOTE, price_amount=None, price_currency="ARS", accepts_urgent=False, requires_quote_details=True)
            session.add(offer)
            await session.flush()
            session.add(ProviderServiceModality(provider_service_id=offer.id, modality=ProviderModality.AT_CLIENT_ADDRESS, enabled=True))
            session.add(ProviderServiceArea(provider_service_id=offer.id, center_address_id=address.id, center=WKTElement("POINT(-58.3816 -34.6037)", srid=4326), radius_meters=1500))
            await session.commit()

            search = ProviderSearchService(SqlAlchemySearchRepository(session), DocumentReadinessService(SqlAlchemyDocumentRepository(session)), SubscriptionVisibilityService(SqlAlchemySubscriptionRepository(session)))
            inside = await search.search(SearchRequest(service_slug=catalog_service.slug, mode=SearchMode.NEARBY, latitude=-34.6037, longitude=-58.3816))
            assert inside.count == 1
            assert inside.results[0].offer.approximate_latitude == -34.60
            assert inside.results[0].offer.approximate_longitude == -58.38

            outside = await search.search(SearchRequest(service_slug=catalog_service.slug, mode=SearchMode.NEARBY, latitude=-34.6037, longitude=-58.0))
            assert outside.count == 0

            limited_radius = await search.search(SearchRequest(service_slug=catalog_service.slug, mode=SearchMode.NEARBY, latitude=-34.6037, longitude=-58.3716, radius_meters=500))
            assert limited_radius.count == 0

            public_profile = await search.profile(profile.slug)
            assert public_profile is not None
            assert public_profile.services[0].approximate_latitude is None
            assert "address" not in public_profile.model_dump_json().lower()

            origin = cast(func.ST_SetSRID(func.ST_MakePoint(-58.3816, -34.6037), 4326), Geography(geometry_type="POINT", srid=4326))
            boundary = func.ST_Project(origin, 1500, func.radians(90))
            assert await session.scalar(select(func.ST_DWithin(origin, boundary, 1500))) is True

            profile.paused_at = datetime.now(timezone.utc)
            await session.commit()
            assert await search.profile(profile.slug) is None
        finally:
            await session.rollback()
            await session.execute(delete(ProviderSubscription).where(ProviderSubscription.provider_id == provider_id))
            await session.execute(delete(SubscriptionPlan).where(SubscriptionPlan.id == plan_id))
            await session.execute(delete(ProviderProfile).where(ProviderProfile.id == provider_id))
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()
