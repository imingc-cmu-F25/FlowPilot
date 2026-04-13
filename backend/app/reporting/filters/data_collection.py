"""DataCollectionFilter — stage 1 of the reporting pipeline.

Reads workflow_runs scoped to (owner_name, period) via WorkflowRunRepository
and writes them as plain dicts onto PipeData.raw_execution_records. Keeping
the collected records as dicts (rather than domain objects) shields later
filters from repository/domain coupling.
"""

from __future__ import annotations

from typing import Any

from app.reporting.pipeline import Filter, PipeData
from app.workflow.run_repo import WorkflowRunRepository


class DataCollectionFilter(Filter):
    def __init__(self, run_repo: WorkflowRunRepository) -> None:
        self._run_repo = run_repo

    def process(self, data: PipeData) -> PipeData:
        runs = self._run_repo.list_for_owner_in_period(
            owner_name=data.owner_name,
            period_start=data.period_start,
            period_end=data.period_end,
        )
        records: list[dict[str, Any]] = [
            {
                "run_id": str(run.run_id),
                "workflow_id": str(run.workflow_id),
                "status": run.status.value,
                "trigger_type": run.trigger_type,
                "triggered_at": run.triggered_at,
                "started_at": run.started_at,
                "finished_at": run.finished_at,
                "error": run.error,
            }
            for run in runs
        ]
        return data.model_copy(update={"raw_execution_records": records})
