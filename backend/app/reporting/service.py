"""ReportingService — composition root for the reporting pipeline.

Assembles the five filters and runs them inside a single Pipeline.execute
call. Called by the Celery task (scheduled via beat) and by the manual
trigger API endpoint.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.reporting.ai_client import (
    AISummaryClient,
    FakeAISummaryClient,
    OpenAIAISummaryClient,
)
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


def _default_ai_client() -> AISummaryClient:
    """Pick the AI client based on settings.

    If an OpenAI key is configured we hit the real API; otherwise the fake
    client keeps the pipeline runnable in local dev / CI / tests without
    network access or secrets.
    """
    if settings.openai_api_key:
        return OpenAIAISummaryClient(api_key=settings.openai_api_key)
    return FakeAISummaryClient()


def make_reporting_service(db: Session) -> ReportingService:
    """Default DI factory — picks the AI client based on settings."""
    return ReportingService(
        run_repo=WorkflowRunRepository(db),
        report_repo=ReportRepository(db),
        ai_client=_default_ai_client(),
    )
