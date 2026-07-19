from uuid import uuid4

import pytest
from pydantic import ValidationError

from sic_api.main import app
from sic_api.modules.messaging.schemas import MessageCreate
from sic_api.modules.messaging.service import MessagingService
from sic_api.modules.notifications.email import NotificationEmailDispatcher, SmtpConfiguration
from sic_api.modules.notifications.models import NotificationType
from sic_api.modules.notifications.service import NotificationService
from sic_api.modules.reviews.schemas import ReviewCreate, ReviewDecision


class RepositoryThatMustNotRun:
    async def create(self, **_kwargs):
        raise AssertionError("repository must not be called")

    async def pending_emails(self, _limit):
        raise AssertionError("SMTP-disabled dispatcher must not claim outbox rows")


@pytest.mark.anyio
async def test_blank_message_is_rejected_before_persistence() -> None:
    service = MessagingService(RepositoryThatMustNotRun())
    with pytest.raises(ValueError, match="blank"):
        await service.send(uuid4(), uuid4(), MessageCreate(body="   "))


def test_verified_review_contract_limits_rating_and_moderation() -> None:
    assert ReviewCreate(rating=5, comment="Trabajo excelente y puntual.").rating == 5
    with pytest.raises(ValidationError):
        ReviewCreate(rating=6, comment="Trabajo excelente y puntual.")
    with pytest.raises(ValidationError):
        ReviewCreate(rating=4, comment="Breve")
    with pytest.raises(ValidationError):
        ReviewDecision(action="reject", reason="mal")
    assert ReviewDecision(action="publish").reason is None


@pytest.mark.anyio
async def test_notification_rejects_external_or_protocol_relative_links() -> None:
    service = NotificationService(RepositoryThatMustNotRun())
    for unsafe in ("https://example.com", "//example.com"):
        with pytest.raises(ValueError, match="local"):
            await service.notify_user(uuid4(), type=NotificationType.MESSAGE_RECEIVED, title="Aviso", body="Mensaje", link_path=unsafe, resource_type=None, resource_id=None)


@pytest.mark.anyio
async def test_email_dispatcher_does_not_touch_outbox_without_smtp() -> None:
    dispatcher = NotificationEmailDispatcher(
        RepositoryThatMustNotRun(),
        SmtpConfiguration(host=None, port=1025, user=None, password=None, sender=None, use_tls=False, app_url="http://localhost:3000"),
    )
    assert await dispatcher.dispatch() == 0


def test_communication_routes_are_contextual_and_reviews_are_role_scoped() -> None:
    paths = app.openapi()["paths"]
    assert "/v1/me/conversations/{request_id}/messages" in paths
    assert "/v1/me/notifications/read-all" in paths
    assert "/v1/client/favorites/{provider_slug}" in paths
    assert "/v1/client/reviews/bookings/{booking_id}" in paths
    assert "/v1/admin/reviews/{review_id}/moderate" in paths
    assert "/v1/providers/{provider_slug}/reviews" in paths
    assert not any(path in paths for path in ("/v1/messages", "/v1/conversations", "/v1/reviews"))
