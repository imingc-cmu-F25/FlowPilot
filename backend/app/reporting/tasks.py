"""Celery tasks for the reporting pipeline.

Two tasks:
    reporting.dispatch_monthly_reports — beat-triggered fan-out task that
        enqueues one generate_monthly_report sub-task per user for the
        previous calendar month.
    reporting.generate_monthly_report — per-user worker task that runs the
        full pipeline in-process inside a single task.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from celery import shared_task
from sqlalchemy.orm import Session

from app.db.session import new_session
from app.reporting.service import make_reporting_service
from app.user.repo import UserRepository

TASK_GENERATE_MONTHLY_REPORT = "reporting.generate_monthly_report"
TASK_DISPATCH_MONTHLY_REPORTS = "reporting.dispatch_monthly_reports"


def _previous_month_bounds(now: datetime) -> tuple[datetime, datetime]:
    """Return (start, end) datetimes covering the previous calendar month in UTC."""
    first_of_this_month = now.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=UTC
    )
    last_of_prev_month = first_of_this_month - timedelta(microseconds=1)
    first_of_prev_month = last_of_prev_month.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    return first_of_prev_month, last_of_prev_month


@shared_task(name=TASK_GENERATE_MONTHLY_REPORT)
def generate_monthly_report(
    owner_name: str,
    period_start_iso: str,
    period_end_iso: str,
) -> str:
    """Run the reporting pipeline for a single user and period."""
    period_start = datetime.fromisoformat(period_start_iso)
    period_end = datetime.fromisoformat(period_end_iso)
    session: Session = new_session()
    try:
        service = make_reporting_service(session)
        report = service.generate_monthly_report(
            owner_name=owner_name,
            period_start=period_start,
            period_end=period_end,
        )
        session.commit()
        return str(report.report_id)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@shared_task(name=TASK_DISPATCH_MONTHLY_REPORTS)
def dispatch_monthly_reports() -> int:
    """Fan out a generate_monthly_report task per user for the previous month."""
    period_start, period_end = _previous_month_bounds(datetime.now(UTC))
    session: Session = new_session()
    try:
        users = UserRepository(session).get_all_users()
        for user in users:
            generate_monthly_report.delay(
                user.name,
                period_start.isoformat(),
                period_end.isoformat(),
            )
        return len(users)
    finally:
        session.close()
