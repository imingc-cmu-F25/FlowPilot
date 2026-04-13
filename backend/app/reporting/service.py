"""ReportingService — composition root for the reporting pipeline.

Assembles the five filters and runs them inside a single Pipeline.execute
call. Called by the Celery task (scheduled via beat) and by the manual
trigger API endpoint.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.reporting.ai_client import AISummaryClient, FakeAISummaryClient
from app.reporting.filters.aggregation import AggregationFilter
from app.reporting.filters.ai_summary import AISummaryFilter
from app.reporting.filters.data_collection import DataCollectionFilter
from app.reporting.filters.distribution import DistributionFilter
from app.reporting.filters.formatting import FormattingFilter
from app.reporting.pipeline import PipeData, Pipeline
from app.reporting.repo import ReportRepository
from app.reporting.report import MonthlyReport
from app.workflow.run_repo import WorkflowRunRepository


class ReportingService:
    def __init__(
        self,
        run_repo: WorkflowRunRepository,
        report_repo: ReportRepository,
        ai_client: AISummaryClient,
    ) -> None:
        self._pipeline = Pipeline([
            DataCollectionFilter(run_repo),
            AggregationFilter(),
            AISummaryFilter(ai_client),
            FormattingFilter(),
            DistributionFilter(report_repo),
        ])

    def generate_monthly_report(
        self,
        owner_name: str,
        period_start: datetime,
        period_end: datetime,
    ) -> MonthlyReport:
        data = PipeData(
            owner_name=owner_name,
            period_start=period_start,
            period_end=period_end,
        )
        result = self._pipeline.execute(data)
        assert result.formatted_report is not None  # DistributionFilter guarantees this
        return result.formatted_report


def make_reporting_service(db: Session) -> ReportingService:
    """Default DI factory — uses FakeAISummaryClient until a real one lands."""
    return ReportingService(
        run_repo=WorkflowRunRepository(db),
        report_repo=ReportRepository(db),
        ai_client=FakeAISummaryClient(),
    )
