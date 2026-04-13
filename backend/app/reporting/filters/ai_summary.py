"""AISummaryFilter — stage 3 of the reporting pipeline.

Calls the injected AI client to produce a natural-language summary of the
aggregated metrics. Fault-isolated: if the client raises, the filter
swallows the exception and writes a fallback string so earlier stages'
output is preserved and downstream stages still run.
"""

from __future__ import annotations

from app.reporting.ai_client import AISummaryClient
from app.reporting.pipeline import Filter, PipeData
from app.reporting.report import AggregatedMetrics


class AISummaryFilter(Filter):
    def __init__(self, client: AISummaryClient) -> None:
        self._client = client

    def process(self, data: PipeData) -> PipeData:
        metrics = data.aggregated_metrics or AggregatedMetrics()
        try:
            summary = self._client.summarize(metrics.model_dump())
        except Exception as exc:
            summary = f"AI summary unavailable: {type(exc).__name__}"
        return data.model_copy(update={"ai_summary": summary})
