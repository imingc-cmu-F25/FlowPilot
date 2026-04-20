import os

from celery import Celery

from app.action.tasks import ACTION_QUEUE_NAME, CELERY_TASK_EXECUTE_ACTION_STEP
from app.core.config import settings
from app.reporting.schedule import BEAT_SCHEDULE

celery_app = Celery(
    "flowpilot",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.autodiscover_tasks(
    ["app.execution", "app.reporting", "app.trigger", "app.action", "app.connectors"],
)
celery_app.conf.beat_schedule = BEAT_SCHEDULE
celery_app.conf.beat_schedule["trigger-dispatch-time-triggers"] = {
    "task": "trigger.dispatch_time_triggers",
    "schedule": 60.0,  # every minute
}
celery_app.conf.beat_schedule["trigger-dispatch-custom-triggers"] = {
    "task": "trigger.dispatch_custom_triggers",
    "schedule": 60.0,  # every minute
}
celery_app.conf.beat_schedule["execution-reap-stale-runs"] = {
    "task": "execution.reap_stale_runs",
    "schedule": 120.0,  # every 2 minutes
}
celery_app.conf.beat_schedule["connectors-sync-google-calendars"] = {
    "task": "connectors.sync_google_calendars",
    "schedule": 600.0,  # every 10 minutes
}
celery_app.conf.beat_schedule["trigger-dispatch-calendar-event-triggers"] = {
    "task": "trigger.dispatch_calendar_event_triggers",
    "schedule": 60.0,  # every minute
}

# Route the per-step action task to the dedicated "actions" queue. The
# default "celery" queue keeps workflow / reporting / trigger tasks; the
# separate action queue is what gives us the process-level fault isolation
# the Architecture Haiku calls for.
celery_app.conf.task_routes = {
    CELERY_TASK_EXECUTE_ACTION_STEP: {"queue": ACTION_QUEUE_NAME},
}
# Explicit default queue — keeps the engine worker from accidentally pulling
# action-queue tasks when both workers run on the same broker.
celery_app.conf.task_default_queue = "celery"

# Test and local-sync fallback: run tasks inline instead of pushing to Redis.
# Controlled via env so CI and unit tests don't need a broker.
if os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() in {"1", "true", "yes"}:
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
