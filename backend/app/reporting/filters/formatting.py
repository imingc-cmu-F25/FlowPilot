"""FormattingFilter — stage 4 of the reporting pipeline.

Assembles the final MonthlyReport object from already-populated PipeData
fields. Does not touch the AI client; reads whatever summary the upstream
AISummaryFilter produced (empty string is valid).
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.reporting.pipeline import Filter, PipeData
from app.reporting.report import AggregatedMetrics, MonthlyReport, ReportStatus


class FormattingFilter(Filter):
    def process(self, data: PipeData) -> PipeData:
        metrics = data.aggregated_metrics or AggregatedMetrics()
        now = datetime.now(UTC)
        report = MonthlyReport(
            owner_name=data.owner_name,
            period_start=data.period_start,
            period_end=data.period_end,
            status=ReportStatus.COMPLETED,
            metrics=metrics,
            ai_summary=data.ai_summary,
            created_at=now,
            updated_at=now,
        )
        return data.model_copy(update={"formatted_report": report})
