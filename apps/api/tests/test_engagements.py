import base64
from uuid import uuid4

import pytest
from fastapi import HTTPException

from sic_api.main import app
from sic_api.modules.addresses.schemas import AddressView
from sic_api.modules.engagements.crypto import AesGcmAddressCipher, AddressEncryptionConfigurationError
from sic_api.modules.engagements.models import BookingStatus, ServiceRequestStatus
from sic_api.modules.engagements.state import InvalidTransitionError, booking_transition, request_transition
from sic_api.modules.identity.permissions import Principal, get_client_principal


def test_private_address_snapshot_round_trip_excludes_location_identifiers() -> None:
    cipher = AesGcmAddressCipher(base64.urlsafe_b64encode(b"phase-nine-test-key-material-0000"[:32]).decode())
    address = AddressView(
        id=uuid4(), label="Casa", formatted_address="Av. Siempre Viva 742", street="Av. Siempre Viva",
        street_number="742", unit="2 B", city="Buenos Aires", administrative_area="Comuna 1",
        province="Buenos Aires", postal_code="1000", country_code="AR", google_place_id="private-place-id",
        latitude=-34.6037, longitude=-58.3816, is_default=True,
    )
    encrypted = cipher.encrypt(address)
    assert "Siempre Viva" not in encrypted
    restored = cipher.decrypt(encrypted)
    assert restored.formatted_address == address.formatted_address
    assert "google_place_id" not in restored.model_dump()
    assert "latitude" not in restored.model_dump()


def test_private_address_snapshot_detects_tampering() -> None:
    cipher = AesGcmAddressCipher(base64.urlsafe_b64encode(b"phase-nine-test-key-material-0000"[:32]).decode())
    with pytest.raises(AddressEncryptionConfigurationError):
        cipher.decrypt(base64.urlsafe_b64encode(b"tampered-payload").decode())


def test_request_and_booking_state_machines_reject_invalid_transitions() -> None:
    assert request_transition(ServiceRequestStatus.REQUESTED, "view") == ServiceRequestStatus.VIEWED
    assert request_transition(ServiceRequestStatus.VIEWED, "quote") == ServiceRequestStatus.QUOTED
    with pytest.raises(InvalidTransitionError):
        request_transition(ServiceRequestStatus.CANCELLED, "quote")
    assert booking_transition(BookingStatus.CONFIRMED, "start", actor="provider") == BookingStatus.IN_PROGRESS
    assert booking_transition(BookingStatus.PENDING_PROVIDER, "confirm", actor="provider") == BookingStatus.CONFIRMED
    assert booking_transition(BookingStatus.IN_PROGRESS, "complete", actor="provider") == BookingStatus.COMPLETED
    with pytest.raises(InvalidTransitionError):
        booking_transition(BookingStatus.CONFIRMED, "start", actor="client")


@pytest.mark.anyio
async def test_client_permission_is_role_scoped() -> None:
    user_id = uuid4()
    allowed = await get_client_principal(Principal(user_id, frozenset({"CLIENT"}), "session"))
    assert allowed.user_id == user_id
    with pytest.raises(HTTPException) as error:
        await get_client_principal(Principal(user_id, frozenset({"PROVIDER"}), "session"))
    assert error.value.status_code == 403


def test_engagement_routes_have_no_public_write_endpoint() -> None:
    paths = app.openapi()["paths"]
    engagement_paths = {path for path in paths if "service-requests" in path or "/bookings" in path}
    assert engagement_paths
    assert all(path.startswith("/v1/client/") or path.startswith("/v1/provider/") for path in engagement_paths)
    assert "/v1/service-requests" not in paths
