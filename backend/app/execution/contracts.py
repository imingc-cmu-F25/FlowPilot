"""
Stable contracts for Workflow Execution — import from here for triggers, API, and tests.

- `workflow_runs.status` stores the same strings as `RunStatus` (see `app.workflow.run`).
- Celery task name must match `CELERY_TASK_EXECUTE_RUN`.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.workflow.run import RunStatus

# Public Celery task name — keep in sync with @shared_task(name=...) in tasks.py
CELERY_TASK_EXECUTE_RUN = "execution.execute_workflow_run"


class WorkflowRunTaskPayload(BaseModel):
    """Payload for enqueueing a workflow run job. `run_id` must already exist in `workflow_runs`."""

    run_id: UUID
    idempotency_key: str | None = None


class ExecutionLogEvent(BaseModel):
    """Reserved for step-level logs (optional DB later). Does not affect execution."""

    run_id: UUID
    step_order: int | None = None
    level: str = "info"
    message: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)


# --- Keys passed into BaseAction.execute(inputs) alongside action-specific fields ---
EXECUTION_INPUT_RUN_ID = "run_id"
EXECUTION_INPUT_WORKFLOW_ID = "workflow_id"
EXECUTION_INPUT_PREVIOUS_OUTPUT = "previous_output"
# Present for every step so connector-backed actions (e.g. Google Calendar)
# can resolve the owning user's stored credentials without a separate hop.
EXECUTION_INPUT_OWNER_NAME = "owner_name"
# Every step — regardless of position — gets the original trigger payload
# under this key. It decouples "what fired me" (the trigger) from "what
# the previous step returned" (previous_output), so chaining an HTTP call
# or a List Upcoming Events step between the webhook and a Create
# Calendar Event doesn't blow away ``{{trigger.parsed.duration}}``.
EXECUTION_INPUT_TRIGGER = "trigger"


def public_run_status_values() -> tuple[str, ...]:
    """Documented enum strings persisted in DB and returned by API."""
    return tuple(s.value for s in RunStatus)


def enqueue_execute_run(run_id: UUID, *, idempotency_key: str | None = None) -> None:
    """
    Thin wrapper for teammates — enqueue execution without importing Celery app details.
    Import: `from app.execution.contracts import enqueue_execute_run`
    """
    from app.worker import celery_app

    payload = WorkflowRunTaskPayload(run_id=run_id, idempotency_key=idempotency_key)
    celery_app.send_task(CELERY_TASK_EXECUTE_RUN, args=[str(payload.run_id)])
