"""Celery tasks for the ActionService.

Each workflow step is executed by a dedicated worker process
subscribed to the "actions" queue. If the action crashes, OOMs, or hangs,
only this worker is affected — the engine worker keeps processing other
runs and records the failure as a normal step error.

The engine always calls ``dispatch_action_step``; whether it runs
in-process or out-of-process is controlled by
``settings.action_worker_enabled`` so existing unit tests (which patch
``run_action_sync``) keep the fast synchronous path.
"""

from __future__ import annotations

from typing import Any

from celery import shared_task
from pydantic import TypeAdapter

from app.action.action import ActionStep
from app.core.config import settings

ACTION_QUEUE_NAME = "actions"
CELERY_TASK_EXECUTE_ACTION_STEP = "action.execute_step"

# Rebuilt once per process — discriminated-union (de)serialization is hot.
_STEP_ADAPTER: TypeAdapter[ActionStep] = TypeAdapter(ActionStep)


@shared_task(
    name=CELERY_TASK_EXECUTE_ACTION_STEP,
    queue=ACTION_QUEUE_NAME,
    # Propagate exceptions back to the caller (engine) so the engine's own
    # retry / failure logic runs in the engine process, not this worker.
    # autoretry_for is intentionally omitted: we want the engine to decide.
    acks_late=True,
    track_started=True,
)
def execute_action_step(step_payload: dict, inputs: dict) -> dict[str, Any]:
    """Run a single workflow step in this (isolated) worker process.

    Payloads are plain JSON-serializable dicts so Celery's default JSON
    serializer handles the wire format without custom pickling.
    """
    # Import inside the task so that starting the action worker doesn't drag
    # in the whole workflow service graph; this keeps the action worker's
    # import surface (and memory footprint) small.
    from app.execution.step_runner import run_action_sync

    step = _STEP_ADAPTER.validate_python(step_payload)
    return run_action_sync(step, inputs)


def dispatch_action_step(step: ActionStep, inputs: dict[str, Any]) -> dict[str, Any]:
    """Run an action step, optionally isolated in a dedicated worker process.

    When ``settings.action_worker_enabled`` is true, the step is sent to the
    ``actions`` Celery queue and we block on the AsyncResult with a
    generous timeout. Otherwise we fall back to running in-process — this
    is the default so that unit tests, single-process dev setups, and the
    execution-engine timeout test keep working without a live broker.
    """
    from app.execution.step_runner import run_action_sync

    if not settings.action_worker_enabled:
        return run_action_sync(step, inputs)

    async_result = execute_action_step.apply_async(
        args=[step.model_dump(mode="json"), inputs],
        queue=ACTION_QUEUE_NAME,
    )
    return async_result.get(
        timeout=settings.action_worker_result_timeout_seconds,
        disable_sync_subtasks=False,
    )
