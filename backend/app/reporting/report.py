"""MonthlyReport domain model — represents a user's monthly workflow report."""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ReportStatus(StrEnum):
    PENDING = "pending"          # created, pipeline not yet run
    GENERATING = "generating"    # pipeline currently running
    COMPLETED = "completed"      # pipeline finished successfully
    FAILED = "failed"            # pipeline failed terminally


class AggregatedMetrics(BaseModel):
    """Output of the AggregationFilter — pure computed statistics."""

    total_runs: int = 0
    success_count: int = 0
    failure_count: int = 0
    success_rate: float = 0.0
    avg_duration_seconds: float = 0.0
    runs_per_workflow: dict[str, int] = Field(default_factory=dict)
    # workflow_id -> workflow name, captured at report-generation time so
    # renames/deletions after the fact don't corrupt historical reports.
    workflow_names: dict[str, str] = Field(default_factory=dict)
    top_error_messages: list[str] = Field(default_factory=list)


class MonthlyReport(BaseModel):
    report_id: UUID = Field(default_factory=uuid4)
    owner_name: str
    period_start: datetime
    period_end: datetime
    status: ReportStatus = ReportStatus.PENDING
    metrics: AggregatedMetrics = Field(default_factory=AggregatedMetrics)
    ai_summary: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
