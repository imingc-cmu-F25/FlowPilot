from celery import Celery

from app.core.config import settings
from app.reporting.schedule import BEAT_SCHEDULE

celery_app = Celery(
    "flowpilot",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.autodiscover_tasks(["app.execution", "app.reporting"])
celery_app.conf.beat_schedule = BEAT_SCHEDULE
