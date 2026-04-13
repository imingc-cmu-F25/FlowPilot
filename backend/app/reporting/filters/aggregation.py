"""AggregationFilter — stage 2 of the reporting pipeline.

Pure computation over PipeData.raw_execution_records. Produces an
AggregatedMetrics object capturing totals, success/failure counts, average
runtime, per-workflow breakdown, and the most frequent error messages.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.reporting.pipeline import Filter, PipeData
from app.reporting.report import AggregatedMetrics

_TOP_ERRORS_LIMIT = 5


class AggregationFilter(Filter):
    def process(self, data: PipeData) -> PipeData:
        records = data.raw_execution_records
        metrics = _compute_metrics(records)
        return data.model_copy(update={"aggregated_metrics": metrics})


def _compute_metrics(records: list[dict[str, Any]]) -> AggregatedMetrics:
    total = len(records)
    if total == 0:
        return AggregatedMetrics()

    success_count = sum(1 for r in records if r.get("status") == "success")
    failure_count = sum(1 for r in records if r.get("status") == "failed")
    success_rate = success_count / total if total else 0.0

    durations: list[float] = []
    for r in records:
        started = r.get("started_at")
        finished = r.get("finished_at")
        if started and finished:
            durations.append((finished - started).total_seconds())
    avg_duration = sum(durations) / len(durations) if durations else 0.0

    runs_per_workflow: dict[str, int] = {}
    for r in records:
        wf = r.get("workflow_id")
        if wf is None:
            continue
        runs_per_workflow[wf] = runs_per_workflow.get(wf, 0) + 1

    error_counter: Counter[str] = Counter()
    for r in records:
        err = r.get("error")
        if err:
            error_counter[err] += 1
    top_errors = [msg for msg, _ in error_counter.most_common(_TOP_ERRORS_LIMIT)]

    return AggregatedMetrics(
        total_runs=total,
        success_count=success_count,
        failure_count=failure_count,
        success_rate=success_rate,
        avg_duration_seconds=avg_duration,
        runs_per_workflow=runs_per_workflow,
        top_error_messages=top_errors,
    )
