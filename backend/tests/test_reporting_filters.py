"""Unit tests for reporting pipeline filters."""

from datetime import UTC, datetime, timedelta

import pytest
from app.db.connector import get_engine
from app.reporting.ai_client import FakeAISummaryClient
from app.reporting.filters.aggregation import AggregationFilter
from app.reporting.filters.ai_summary import AISummaryFilter
from app.reporting.filters.data_collection import DataCollectionFilter
from app.reporting.filters.formatting import FormattingFilter
from app.reporting.pipeline import PipeData
from app.reporting.report import AggregatedMetrics, ReportStatus
from app.trigger.service import TriggerService
from app.user.repo import UserRepository
from app.workflow.repo import WorkflowRepository
from app.workflow.run import RunStatus, WorkflowRun
from app.workflow.run_repo import WorkflowRunRepository
from app.workflow.service import CreateWorkflowCommand, WorkflowService
from app.workflow.workflow import WorkflowDefinitionBuilder, WorkflowStatus
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


def _make_record(
    workflow_id: str,
    status: str = "success",
    started: datetime | None = None,
    finished: datetime | None = None,
    error: str | None = None,
) -> dict:
    return {
        "run_id": "rid",
        "workflow_id": workflow_id,
        "status": status,
        "trigger_type": "time",
        "triggered_at": PERIOD_START + timedelta(days=1),
        "started_at": started,
        "finished_at": finished,
        "error": error,
    }


# DataCollectionFilter

def test_data_collection_filter_returns_runs_in_period(db_session):
    wf = _seed_workflow(db_session)
    repo = WorkflowRunRepository(db_session)

    in_period = WorkflowRun(
        workflow_id=wf.workflow_id,
        trigger_type="time",
        triggered_at=PERIOD_START + timedelta(days=5),
        status=RunStatus.SUCCESS,
    )
    out_of_period = WorkflowRun(
        workflow_id=wf.workflow_id,
        trigger_type="time",
        triggered_at=PERIOD_START - timedelta(days=5),
        status=RunStatus.SUCCESS,
    )
    repo.create(in_period)
    repo.create(out_of_period)
    db_session.commit()

    filt = DataCollectionFilter(repo)
    data = PipeData(
        owner_name="report-owner",
        period_start=PERIOD_START,
        period_end=PERIOD_END,
    )
    result = filt.process(data)
    assert len(result.raw_execution_records) == 1
    assert result.raw_execution_records[0]["status"] == "success"
    # workflow names are captured for display alongside raw run records
    assert result.workflow_names == {str(wf.workflow_id): wf.name}


def test_data_collection_filter_scopes_by_owner(db_session):
    wf_a = _seed_workflow(db_session, owner="owner-a")
    wf_b = _seed_workflow(db_session, owner="owner-b")
    repo = WorkflowRunRepository(db_session)
    repo.create(WorkflowRun(
        workflow_id=wf_a.workflow_id,
        trigger_type="time",
        triggered_at=PERIOD_START + timedelta(days=1),
    ))
    repo.create(WorkflowRun(
        workflow_id=wf_b.workflow_id,
        trigger_type="time",
        triggered_at=PERIOD_START + timedelta(days=1),
    ))
    db_session.commit()

    result = DataCollectionFilter(repo).process(PipeData(
        owner_name="owner-a",
        period_start=PERIOD_START,
        period_end=PERIOD_END,
    ))
    assert len(result.raw_execution_records) == 1
    assert result.raw_execution_records[0]["workflow_id"] == str(wf_a.workflow_id)
    # workflow_names must be scoped to the requested owner, not leak owner-b
    assert str(wf_b.workflow_id) not in result.workflow_names
    assert result.workflow_names == {str(wf_a.workflow_id): wf_a.name}


# AggregationFilter

def test_aggregation_filter_empty_records_returns_defaults():
    data = PipeData(
        owner_name="a",
        period_start=PERIOD_START,
        period_end=PERIOD_END,
    )
    result = AggregationFilter().process(data)
    assert result.aggregated_metrics == AggregatedMetrics()


def test_aggregation_filter_counts_and_success_rate():
    started = PERIOD_START + timedelta(days=1)
    records = [
        _make_record("wf-a", status="success", started=started,
                     finished=started + timedelta(seconds=2)),
        _make_record("wf-a", status="success", started=started,
                     finished=started + timedelta(seconds=4)),
        _make_record("wf-b", status="failed", started=started,
                     finished=started + timedelta(seconds=6),
                     error="boom"),
        _make_record("wf-b", status="failed", started=None, finished=None,
                     error="boom"),
    ]
    data = PipeData(
        owner_name="a",
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        raw_execution_records=records,
        workflow_names={"wf-a": "Alpha", "wf-b": "Bravo", "wf-unused": "Charlie"},
    )
    metrics = AggregationFilter().process(data).aggregated_metrics
    assert metrics is not None
    assert metrics.total_runs == 4
    assert metrics.success_count == 2
    assert metrics.failure_count == 2
    assert metrics.success_rate == 0.5
    assert metrics.runs_per_workflow == {"wf-a": 2, "wf-b": 2}
    assert metrics.avg_duration_seconds == 4.0  # (2+4+6)/3
    assert metrics.top_error_messages == ["boom"]
    # Only workflows that produced runs in the period appear in workflow_names.
    assert metrics.workflow_names == {"wf-a": "Alpha", "wf-b": "Bravo"}


# FormattingFilter

def test_formatting_filter_builds_report_from_data():
    metrics = AggregatedMetrics(total_runs=3, success_count=3, success_rate=1.0)
    data = PipeData(
        owner_name="a",
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        aggregated_metrics=metrics,
        ai_summary="all green",
    )
    result = FormattingFilter().process(data)
    assert result.formatted_report is not None
    assert result.formatted_report.status == ReportStatus.COMPLETED
    assert result.formatted_report.metrics.total_runs == 3
    assert result.formatted_report.ai_summary == "all green"
    assert result.formatted_report.owner_name == "a"


def test_formatting_filter_defaults_when_metrics_missing():
    data = PipeData(
        owner_name="a",
        period_start=PERIOD_START,
        period_end=PERIOD_END,
    )
    result = FormattingFilter().process(data)
    assert result.formatted_report is not None
    assert result.formatted_report.metrics.total_runs == 0
    assert result.formatted_report.ai_summary == ""


# AISummaryFilter

class _ExplodingAIClient:
    def summarize(self, metrics: dict) -> str:
        raise RuntimeError("model unavailable")


def test_ai_summary_filter_uses_fake_client():
    metrics = AggregatedMetrics(total_runs=5, success_count=4, success_rate=0.8)
    data = PipeData(
        owner_name="a",
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        aggregated_metrics=metrics,
    )
    result = AISummaryFilter(FakeAISummaryClient()).process(data)
    assert result.ai_summary == "Monthly report: 5 runs, 80% success."


def test_ai_summary_filter_falls_back_on_client_error():
    data = PipeData(
        owner_name="a",
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        aggregated_metrics=AggregatedMetrics(total_runs=1),
    )
    result = AISummaryFilter(_ExplodingAIClient()).process(data)
    assert result.ai_summary == "AI summary unavailable: RuntimeError"


def test_ai_summary_filter_handles_missing_metrics():
    data = PipeData(
        owner_name="a",
        period_start=PERIOD_START,
        period_end=PERIOD_END,
    )
    result = AISummaryFilter(FakeAISummaryClient()).process(data)
    assert result.ai_summary == "Monthly report: 0 runs, 0% success."
