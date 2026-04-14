"""Assertion-only tests for the reporting Celery schedule.

These tests do not start a beat process — they verify the schedule dict is
wired correctly and that the task names match the ones registered on the
Celery app.
"""

from datetime import UTC, datetime

from app.reporting.schedule import BEAT_SCHEDULE
from app.reporting.tasks import (
    TASK_DISPATCH_MONTHLY_REPORTS,
    TASK_GENERATE_MONTHLY_REPORT,
    _previous_month_bounds,
)
from app.worker import celery_app


def test_beat_schedule_contains_dispatch_entry():
    assert "reporting-dispatch-monthly-reports" in BEAT_SCHEDULE
    entry = BEAT_SCHEDULE["reporting-dispatch-monthly-reports"]
    assert entry["task"] == TASK_DISPATCH_MONTHLY_REPORTS


def test_dispatch_task_discoverable_on_celery_app():
    assert TASK_DISPATCH_MONTHLY_REPORTS in celery_app.tasks
    assert TASK_GENERATE_MONTHLY_REPORT in celery_app.tasks


def test_celery_app_has_beat_schedule_configured():
    assert "reporting-dispatch-monthly-reports" in celery_app.conf.beat_schedule


def test_previous_month_bounds_mid_month():
    now = datetime(2026, 3, 15, 12, 0, 0, tzinfo=UTC)
    start, end = _previous_month_bounds(now)
    assert start == datetime(2026, 2, 1, 0, 0, 0, tzinfo=UTC)
    assert start < end < datetime(2026, 3, 1, tzinfo=UTC)
    assert end.month == 2


def test_previous_month_bounds_january_rolls_back_year():
    now = datetime(2026, 1, 5, 9, 0, 0, tzinfo=UTC)
    start, end = _previous_month_bounds(now)
    assert start == datetime(2025, 12, 1, 0, 0, 0, tzinfo=UTC)
    assert end.year == 2025
    assert end.month == 12
