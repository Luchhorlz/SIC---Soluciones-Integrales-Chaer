from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sic_api.modules.addresses.repository import AddressNotFoundError, AddressRepository
from sic_api.modules.documents.repository import RequirementReadiness
from sic_api.modules.documents.service import DocumentReadinessReader
from sic_api.modules.media.models import MediaFile, MediaScanStatus
from sic_api.modules.media.repository import DuplicateMediaError, MediaRepository
from sic_api.modules.media.storage import AntivirusScanner, MalwareDetectedError, PrivateStorage, StorageUnavailableError, validate_private_document
from sic_api.modules.provider_services.models import PricingType, ProviderModality
from sic_api.modules.providers.models import SubscriptionVisibilityStatus
from sic_api.modules.providers.visibility import ProviderVisibilityContext, ProviderVisibilityService
from sic_api.modules.users.models import UserStatus

from .crypto import AddressCipher, AddressEncryptionConfigurationError
from .models import BookingStatus, QuoteStatus, ServiceRequestStatus
from .repository import BookingRecord, EngagementConflictError, EngagementNotFoundError, RequestRecord, SqlAlchemyEngagementRepository
from .schemas import AttachmentDownloadView, BookingDispute, BookingSchedule, BookingView, QuoteCreate, QuoteDecision, QuoteView, RequestAttachmentView, ServiceRequestCreate, ServiceRequestView
from .state import booking_transition


class SubscriptionVisibilityReader:
    async def status(self, provider_id: UUID) -> SubscriptionVisibilityStatus: ...


@dataclass(frozen=True)
class AttachmentInfrastructure:
    storage: PrivateStorage
    scanner: AntivirusScanner
    private_bucket: str
    max_bytes: int
    download_ttl_seconds: int


