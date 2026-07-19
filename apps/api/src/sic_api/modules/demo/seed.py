from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid5

from geoalchemy2.elements import WKTElement
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from sic_api.db.session import SessionFactory
from sic_api.modules.addresses.models import Address
from sic_api.modules.catalog.models import Category, Service, Subcategory
from sic_api.modules.documents.models import DocumentReview, ProviderDocument
from sic_api.modules.engagements.models import Booking, Quote, RequestAttachment, ServiceRequest
from sic_api.modules.favorites.models import FavoriteProvider
from sic_api.modules.media.models import MediaFile
from sic_api.modules.messaging.models import Conversation, Message
from sic_api.modules.notifications.models import Notification
from sic_api.modules.provider_services.models import PricingType, ProviderModality, ProviderService, ProviderServiceArea, ProviderServiceModality, ProviderServiceStatus
from sic_api.modules.providers.models import ProviderPortfolioItem, ProviderProfile, ProviderProfileStatus, SubscriptionVisibilityStatus
from sic_api.modules.reviews.models import Review, ReviewRevision
from sic_api.modules.subscriptions.models import ProviderSubscription
from sic_api.modules.users.models import User, UserRole, UserRoleName, UserStatus
from sic_api.settings import get_settings


DEMO_NAMESPACE = UUID("12f50e16-6bb5-4f0f-a9cd-1eb67d319fd7")
DEMO_ADMIN_ID = UUID("10000000-0000-4000-8000-000000000001")
DEMO_CLIENT_ID = UUID("10000000-0000-4000-8000-000000000002")
DEMO_PROVIDER_LOGIN_ID = UUID("10000000-0000-4000-8000-000000000003")


class DemoLocation(BaseModel):
    city: str = Field(min_length=2, max_length=120)
    province: str = Field(min_length=2, max_length=120)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class DemoSeedConfig(BaseModel):
    version: int = Field(ge=1)
    dataset_key: str = Field(min_length=3, max_length=80)
    providers_per_service: int = Field(ge=3, le=3)
    first_names: list[str] = Field(min_length=18)
    last_names: list[str] = Field(min_length=18)
    locations: list[DemoLocation] = Field(min_length=1)
    remote_category_codes: set[str]
    provider_location_category_codes: set[str]

    @model_validator(mode="after")
    def names_are_unique(self):
        if len(set(self.first_names)) != len(self.first_names) or len(set(self.last_names)) != len(self.last_names):
            raise ValueError("Demo name pools must contain unique values")
        return self


@dataclass(frozen=True)
class CatalogService:
    id: UUID
    code: str
    name: str
    slug: str
    subcategory_name: str
    category_code: str
    category_name: str


@dataclass(frozen=True)
class DemoSeedSummary:
    services: int
    providers: int
    minimum_providers_per_service: int
    demo_login_users: int


def _stable_id(kind: str, service_code: str, slot: int) -> UUID:
    return uuid5(DEMO_NAMESPACE, f"{kind}:{service_code}:{slot}")


