import os
import asyncio

from celery import Celery

celery_app = Celery("sic-worker", broker=os.getenv("REDIS_URL", "redis://redis:6379/0"))
celery_app.conf.beat_schedule = {
    "expire-professional-documents-hourly": {
        "task": "sic.documents.expire",
        "schedule": 3600.0,
    },
    "send-transactional-notifications-every-minute": {
        "task": "sic.notifications.email",
        "schedule": 60.0,
    },
}


@celery_app.task(name="sic.diagnostic")
def diagnostic() -> dict[str, str]:
    return {"status": "ok", "worker": "sic-worker"}


async def _expire_documents() -> int:
    from sic_api.db.session import SessionFactory, engine
    from sic_api.modules.documents.repository import SqlAlchemyDocumentRepository
    from sic_api.modules.provider_services.repository import SqlAlchemyProviderServiceRepository

    try:
        async with SessionFactory() as session:
            documents = SqlAlchemyDocumentRepository(session)
            services = SqlAlchemyProviderServiceRepository(session)
            provider_ids = await documents.expire_approved()
            for provider_id in set(provider_ids):
                for configuration in await services.list(provider_id):
                    readiness = await documents.readiness(provider_id, configuration.service.service_id)
                    await services.set_document_readiness(provider_id, configuration.service.id, readiness.ready)
            return len(provider_ids)
    finally:
        await engine.dispose()


@celery_app.task(name="sic.documents.expire")
def expire_documents() -> dict[str, int]:
    return {"expired_documents": asyncio.run(_expire_documents())}


async def _send_notification_emails() -> int:
    from sic_api.db.session import SessionFactory, engine
    from sic_api.modules.notifications.email import NotificationEmailDispatcher, SmtpConfiguration
    from sic_api.modules.notifications.repository import SqlAlchemyNotificationRepository

    try:
        async with SessionFactory() as session:
            dispatcher = NotificationEmailDispatcher(
                SqlAlchemyNotificationRepository(session),
                SmtpConfiguration(
                    host=os.getenv("SMTP_HOST") or None,
                    port=int(os.getenv("SMTP_PORT", "1025")),
                    user=os.getenv("SMTP_USER") or None,
                    password=os.getenv("SMTP_PASSWORD") or None,
                    sender=os.getenv("EMAIL_FROM") or None,
                    use_tls=os.getenv("SMTP_USE_TLS", "false").lower() == "true",
                    app_url=os.getenv("APP_URL", "http://localhost:3000"),
                ),
            )
            return await dispatcher.dispatch()
    finally:
        await engine.dispose()


@celery_app.task(name="sic.notifications.email")
def send_notification_emails() -> dict[str, int]:
    return {"emails_sent": asyncio.run(_send_notification_emails())}
