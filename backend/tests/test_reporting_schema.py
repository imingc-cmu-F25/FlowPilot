"""Round-trip tests for reporting domain model and ORM."""

import uuid
from datetime import UTC, datetime

from app.db.connector import get_engine
from app.db.schema import ReportORM
from app.reporting.report import AggregatedMetrics, MonthlyReport, ReportStatus
from app.user.repo import UserRepository
from sqlalchemy.orm import sessionmaker


def _make_session():
    maker = sessionmaker(
        bind=get_engine(),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    return maker()


def test_monthly_report_defaults():
    period_start = datetime(2026, 3, 1, tzinfo=UTC)
    period_end = datetime(2026, 3, 31, tzinfo=UTC)
    report = MonthlyReport(
        owner_name="alice",
        period_start=period_start,
        period_end=period_end,
    )
    assert report.status == ReportStatus.PENDING
    assert report.metrics.total_runs == 0
    assert report.metrics.runs_per_workflow == {}
    assert report.ai_summary == ""
    assert report.report_id is not None


def test_aggregated_metrics_fields():
    metrics = AggregatedMetrics(
        total_runs=10,
        success_count=8,
        failure_count=2,
        success_rate=0.8,
        avg_duration_seconds=1.5,
        runs_per_workflow={"wf-a": 6, "wf-b": 4},
        top_error_messages=["boom", "oops"],
    )
    dumped = metrics.model_dump()
    assert dumped["total_runs"] == 10
    assert dumped["runs_per_workflow"]["wf-a"] == 6


def test_report_orm_persists_and_loads():
    session = _make_session()
    try:
        UserRepository(session).create("report-owner", "x" * 60)
        session.commit()

        now = datetime.now(UTC)
        period_start = datetime(2026, 3, 1, tzinfo=UTC)
        period_end = datetime(2026, 3, 31, tzinfo=UTC)
        orm = ReportORM(
            id=uuid.uuid4(),
            owner_name="report-owner",
            period_start=period_start,
            period_end=period_end,
            status=ReportStatus.COMPLETED.value,
            metrics={"total_runs": 5, "success_count": 4},
            ai_summary="5 runs, mostly green.",
            created_at=now,
            updated_at=now,
        )
        session.add(orm)
        session.commit()

        session.expire_all()
        loaded = session.get(ReportORM, orm.id)
        assert loaded is not None
        assert loaded.owner_name == "report-owner"
        assert loaded.status == "completed"
        assert loaded.metrics["total_runs"] == 5
        assert loaded.ai_summary == "5 runs, mostly green."
    finally:
        session.close()
