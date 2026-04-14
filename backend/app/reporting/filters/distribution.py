"""DistributionFilter — stage 5 of the reporting pipeline.

"Distribution to WebClient" is implemented as persistence: the formatted
report is written to the reports table, which the API serves. A future
extension could push to email/webhook; keeping persistence as its own
filter means that extension would compose cleanly.
"""

from __future__ import annotations

from app.reporting.pipeline import Filter, PipeData
from app.reporting.repo import ReportRepository


class DistributionFilter(Filter):
    def __init__(self, report_repo: ReportRepository) -> None:
        self._report_repo = report_repo

    def process(self, data: PipeData) -> PipeData:
        if data.formatted_report is None:
            raise ValueError("DistributionFilter requires formatted_report to be set")
        self._report_repo.create(data.formatted_report)
        return data
