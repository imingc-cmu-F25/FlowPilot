"""End-to-end test for ReportingService — seeds data, runs the pipeline,
asserts a report row was persisted with the expected metrics + summary."""

from datetime import UTC, datetime, timedelta

import pytest
from app.db.connector import get_engine
from app.reporting.repo import ReportRepository
from app.reporting.report import ReportStatus
from app.reporting.service import make_reporting_service
from app.user.repo import UserRepository
from app.workflow.repo import WorkflowRepository
from app.workflow.run import RunStatus, WorkflowRun
from app.workflow.run_repo import WorkflowRunRepository
from app.workflow.service import CreateWorkflowCommand, WorkflowService
from app.workflow.workflow import WorkflowDefinitionBuilder, WorkflowStatus
from app.trigger.service import TriggerService
from sqlalchemy.orm import sessionmaker
from tests.test_workflow_service import EMAIL_STEP, TIME_SPEC

PERIOD_START = datetime(2026, 3, 1, tzinfo=UTC)
PERIOD_END = datetime(2026, 3, 31, 23, 59, 59, tzinfo=UTC)


@pytest.fixture
def db_session():
    maker = sessionmaker(
        bind=get_engine(),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    session = maker()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _seed_workflow(session, owner: str = "report-owner"):
    UserRepository(session).create(owner, "x" * 60)
    cmd = CreateWorkflowCommand(
        owner_name=owner,
        name="Report WF",
        trigger=TIME_SPEC,
        steps=[EMAIL_STEP],
        enabled=True,
    )
    wf = WorkflowService(WorkflowDefinitionBuilder(), TriggerService()).create_workflow(cmd)
    wf = wf.model_copy(update={"status": WorkflowStatus.ACTIVE, "enabled": True})
    saved = WorkflowRepository(session).save(wf)
    session.commit()
    return saved


def _seed_runs(session, workflow_id, statuses: list[RunStatus]):
    repo = WorkflowRunRepository(session)
    base = PERIOD_START + timedelta(days=1)
    for i, status in enumerate(statuses):
        started = base + timedelta(hours=i)
        finished = started + timedelta(seconds=3)
        run = WorkflowRun(
            workflow_id=workflow_id,
            trigger_type="time",
            triggered_at=started,
            started_at=started,
            finished_at=finished,
            status=status,
            error="boom" if status == RunStatus.FAILED else None,
        )
        repo.create(run)
    session.commit()


def test_generate_monthly_report_persists_row(db_session):
    wf = _seed_workflow(db_session)
    _seed_runs(db_session, wf.workflow_id, [
        RunStatus.SUCCESS, RunStatus.SUCCESS, RunStatus.SUCCESS, RunStatus.FAILED,
    ])

    service = make_reporting_service(db_session)
    report = service.generate_monthly_report(
        owner_name="report-owner",
        period_start=PERIOD_START,
        period_end=PERIOD_END,
    )
    db_session.commit()

    assert report.status == ReportStatus.COMPLETED
    assert report.metrics.total_runs == 4
    assert report.metrics.success_count == 3
    assert report.metrics.failure_count == 1
    assert report.metrics.success_rate == 0.75
    assert "4 runs" in report.ai_summary
    assert "75% success" in report.ai_summary

    persisted = ReportRepository(db_session).get(report.report_id)
    assert persisted is not None
    assert persisted.owner_name == "report-owner"
    assert persisted.metrics.total_runs == 4
    assert persisted.status == ReportStatus.COMPLETED


def test_generate_monthly_report_with_no_runs(db_session):
    _seed_workflow(db_session)
    service = make_reporting_service(db_session)
    report = service.generate_monthly_report(
        owner_name="report-owner",
        period_start=PERIOD_START,
        period_end=PERIOD_END,
    )
    db_session.commit()

    assert report.metrics.total_runs == 0
    assert report.status == ReportStatus.COMPLETED
    persisted = ReportRepository(db_session).list_for_owner("report-owner")
    assert len(persisted) == 1


def test_generate_monthly_report_scopes_by_owner(db_session):
    wf_a = _seed_workflow(db_session, owner="owner-a")
    _seed_workflow(db_session, owner="owner-b")
    _seed_runs(db_session, wf_a.workflow_id, [RunStatus.SUCCESS, RunStatus.SUCCESS])

    service = make_reporting_service(db_session)
    report_b = service.generate_monthly_report(
        owner_name="owner-b",
        period_start=PERIOD_START,
        period_end=PERIOD_END,
    )
    db_session.commit()
    assert report_b.metrics.total_runs == 0

    report_a = service.generate_monthly_report(
        owner_name="owner-a",
        period_start=PERIOD_START,
        period_end=PERIOD_END,
    )
    db_session.commit()
    assert report_a.metrics.total_runs == 2
