from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sic_api.modules.addresses.models import Address
from sic_api.modules.catalog.models import Service
from sic_api.modules.media.models import MediaFile, MediaScanStatus
from sic_api.modules.provider_services.models import ProviderModality, ProviderService, ProviderServiceArea, ProviderServiceModality
from sic_api.modules.providers.models import ProviderProfile
from sic_api.modules.users.models import User, UserStatus

from .models import Booking, BookingStatus, Quote, QuoteStatus, RequestAttachment, ServiceRequest, ServiceRequestStatus
from .schemas import BookingSchedule, QuoteCreate, ServiceRequestCreate
from .state import InvalidTransitionError, request_transition


class EngagementNotFoundError(LookupError):
    pass


class EngagementConflictError(ValueError):
    pass


@dataclass(frozen=True)
class OfferRequestContext:
    offer: ProviderService
    provider: ProviderProfile
    user_status: UserStatus
    service_name: str
    modalities: frozenset[ProviderModality]
    has_service_area: bool


@dataclass(frozen=True)
class AttachmentRecord:
    attachment: RequestAttachment
    media: MediaFile


@dataclass(frozen=True)
class RequestRecord:
    request: ServiceRequest
    offer: ProviderService
    provider: ProviderProfile
    service_name: str
    client_name: str
    address_label: str | None
    attachments: tuple[AttachmentRecord, ...]
    quotes: tuple[Quote, ...]
    booking_id: UUID | None


@dataclass(frozen=True)
class BookingRecord:
    booking: Booking
    offer: ProviderService
    provider: ProviderProfile
    service_name: str
    client_name: str


class SqlAlchemyEngagementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def provider_id_for_user(self, user_id: UUID) -> UUID | None:
        return await self.session.scalar(select(ProviderProfile.id).where(ProviderProfile.user_id == user_id))

    async def offer_context(self, offer_id: UUID) -> OfferRequestContext | None:
        row = (await self.session.execute(
            select(ProviderService, ProviderProfile, User.status, Service.name)
            .join(ProviderProfile, ProviderProfile.id == ProviderService.provider_id)
            .join(User, User.id == ProviderProfile.user_id)
            .join(Service, Service.id == ProviderService.service_id)
            .where(ProviderService.id == offer_id)
        )).one_or_none()
        if row is None:
            return None
        modalities = frozenset((await self.session.scalars(
            select(ProviderServiceModality.modality).where(
                ProviderServiceModality.provider_service_id == offer_id,
                ProviderServiceModality.enabled.is_(True),
            )
        )).all())
        has_area = bool(await self.session.scalar(select(func.count(ProviderServiceArea.id)).where(ProviderServiceArea.provider_service_id == offer_id)))
        return OfferRequestContext(row[0], row[1], row[2], row[3], modalities, has_area)

    async def coverage_matches(self, offer_id: UUID, address_id: UUID, client_id: UUID) -> bool:
        return bool(await self.session.scalar(
            select(func.ST_DWithin(ProviderServiceArea.center, Address.point, ProviderServiceArea.radius_meters))
            .select_from(ProviderServiceArea)
            .join(Address, Address.id == address_id)
            .where(ProviderServiceArea.provider_service_id == offer_id, Address.user_id == client_id)
        ))

    async def create_request(self, client_id: UUID, provider_id: UUID, payload: ServiceRequestCreate) -> RequestRecord:
        item = ServiceRequest(
            client_id=client_id,
            provider_id=provider_id,
            provider_service_id=payload.provider_service_id,
            client_address_id=payload.client_address_id,
            selected_modality=payload.selected_modality,
            title=payload.title.strip(),
            description=payload.description.strip(),
            preferred_start_at=payload.preferred_start_at,
            status=ServiceRequestStatus.REQUESTED,
        )
        self.session.add(item)
        await self.session.commit()
        return await self.get_request(item.id, client_id)

    async def _request_rows(self, query) -> list[RequestRecord]:
        rows = (await self.session.execute(
            query.add_columns(ProviderService, ProviderProfile, Service.name, User.name, Address.label)
            .join(ProviderService, ProviderService.id == ServiceRequest.provider_service_id)
            .join(ProviderProfile, ProviderProfile.id == ServiceRequest.provider_id)
            .join(Service, Service.id == ProviderService.service_id)
            .join(User, User.id == ServiceRequest.client_id)
            .outerjoin(Address, Address.id == ServiceRequest.client_address_id)
        )).all()
        if not rows:
            return []
        request_ids = [row[0].id for row in rows]
        attachment_rows = (await self.session.execute(
            select(RequestAttachment, MediaFile)
            .join(MediaFile, MediaFile.id == RequestAttachment.media_file_id)
            .where(RequestAttachment.request_id.in_(request_ids), MediaFile.scan_status == MediaScanStatus.CLEAN)
            .order_by(RequestAttachment.created_at)
        )).all()
        attachments: dict[UUID, list[AttachmentRecord]] = {item_id: [] for item_id in request_ids}
        for attachment, media in attachment_rows:
            attachments[attachment.request_id].append(AttachmentRecord(attachment, media))
        quote_rows = (await self.session.scalars(select(Quote).where(Quote.request_id.in_(request_ids)).order_by(Quote.created_at.desc()))).all()
        quotes: dict[UUID, list[Quote]] = {item_id: [] for item_id in request_ids}
        for quote in quote_rows:
            quotes[quote.request_id].append(quote)
        booking_rows = (await self.session.execute(select(Booking.request_id, Booking.id).where(Booking.request_id.in_(request_ids)))).all()
        bookings = dict(booking_rows)
        return [RequestRecord(row[0], row[1], row[2], row[3], row[4], row[5], tuple(attachments[row[0].id]), tuple(quotes[row[0].id]), bookings.get(row[0].id)) for row in rows]

    async def get_request(self, request_id: UUID, actor_user_id: UUID, *, for_update: bool = False) -> RequestRecord:
        provider_id = await self.provider_id_for_user(actor_user_id)
        allowed = or_(ServiceRequest.client_id == actor_user_id, ServiceRequest.provider_id == provider_id) if provider_id else ServiceRequest.client_id == actor_user_id
        query = select(ServiceRequest).where(ServiceRequest.id == request_id, allowed)
        if for_update:
            query = query.with_for_update(of=ServiceRequest)
        records = await self._request_rows(query)
        if not records:
            raise EngagementNotFoundError
        return records[0]

    async def list_client_requests(self, client_id: UUID) -> list[RequestRecord]:
        return await self._request_rows(select(ServiceRequest).where(ServiceRequest.client_id == client_id).order_by(ServiceRequest.created_at.desc()).limit(100))

    async def list_provider_requests(self, provider_user_id: UUID) -> list[RequestRecord]:
        provider_id = await self.provider_id_for_user(provider_user_id)
        if provider_id is None:
            return []
        return await self._request_rows(select(ServiceRequest).where(ServiceRequest.provider_id == provider_id).order_by(ServiceRequest.created_at.desc()).limit(100))

    async def mark_viewed(self, request_id: UUID, provider_user_id: UUID) -> RequestRecord:
        provider_id = await self.provider_id_for_user(provider_user_id)
        item = await self.session.scalar(select(ServiceRequest).where(ServiceRequest.id == request_id, ServiceRequest.provider_id == provider_id).with_for_update())
        if item is None:
            raise EngagementNotFoundError
        if item.status == ServiceRequestStatus.REQUESTED:
            item.status = request_transition(item.status, "view")
            item.viewed_at = datetime.now(timezone.utc)
            await self.session.commit()
        return await self.get_request(request_id, provider_user_id)

    async def create_quote(self, request_id: UUID, provider_user_id: UUID, payload: QuoteCreate) -> RequestRecord:
        provider_id = await self.provider_id_for_user(provider_user_id)
        item = await self.session.scalar(select(ServiceRequest).where(ServiceRequest.id == request_id, ServiceRequest.provider_id == provider_id).with_for_update())
        if item is None or provider_id is None:
            raise EngagementNotFoundError
        item.status = request_transition(item.status, "quote")
        await self.session.execute(update(Quote).where(Quote.request_id == item.id, Quote.status == QuoteStatus.SENT).values(status=QuoteStatus.WITHDRAWN))
        self.session.add(Quote(request_id=item.id, provider_id=provider_id, amount=payload.amount, currency=payload.currency, description=payload.description.strip(), valid_until=payload.valid_until, status=QuoteStatus.SENT))
        await self.session.commit()
        return await self.get_request(request_id, provider_user_id)

    async def decline_request(self, request_id: UUID, provider_user_id: UUID) -> RequestRecord:
        provider_id = await self.provider_id_for_user(provider_user_id)
        item = await self.session.scalar(select(ServiceRequest).where(ServiceRequest.id == request_id, ServiceRequest.provider_id == provider_id).with_for_update())
        if item is None:
            raise EngagementNotFoundError
        item.status = request_transition(item.status, "decline")
        await self.session.execute(update(Quote).where(Quote.request_id == item.id, Quote.status == QuoteStatus.SENT).values(status=QuoteStatus.WITHDRAWN))
        await self.session.commit()
        return await self.get_request(request_id, provider_user_id)

    async def cancel_request(self, request_id: UUID, client_id: UUID) -> RequestRecord:
        item = await self.session.scalar(select(ServiceRequest).where(ServiceRequest.id == request_id, ServiceRequest.client_id == client_id).with_for_update())
        if item is None:
            raise EngagementNotFoundError
        item.status = request_transition(item.status, "cancel")
        await self.session.execute(update(Quote).where(Quote.request_id == item.id, Quote.status == QuoteStatus.SENT).values(status=QuoteStatus.WITHDRAWN))
        await self.session.commit()
        return await self.get_request(request_id, client_id)

    async def reject_quote(self, request_id: UUID, quote_id: UUID, client_id: UUID) -> RequestRecord:
        item = await self.session.scalar(select(ServiceRequest).where(ServiceRequest.id == request_id, ServiceRequest.client_id == client_id).with_for_update())
        quote = await self.session.scalar(select(Quote).where(Quote.id == quote_id, Quote.request_id == request_id).with_for_update())
        if item is None or quote is None:
            raise EngagementNotFoundError
        if quote.status != QuoteStatus.SENT or quote.valid_until <= datetime.now(timezone.utc):
            raise EngagementConflictError("This quote is no longer available")
        item.status = request_transition(item.status, "decline")
        quote.status = QuoteStatus.REJECTED
        await self.session.commit()
        return await self.get_request(request_id, client_id)

    async def convert_to_booking(
        self,
        *,
        request_id: UUID,
        actor_user_id: UUID,
        actor_kind: str,
        schedule: BookingSchedule,
        address_snapshot_encrypted: str | None,
        quote_id: UUID | None,
        fixed_price: Decimal | None,
        currency: str,
    ) -> BookingRecord:
        provider_id = await self.provider_id_for_user(actor_user_id) if actor_kind == "provider" else None
        actor_filter = ServiceRequest.provider_id == provider_id if actor_kind == "provider" else ServiceRequest.client_id == actor_user_id
        item = await self.session.scalar(select(ServiceRequest).where(ServiceRequest.id == request_id, actor_filter).with_for_update())
        if item is None:
            raise EngagementNotFoundError
        agreed_price = fixed_price
        if quote_id is not None:
            quote = await self.session.scalar(select(Quote).where(Quote.id == quote_id, Quote.request_id == item.id).with_for_update())
            if actor_kind != "client" or quote is None:
                raise EngagementNotFoundError
            if quote.status != QuoteStatus.SENT or quote.valid_until <= datetime.now(timezone.utc):
                if quote.status == QuoteStatus.SENT:
                    quote.status = QuoteStatus.EXPIRED
                await self.session.commit()
                raise EngagementConflictError("This quote is no longer available")
            agreed_price = quote.amount
            currency = quote.currency
            quote.status = QuoteStatus.ACCEPTED
            await self.session.execute(update(Quote).where(Quote.request_id == item.id, Quote.id != quote.id, Quote.status == QuoteStatus.SENT).values(status=QuoteStatus.WITHDRAWN))
        elif actor_kind != "provider" or fixed_price is None:
            raise EngagementConflictError("A direct acceptance requires the configured fixed price")
        item.status = request_transition(item.status, "accept")
        booking = Booking(
            request_id=item.id,
            client_id=item.client_id,
            provider_id=item.provider_id,
            provider_service_id=item.provider_service_id,
            modality=item.selected_modality,
            address_snapshot_encrypted=address_snapshot_encrypted,
            starts_at=schedule.starts_at,
            ends_at=schedule.ends_at,
            agreed_price=agreed_price,
            currency=currency,
            status=BookingStatus.PENDING_PROVIDER if actor_kind == "client" else BookingStatus.CONFIRMED,
        )
        self.session.add(booking)
        item.status = request_transition(item.status, "convert")
        try:
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise EngagementConflictError("The provider is not available for that schedule") from error
        return await self.get_booking(booking.id, actor_user_id)

    async def add_attachment(self, request_id: UUID, actor_user_id: UUID, media_id: UUID) -> RequestRecord:
        record = await self.get_request(request_id, actor_user_id, for_update=True)
        if record.request.client_id != actor_user_id:
            raise EngagementNotFoundError
        if record.request.status not in {ServiceRequestStatus.REQUESTED, ServiceRequestStatus.VIEWED, ServiceRequestStatus.QUOTED}:
            raise EngagementConflictError("Attachments cannot be added to this request")
        if len(record.attachments) >= 5:
            raise EngagementConflictError("A request can keep up to five attachments")
        self.session.add(RequestAttachment(request_id=request_id, media_file_id=media_id, uploaded_by_user_id=actor_user_id))
        await self.session.commit()
        return await self.get_request(request_id, actor_user_id)

    async def attachment(self, request_id: UUID, attachment_id: UUID, actor_user_id: UUID) -> AttachmentRecord:
        await self.get_request(request_id, actor_user_id)
        row = (await self.session.execute(
            select(RequestAttachment, MediaFile)
            .join(MediaFile, MediaFile.id == RequestAttachment.media_file_id)
            .where(RequestAttachment.id == attachment_id, RequestAttachment.request_id == request_id, MediaFile.scan_status == MediaScanStatus.CLEAN)
        )).one_or_none()
        if row is None:
            raise EngagementNotFoundError
        return AttachmentRecord(row[0], row[1])

    async def _booking_rows(self, query) -> list[BookingRecord]:
        rows = (await self.session.execute(
            query.add_columns(ProviderService, ProviderProfile, Service.name, User.name)
            .join(ProviderService, ProviderService.id == Booking.provider_service_id)
            .join(ProviderProfile, ProviderProfile.id == Booking.provider_id)
            .join(Service, Service.id == ProviderService.service_id)
            .join(User, User.id == Booking.client_id)
        )).all()
        return [BookingRecord(row[0], row[1], row[2], row[3], row[4]) for row in rows]

    async def get_booking(self, booking_id: UUID, actor_user_id: UUID, *, for_update: bool = False) -> BookingRecord:
        provider_id = await self.provider_id_for_user(actor_user_id)
        allowed = or_(Booking.client_id == actor_user_id, Booking.provider_id == provider_id) if provider_id else Booking.client_id == actor_user_id
        query = select(Booking).where(Booking.id == booking_id, allowed)
        if for_update:
            query = query.with_for_update(of=Booking)
        records = await self._booking_rows(query)
        if not records:
            raise EngagementNotFoundError
        return records[0]

    async def list_client_bookings(self, client_id: UUID) -> list[BookingRecord]:
        return await self._booking_rows(select(Booking).where(Booking.client_id == client_id).order_by(Booking.starts_at.desc()).limit(100))

    async def list_provider_bookings(self, provider_user_id: UUID) -> list[BookingRecord]:
        provider_id = await self.provider_id_for_user(provider_user_id)
        if provider_id is None:
            return []
        return await self._booking_rows(select(Booking).where(Booking.provider_id == provider_id).order_by(Booking.starts_at.desc()).limit(100))

    async def save_booking(self, booking: Booking) -> None:
        try:
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise EngagementConflictError("The booking state conflicts with another schedule") from error

    async def recompute_completed_services(self, provider_id: UUID) -> None:
        completed = int(await self.session.scalar(select(func.count(Booking.id)).where(Booking.provider_id == provider_id, Booking.completed_at.is_not(None))) or 0)
        profile = await self.session.get(ProviderProfile, provider_id)
        if profile:
            profile.completed_services_count = completed
            await self.session.commit()
