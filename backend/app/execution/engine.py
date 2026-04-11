"""Workflow execution engine — claims run, walks steps, delegates to State pattern context."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.execution.context import ExecutionContext
from app.execution.persistence import RunStatePersister
from app.execution.states.base import StepFailureDecision
from app.execution.step_runner import build_execution_inputs, run_action_sync
from app.workflow.repo import WorkflowRepository
from app.workflow.run import RunStatus
from app.workflow.run_repo import WorkflowRunRepository


class ExecutionEngine:
    def __init__(self, db: Session) -> None:
        self._db = db

    def execute(self, run_id: UUID) -> None:
        run_repo = WorkflowRunRepository(self._db)
        claimed = run_repo.try_claim_running(run_id)
        if claimed is None:
            existing = run_repo.get(run_id)
            if existing is None:
                return
            # Idempotent exit: already finished or another worker claimed
            if existing.status in (RunStatus.SUCCESS, RunStatus.FAILED):
                return
            if existing.status == RunStatus.RUNNING:
                return
            return

        run = claimed
        # Release DB lock quickly before potentially slow action I/O
        self._db.commit()

        wf_repo = WorkflowRepository(self._db)
        wf = wf_repo.get(run.workflow_id)
        if wf is None:
            run_repo.mark_failed(run_id, "Workflow not found")
            self._db.commit()
            return

        if not wf.enabled:
            run_repo.mark_failed(run_id, "Workflow is not enabled")
            self._db.commit()
            return

        steps = sorted(wf.steps, key=lambda s: s.step_order)
        persister = RunStatePersister(run_repo, run_id)
        ctx = ExecutionContext(run, persister)

        if not steps:
            run_repo.mark_failed(run_id, "Workflow has no steps")
            self._db.commit()
            return

        previous_output: dict | None = None
        for step in steps:
            while True:
                try:
                    inputs = build_execution_inputs(
                        step,
                        run_id=run.run_id,
                        workflow_id=run.workflow_id,
                        previous_output=previous_output,
                    )
                    step_out = run_action_sync(step, inputs)
                except Exception as exc:  # noqa: BLE001 — surface as run failure / retry
                    decision = ctx.request_step_failure(exc)
                    self._db.commit()
                    if decision == StepFailureDecision.RETRY:
                        run = run_repo.get(run_id)
                        if run is None:
                            return
                        ctx.run = run
                        continue
                    return

                previous_output = step_out
                is_last = step == steps[-1]
                ctx.request_step_success(step_out, is_last=is_last)
                self._db.commit()
                break
