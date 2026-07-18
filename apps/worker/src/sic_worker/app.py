import os

from celery import Celery

celery_app = Celery("sic-worker", broker=os.getenv("REDIS_URL", "redis://redis:6379/0"))


@celery_app.task(name="sic.diagnostic")
def diagnostic() -> dict[str, str]:
    return {"status": "ok", "worker": "sic-worker"}
