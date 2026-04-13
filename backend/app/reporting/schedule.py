"""Celery beat schedule entries for the reporting module.

Exposes BEAT_SCHEDULE so app.worker can wire it onto celery_app.conf without
importing tasks directly (kept separate so tests can assert the schedule in
isolation).
"""

from __future__ import annotations

from celery.schedules import crontab

from app.reporting.tasks import TASK_DISPATCH_MONTHLY_REPORTS

BEAT_SCHEDULE: dict = {
    "reporting-dispatch-monthly-reports": {
        "task": TASK_DISPATCH_MONTHLY_REPORTS,
        # Fire at 02:00 UTC on the 1st of every month.
        "schedule": crontab(day_of_month="1", hour="2", minute="0"),
    },
}