class EngagementService:
    coverage_modalities = ProviderVisibilityService.coverage_modalities

    def __init__(
        self,
        repository: SqlAlchemyEngagementRepository,
        addresses: AddressRepository,
        documents: DocumentReadinessReader,
        subscriptions: SubscriptionVisibilityReader,
        cipher: AddressCipher | None = None,
        media: MediaRepository | None = None,
        attachments: AttachmentInfrastructure | None = None,
    ) -> None:
        self.repository = repository
        self.addresses = addresses
        self.documents = documents
        self.subscriptions = subscriptions
        self.cipher = cipher
        self.media = media
        self.attachments = attachments
        self.visibility = ProviderVisibilityService()

    @staticmethod
    def _attachment_view(record) -> RequestAttachmentView:
        return RequestAttachmentView(id=record.attachment.id, filename=record.media.original_filename, mime_type=record.media.mime_type, byte_size=record.media.byte_size, created_at=record.attachment.created_at)

    @staticmethod
    def _quote_view(item) -> QuoteView:
        status = QuoteStatus.EXPIRED if item.status == QuoteStatus.SENT and item.valid_until <= datetime.now(timezone.utc) else item.status
        return QuoteView(id=item.id, amount=item.amount, currency=item.currency, description=item.description, valid_until=item.valid_until, status=status, created_at=item.created_at)

    @classmethod
    def _request_view(cls, record: RequestRecord) -> ServiceRequestView:
        item = record.request
        return ServiceRequestView(
            id=item.id,
            client_id=item.client_id,
            provider_id=item.provider_id,
            provider_service_id=item.provider_service_id,
            service_name=record.service_name,
            offer_headline=record.offer.headline,
            pricing_type=record.offer.pricing_type,
            configured_price=record.offer.price_amount,
            price_currency=record.offer.price_currency,
            client_name=record.client_name,
            provider_name=record.provider.display_name,
            selected_modality=item.selected_modality,
            client_address_label=record.address_label,
            title=item.title,
            description=item.description,
            preferred_start_at=item.preferred_start_at,
            status=item.status,
            viewed_at=item.viewed_at,
            created_at=item.created_at,
            attachments=[cls._attachment_view(entry) for entry in record.attachments],
            quotes=[cls._quote_view(quote) for quote in record.quotes],
            booking_id=record.booking_id,
        )

    def _booking_view(self, record: BookingRecord) -> BookingView:
        item = record.booking
        address = self.cipher.decrypt(item.address_snapshot_encrypted) if item.address_snapshot_encrypted and self.cipher else None
        if item.address_snapshot_encrypted and self.cipher is None:
            raise AddressEncryptionConfigurationError("Booking address encryption is not configured")
        return BookingView(
            id=item.id,
            request_id=item.request_id,
            client_id=item.client_id,
            provider_id=item.provider_id,
            provider_service_id=item.provider_service_id,
            service_name=record.service_name,
            offer_headline=record.offer.headline,
            client_name=record.client_name,
            provider_name=record.provider.display_name,
            modality=item.modality,
            address=address,
            starts_at=item.starts_at,
            ends_at=item.ends_at,
            agreed_price=item.agreed_price,
            currency=item.currency,
            status=item.status,
            completed_at=item.completed_at,
            client_confirmed_at=item.client_confirmed_at,
            cancelled_at=item.cancelled_at,
            dispute_reason=item.dispute_reason,
            created_at=item.created_at,
        )

    async def create_request(self, client_id: UUID, payload: ServiceRequestCreate) -> ServiceRequestView:
        context = await self.repository.offer_context(payload.provider_service_id)
        if context is None:
            raise EngagementNotFoundError
        if context.provider.user_id == client_id:
            raise EngagementConflictError("A provider cannot request their own service")
        readiness: RequirementReadiness = await self.documents.readiness(context.provider.id, context.offer.service_id)
        subscription = await self.subscriptions.status(context.provider.id)
        visible = self.visibility.evaluate(ProviderVisibilityContext(
            user_active=context.user_status == UserStatus.ACTIVE,
            profile_status=context.provider.profile_status,
            profile_paused=context.provider.paused_at is not None,
            subscription_status=subscription,
            service_status=context.offer.status,
            modalities=context.modalities,
            has_service_area=context.has_service_area,
            documents_ready=readiness.ready,
            documents_expired=readiness.expired,
        ))
        if not visible.visible:
            raise EngagementNotFoundError
        if payload.selected_modality not in context.modalities:
            raise EngagementConflictError("The selected modality is not enabled for this service")
        if payload.selected_modality in self.coverage_modalities:
            if payload.client_address_id is None:
                raise EngagementConflictError("This modality requires one of the client's private addresses")
            try:
                await self.addresses.get(client_id, payload.client_address_id)
            except AddressNotFoundError as error:
                raise EngagementNotFoundError from error
            if not await self.repository.coverage_matches(context.offer.id, payload.client_address_id, client_id):
                raise EngagementConflictError("The selected address is outside this service's coverage")
        elif payload.client_address_id is not None:
            raise EngagementConflictError("Remote and provider-location requests do not send a client address")
        return self._request_view(await self.repository.create_request(client_id, context.provider.id, payload))

    async def get_request(self, actor_user_id: UUID, request_id: UUID) -> ServiceRequestView:
        return self._request_view(await self.repository.get_request(request_id, actor_user_id))

    async def list_client_requests(self, client_id: UUID) -> list[ServiceRequestView]:
        return [self._request_view(item) for item in await self.repository.list_client_requests(client_id)]

    async def list_provider_requests(self, provider_user_id: UUID) -> list[ServiceRequestView]:
        return [self._request_view(item) for item in await self.repository.list_provider_requests(provider_user_id)]

    async def view_request(self, provider_user_id: UUID, request_id: UUID) -> ServiceRequestView:
        return self._request_view(await self.repository.mark_viewed(request_id, provider_user_id))

    async def quote_request(self, provider_user_id: UUID, request_id: UUID, payload: QuoteCreate) -> ServiceRequestView:
        record = await self.repository.get_request(request_id, provider_user_id)
        if record.provider.user_id != provider_user_id:
            raise EngagementNotFoundError
        if record.offer.pricing_type == PricingType.FIXED:
            raise EngagementConflictError("This fixed-price offer uses its configured direct price and cannot be quoted")
        return self._request_view(await self.repository.create_quote(request_id, provider_user_id, payload))

    async def decline_request(self, provider_user_id: UUID, request_id: UUID) -> ServiceRequestView:
        return self._request_view(await self.repository.decline_request(request_id, provider_user_id))

    async def cancel_request(self, client_id: UUID, request_id: UUID) -> ServiceRequestView:
        return self._request_view(await self.repository.cancel_request(request_id, client_id))

    async def reject_quote(self, client_id: UUID, request_id: UUID, quote_id: UUID) -> ServiceRequestView:
        return self._request_view(await self.repository.reject_quote(request_id, quote_id, client_id))

    @staticmethod
    def _schedule(record: RequestRecord, supplied: BookingSchedule | None) -> BookingSchedule:
        if supplied:
            return supplied
        if record.request.preferred_start_at and record.offer.estimated_duration_minutes:
            return BookingSchedule(starts_at=record.request.preferred_start_at, ends_at=record.request.preferred_start_at + timedelta(minutes=record.offer.estimated_duration_minutes))
        raise EngagementConflictError("A confirmed start and end time are required")

    async def _snapshot(self, record: RequestRecord) -> str | None:
        if record.request.client_address_id is None:
            return None
        if self.cipher is None:
            raise AddressEncryptionConfigurationError("Booking address encryption is not configured")
        address = await self.addresses.get(record.request.client_id, record.request.client_address_id)
        if not await self.repository.coverage_matches(record.offer.id, address.id, record.request.client_id):
            raise EngagementConflictError("The request address is no longer inside this service's coverage")
        return self.cipher.encrypt(address)

    async def accept_quote(self, client_id: UUID, request_id: UUID, decision: QuoteDecision) -> BookingView:
        record = await self.repository.get_request(request_id, client_id)
        schedule = self._schedule(record, decision.schedule)
        booking = await self.repository.convert_to_booking(
            request_id=request_id,
            actor_user_id=client_id,
            actor_kind="client",
            schedule=schedule,
            address_snapshot_encrypted=await self._snapshot(record),
            quote_id=decision.quote_id,
            fixed_price=None,
            currency="ARS",
        )
        return self._booking_view(booking)

    async def accept_fixed_request(self, provider_user_id: UUID, request_id: UUID, schedule: BookingSchedule | None) -> BookingView:
        record = await self.repository.get_request(request_id, provider_user_id)
        if record.provider.user_id != provider_user_id:
            raise EngagementNotFoundError
        if record.offer.pricing_type != PricingType.FIXED or record.offer.price_amount is None:
            raise EngagementConflictError("Only a fixed-price offer can be accepted without a quote")
        booking = await self.repository.convert_to_booking(
            request_id=request_id,
            actor_user_id=provider_user_id,
            actor_kind="provider",
            schedule=self._schedule(record, schedule),
            address_snapshot_encrypted=await self._snapshot(record),
            quote_id=None,
            fixed_price=record.offer.price_amount,
            currency=record.offer.price_currency,
        )
        return self._booking_view(booking)

    async def list_client_bookings(self, client_id: UUID) -> list[BookingView]:
        return [self._booking_view(item) for item in await self.repository.list_client_bookings(client_id)]

    async def list_provider_bookings(self, provider_user_id: UUID) -> list[BookingView]:
        return [self._booking_view(item) for item in await self.repository.list_provider_bookings(provider_user_id)]

    async def get_booking(self, actor_user_id: UUID, booking_id: UUID) -> BookingView:
        return self._booking_view(await self.repository.get_booking(booking_id, actor_user_id))

    async def booking_action(self, actor_user_id: UUID, booking_id: UUID, action: str, dispute: BookingDispute | None = None) -> BookingView:
        record = await self.repository.get_booking(booking_id, actor_user_id, for_update=True)
        item = record.booking
        provider_id = await self.repository.provider_id_for_user(actor_user_id)
        actor = "client" if item.client_id == actor_user_id else "provider" if item.provider_id == provider_id else "none"
        if actor == "none":
            raise EngagementNotFoundError
        if action == "no_show" and datetime.now(timezone.utc) < item.starts_at:
            raise EngagementConflictError("A no-show cannot be recorded before the scheduled start")
        item.status = booking_transition(item.status, action, actor=actor, client_confirmed=item.client_confirmed_at is not None)
        now = datetime.now(timezone.utc)
        if action == "complete":
            item.completed_at = now
        elif action == "confirm" and actor == "client":
            item.client_confirmed_at = now
        elif action == "dispute":
            if dispute is None:
                raise EngagementConflictError("A dispute reason is required")
            item.dispute_reason = dispute.reason.strip()
        elif action == "cancel":
            item.cancelled_at = now
        await self.repository.save_booking(item)
        if action == "complete":
            await self.repository.recompute_completed_services(item.provider_id)
        return self._booking_view(await self.repository.get_booking(booking_id, actor_user_id))

    async def upload_attachment(self, client_id: UUID, request_id: UUID, content: bytes, filename: str, declared_mime: str | None) -> ServiceRequestView:
        if self.media is None or self.attachments is None:
            raise StorageUnavailableError("Private request attachments are not configured")
        record = await self.repository.get_request(request_id, client_id)
        if record.request.client_id != client_id:
            raise EngagementNotFoundError
        validated = validate_private_document(content, filename, declared_mime, self.attachments.max_bytes)
        if await self.media.find_duplicate(client_id, validated.sha256):
            raise DuplicateMediaError("This exact file was already uploaded")
        media_id = uuid4()
        key = f"request-attachments/{client_id}/{request_id}/{media_id}{validated.extension}"
        await self.attachments.storage.put(key, validated.content, validated.mime_type)
        media = await self.media.create(MediaFile(id=media_id, owner_user_id=client_id, storage_bucket=self.attachments.private_bucket, object_key=key, original_filename=validated.original_filename, mime_type=validated.mime_type, byte_size=len(validated.content), sha256=validated.sha256, scan_status=MediaScanStatus.PENDING))
        try:
            message = await self.attachments.scanner.scan(validated.content)
        except MalwareDetectedError:
            await self.media.set_scan_status(media.id, MediaScanStatus.INFECTED, "Malware detected")
            await self.attachments.storage.delete(key)
            raise
        except StorageUnavailableError:
            await self.media.set_scan_status(media.id, MediaScanStatus.ERROR, "Scanner unavailable")
            raise
        await self.media.set_scan_status(media.id, MediaScanStatus.CLEAN, message)
        return self._request_view(await self.repository.add_attachment(request_id, client_id, media.id))

    async def attachment_download(self, actor_user_id: UUID, request_id: UUID, attachment_id: UUID) -> AttachmentDownloadView:
        if self.attachments is None:
            raise StorageUnavailableError("Private request attachments are not configured")
        record = await self.repository.attachment(request_id, attachment_id, actor_user_id)
        url = await self.attachments.storage.presigned_download(record.media.object_key, record.media.original_filename, self.attachments.download_ttl_seconds)
        return AttachmentDownloadView(url=url, expires_in_seconds=self.attachments.download_ttl_seconds)