def _display_name(config: DemoSeedConfig, ordinal: int) -> str:
    first_count = len(config.first_names)
    last_count = len(config.last_names)
    first = config.first_names[ordinal % first_count]
    first_last = config.last_names[(ordinal // first_count) % last_count]
    second_last = config.last_names[((ordinal // (first_count * last_count)) + 5) % last_count]
    return f"{first} {first_last} {second_last}"


def _modality(config: DemoSeedConfig, category_code: str) -> ProviderModality:
    if category_code in config.remote_category_codes:
        return ProviderModality.REMOTE
    if category_code in config.provider_location_category_codes:
        return ProviderModality.AT_PROVIDER_LOCATION
    return ProviderModality.AT_CLIENT_ADDRESS


async def _bulk_upsert(
    session: AsyncSession,
    model,
    rows: list[dict],
    *,
    update_columns: tuple[str, ...],
    chunk_size: int = 250,
) -> None:
    for offset in range(0, len(rows), chunk_size):
        statement = insert(model).values(rows[offset:offset + chunk_size])
        if update_columns:
            statement = statement.on_conflict_do_update(
                index_elements=[model.id],
                set_={column: getattr(statement.excluded, column) for column in update_columns},
            )
        else:
            statement = statement.on_conflict_do_nothing()
        await session.execute(statement)


async def _catalog_services(session: AsyncSession) -> list[CatalogService]:
    rows = (await session.execute(
        select(Service.id, Service.code, Service.name, Service.slug, Subcategory.name, Category.code, Category.name)
        .join(Subcategory, Subcategory.id == Service.subcategory_id)
        .join(Category, Category.id == Subcategory.category_id)
        .where(Service.is_active.is_(True), Subcategory.is_active.is_(True), Category.is_active.is_(True))
        .order_by(Service.code)
    )).all()
    return [CatalogService(*row) for row in rows]


async def apply_demo_seed(session: AsyncSession, config: DemoSeedConfig) -> DemoSeedSummary:
    services = await _catalog_services(session)
    if len(services) != 1392:
        raise RuntimeError(f"The canonical 1,392-service catalog must be loaded first; found {len(services)}")

    login_users = [
        {"id": DEMO_ADMIN_ID, "google_subject": "demo-login:admin", "email": "admin@demo.sic.invalid", "name": "Administración Demo", "avatar_url": None, "phone": None, "is_demo": True, "status": UserStatus.ACTIVE},
        {"id": DEMO_CLIENT_ID, "google_subject": "demo-login:cliente", "email": "cliente@demo.sic.invalid", "name": "Cliente Demo", "avatar_url": None, "phone": None, "is_demo": True, "status": UserStatus.ACTIVE},
    ]
    users: list[dict] = []
    roles: list[dict] = [
        {"user_id": DEMO_ADMIN_ID, "role": UserRoleName.ADMIN},
        {"user_id": DEMO_CLIENT_ID, "role": UserRoleName.CLIENT},
    ]
    addresses: list[dict] = []
    profiles: list[dict] = []
    offers: list[dict] = []
    modalities: list[dict] = []
    areas: list[dict] = []

    for service_index, service in enumerate(services):
        for slot_index in range(config.providers_per_service):
            ordinal = service_index * config.providers_per_service + slot_index
            user_id = DEMO_PROVIDER_LOGIN_ID if ordinal == 0 else _stable_id("user", service.code, slot_index)
            profile_id = _stable_id("profile", service.code, slot_index)
            address_id = _stable_id("address", service.code, slot_index)
            offer_id = _stable_id("offer", service.code, slot_index)
            area_id = _stable_id("area", service.code, slot_index)
            location = config.locations[ordinal % len(config.locations)]
            display_name = _display_name(config, ordinal)
            slot = slot_index + 1
            modality = _modality(config, service.category_code)
            users.append({
                "id": user_id,
                "google_subject": "demo-login:servicio" if ordinal == 0 else f"demo-provider:{service.code.lower()}:{slot}",
                "email": "servicio@demo.sic.invalid" if ordinal == 0 else f"{service.code.lower()}-{slot}@demo.sic.invalid",
                "name": display_name,
                "avatar_url": f"/images/demo/provider-{(ordinal % 6) + 1:02d}.png",
                "phone": None,
                "is_demo": True,
                "status": UserStatus.ACTIVE,
            })
            roles.append({"user_id": user_id, "role": UserRoleName.PROVIDER})
            addresses.append({
                "id": address_id,
                "user_id": user_id,
                "label": "Base demo",
                "formatted_address": f"Avenida Demo {1000 + ordinal}, {location.city}, {location.province}",
                "street": "Avenida Demo",
                "street_number": str(1000 + ordinal),
                "unit": None,
                "city": location.city,
                "administrative_area": location.city,
                "province": location.province,
                "postal_code": None,
                "country_code": "AR",
                "google_place_id": f"sic-demo-{service.code.lower()}-{slot}",
                "point": WKTElement(f"POINT({location.longitude} {location.latitude})", srid=4326),
                "is_default": True,
            })
            profiles.append({
                "id": profile_id,
                "user_id": user_id,
                "display_name": display_name,
                "slug": f"demo-{service.slug}-{slot}",
                "business_name": f"{service.subcategory_name} · Profesional demo",
                "bio": f"Perfil ficticio de SIC para demostrar la búsqueda de {service.name.rstrip('.').lower()}. No representa a una persona ni una matrícula real.",
                "experience_years": 4 + (ordinal % 17),
                "base_address_id": address_id,
                "base_point": WKTElement(f"POINT({location.longitude} {location.latitude})", srid=4326),
                "profile_status": ProviderProfileStatus.APPROVED,
                "subscription_visibility_status": SubscriptionVisibilityStatus.ACTIVE,
                "rating_average": 4.6 + ((ordinal % 4) / 10),
                "rating_count": 18 + (ordinal % 83),
                "completed_services_count": 24 + (ordinal % 190),
                "response_rate": 91 + (ordinal % 9),
                "average_response_minutes": 8 + (ordinal % 42),
                "profile_completeness": 100,
                "is_identity_verified": True,
                "is_demo": True,
                "paused_at": None,
            })
            offers.append({
                "id": offer_id,
                "provider_id": profile_id,
                "service_id": service.id,
                "status": ProviderServiceStatus.ACTIVE,
                "headline": f"{service.name.rstrip('.')} con atención personalizada",
                "description": f"Oferta demostrativa para explorar cómo se presenta y solicita {service.name.rstrip('.').lower()} dentro de SIC.",
                "pricing_type": PricingType.QUOTE,
                "price_amount": None,
                "price_currency": "ARS",
                "estimated_duration_minutes": 60 + ((ordinal % 4) * 30),
                "guarantee_days": None,
                "accepts_urgent": False,
                "requires_quote_details": True,
            })
            modalities.append({"provider_service_id": offer_id, "modality": modality, "enabled": True})
            if modality == ProviderModality.AT_CLIENT_ADDRESS:
                areas.append({
                    "id": area_id,
                    "provider_service_id": offer_id,
                    "center_address_id": address_id,
                    "center": WKTElement(f"POINT({location.longitude} {location.latitude})", srid=4326),
                    "radius_meters": 50_000,
                    "urgent_radius_meters": None,
                    "travel_fee_policy": "QUOTE",
                })

    await _bulk_upsert(session, User, login_users + users, update_columns=("google_subject", "email", "name", "avatar_url", "phone", "is_demo", "status"))
    for offset in range(0, len(roles), 500):
        await session.execute(insert(UserRole).values(roles[offset:offset + 500]).on_conflict_do_nothing())
    await _bulk_upsert(session, Address, addresses, update_columns=("user_id", "label", "formatted_address", "street", "street_number", "unit", "city", "administrative_area", "province", "postal_code", "country_code", "google_place_id", "point", "is_default"))
    await _bulk_upsert(session, ProviderProfile, profiles, update_columns=("user_id", "display_name", "slug", "business_name", "bio", "experience_years", "base_address_id", "base_point", "profile_status", "subscription_visibility_status", "rating_average", "rating_count", "completed_services_count", "response_rate", "average_response_minutes", "profile_completeness", "is_identity_verified", "is_demo", "paused_at"))
    await _bulk_upsert(session, ProviderService, offers, update_columns=("provider_id", "service_id", "status", "headline", "description", "pricing_type", "price_amount", "price_currency", "estimated_duration_minutes", "guarantee_days", "accepts_urgent", "requires_quote_details"))
    for offset in range(0, len(modalities), 500):
        statement = insert(ProviderServiceModality).values(modalities[offset:offset + 500])
        await session.execute(statement.on_conflict_do_update(
            index_elements=[ProviderServiceModality.provider_service_id, ProviderServiceModality.modality],
            set_={"enabled": statement.excluded.enabled},
        ))
    await _bulk_upsert(session, ProviderServiceArea, areas, update_columns=("provider_service_id", "center_address_id", "center", "radius_meters", "urgent_radius_meters", "travel_fee_policy"))
    await session.commit()
    return await verify_demo_seed(session, len(services), config.providers_per_service)


async def verify_demo_seed(session: AsyncSession, service_count: int = 1392, expected_per_service: int = 3) -> DemoSeedSummary:
    provider_count = int(await session.scalar(select(func.count()).select_from(ProviderProfile).where(ProviderProfile.is_demo.is_(True))) or 0)
    grouped = (await session.execute(
        select(ProviderService.service_id, func.count(ProviderService.id))
        .join(ProviderProfile, ProviderProfile.id == ProviderService.provider_id)
        .where(ProviderProfile.is_demo.is_(True))
        .group_by(ProviderService.service_id)
    )).all()
    minimum = min((int(count) for _, count in grouped), default=0)
    login_count = int(await session.scalar(select(func.count()).select_from(User).where(User.id.in_([DEMO_ADMIN_ID, DEMO_CLIENT_ID, DEMO_PROVIDER_LOGIN_ID]), User.is_demo.is_(True))) or 0)
    expected = service_count * expected_per_service
    if provider_count != expected or len(grouped) != service_count or minimum != expected_per_service or login_count != 3:
        raise RuntimeError(f"Incomplete demo dataset: providers={provider_count}/{expected}, services={len(grouped)}/{service_count}, minimum={minimum}, logins={login_count}/3")
    return DemoSeedSummary(service_count, provider_count, minimum, login_count)


async def remove_demo_seed(session: AsyncSession) -> int:
    demo_user_ids = select(User.id).where(User.is_demo.is_(True))
    demo_provider_ids = select(ProviderProfile.id).where(ProviderProfile.is_demo.is_(True))
    demo_offer_ids = select(ProviderService.id).where(ProviderService.provider_id.in_(demo_provider_ids))
    demo_request_ids = select(ServiceRequest.id).where(or_(ServiceRequest.client_id.in_(demo_user_ids), ServiceRequest.provider_id.in_(demo_provider_ids), ServiceRequest.provider_service_id.in_(demo_offer_ids)))
    demo_booking_ids = select(Booking.id).where(or_(Booking.request_id.in_(demo_request_ids), Booking.client_id.in_(demo_user_ids), Booking.provider_id.in_(demo_provider_ids)))
    demo_review_ids = select(Review.id).where(or_(Review.booking_id.in_(demo_booking_ids), Review.client_id.in_(demo_user_ids), Review.provider_id.in_(demo_provider_ids)))
    demo_conversation_ids = select(Conversation.id).where(Conversation.request_id.in_(demo_request_ids))
    demo_document_ids = select(ProviderDocument.id).where(ProviderDocument.provider_id.in_(demo_provider_ids))

    await session.execute(delete(ReviewRevision).where(ReviewRevision.review_id.in_(demo_review_ids)))
    await session.execute(update(Review).where(Review.moderated_by.in_(demo_user_ids)).values(moderated_by=None))
    await session.execute(delete(Review).where(Review.id.in_(demo_review_ids)))
    await session.execute(delete(Message).where(or_(Message.conversation_id.in_(demo_conversation_ids), Message.sender_id.in_(demo_user_ids))))
    await session.execute(delete(Conversation).where(Conversation.id.in_(demo_conversation_ids)))
    await session.execute(delete(RequestAttachment).where(RequestAttachment.request_id.in_(demo_request_ids)))
    await session.execute(delete(Booking).where(Booking.id.in_(demo_booking_ids)))
    await session.execute(delete(Quote).where(or_(Quote.request_id.in_(demo_request_ids), Quote.provider_id.in_(demo_provider_ids))))
    await session.execute(delete(ServiceRequest).where(ServiceRequest.id.in_(demo_request_ids)))
    await session.execute(delete(DocumentReview).where(or_(DocumentReview.document_id.in_(demo_document_ids), DocumentReview.reviewer_user_id.in_(demo_user_ids))))
    await session.execute(update(ProviderDocument).where(ProviderDocument.reviewed_by.in_(demo_user_ids)).values(reviewed_by=None))
    await session.execute(delete(ProviderDocument).where(ProviderDocument.id.in_(demo_document_ids)))
    await session.execute(delete(ProviderSubscription).where(ProviderSubscription.provider_id.in_(demo_provider_ids)))
    await session.execute(delete(FavoriteProvider).where(or_(FavoriteProvider.client_id.in_(demo_user_ids), FavoriteProvider.provider_id.in_(demo_provider_ids))))
    await session.execute(delete(Notification).where(Notification.user_id.in_(demo_user_ids)))
    await session.execute(delete(ProviderServiceArea).where(ProviderServiceArea.provider_service_id.in_(demo_offer_ids)))
    await session.execute(delete(ProviderServiceModality).where(ProviderServiceModality.provider_service_id.in_(demo_offer_ids)))
    await session.execute(delete(ProviderService).where(ProviderService.id.in_(demo_offer_ids)))
    await session.execute(delete(ProviderPortfolioItem).where(ProviderPortfolioItem.provider_id.in_(demo_provider_ids)))
    await session.execute(delete(ProviderProfile).where(ProviderProfile.id.in_(demo_provider_ids)))
    await session.execute(delete(MediaFile).where(MediaFile.owner_user_id.in_(demo_user_ids)))
    await session.execute(delete(Address).where(Address.user_id.in_(demo_user_ids)))
    await session.execute(delete(UserRole).where(UserRole.user_id.in_(demo_user_ids)))
    result = await session.execute(delete(User).where(User.is_demo.is_(True)))
    await session.commit()
    return int(result.rowcount or 0)


async def run(path: Path, remove: bool) -> DemoSeedSummary | int:
    if get_settings().app_env.lower() == "production":
        raise RuntimeError("Demo data cannot be managed in production")
    config = DemoSeedConfig.model_validate(json.loads(path.read_text(encoding="utf-8")))
    async with SessionFactory() as session:
        try:
            return await remove_demo_seed(session) if remove else await apply_demo_seed(session, config)
        except Exception:
            await session.rollback()
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Load or remove the isolated SIC development demo dataset.")
    parser.add_argument("--file", type=Path, default=Path("seeds/demo-data.json"))
    parser.add_argument("--remove", action="store_true", help="Remove every record marked as demo, including demo interactions.")
    args = parser.parse_args()
    result = asyncio.run(run(args.file, args.remove))
    if isinstance(result, int):
        print(f"Demo dataset removed: {result} users")
    else:
        print(f"Demo dataset ready: {result.providers} providers, {result.minimum_providers_per_service} per each of {result.services} services, {result.demo_login_users} login users")


if __name__ == "__main__":
    main()
