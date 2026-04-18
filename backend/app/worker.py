import os

from celery import Celery

from app.core.config import settings
from app.reporting.schedule import BEAT_SCHEDULE

celery_app = Celery(
    "flowpilot",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.autodiscover_tasks(["app.execution", "app.reporting", "app.trigger"])
celery_app.conf.beat_schedule = BEAT_SCHEDULE
celery_app.conf.beat_schedule["trigger-dispatch-time-triggers"] = {
    "task": "trigger.dispatch_time_triggers",
    "schedule": 60.0,  # every minute
}

# Test and local-sync fallback: run tasks inline instead of pushing to Redis.
# Controlled via env so CI and unit tests don't need a broker.
if os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() in {"1", "true", "yes"}:
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
