"""Map persisted ActionStep models to BaseAction and build execute() inputs."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from app.action.action import ActionStep
from app.action.base import BaseAction
from app.action.calendarAction import CalendarActionStep, CalendarCreateEventAction
from app.action.httpRequestAction import HttpRequestAction, HttpRequestActionStep
from app.action.sendEmailAction import SendEmailAction, SendEmailActionStep
from app.core.config import settings
from app.execution.contracts import (
    EXECUTION_INPUT_PREVIOUS_OUTPUT,
    EXECUTION_INPUT_RUN_ID,
    EXECUTION_INPUT_WORKFLOW_ID,
)


class ActionTimeoutError(RuntimeError):
    """Raised when a single action exceeds the configured timeout."""


def get_action_for_step(step: ActionStep) -> BaseAction:
    if isinstance(step, HttpRequestActionStep):
        return HttpRequestAction()
    if isinstance(step, SendEmailActionStep):
        return SendEmailAction()
    if isinstance(step, CalendarActionStep):
        return CalendarCreateEventAction()
    raise ValueError(
        f"Execution not implemented for action type: {getattr(step, 'action_type', step)}"
    )


def build_execution_inputs(
    step: ActionStep,
    *,
    run_id: UUID,
    workflow_id: UUID,
    previous_output: dict[str, Any] | None,
) -> dict[str, Any]:
    """Stable keys for all actions; action-specific keys merged on top."""
    base: dict[str, Any] = {
        EXECUTION_INPUT_RUN_ID: str(run_id),
        EXECUTION_INPUT_WORKFLOW_ID: str(workflow_id),
        EXECUTION_INPUT_PREVIOUS_OUTPUT: previous_output or {},
    }
    if isinstance(step, HttpRequestActionStep):
        base.update(
            {
                "method": step.method,
                "url": step.url_template,
                "headers": dict(step.headers),
                "body": None,
            }
        )
        return base
    if isinstance(step, SendEmailActionStep):
        base.update(
            {
                "to": step.to_template,
                "subject": step.subject_template,
                "body": step.body_template,
            }
        )
        return base
    if isinstance(step, CalendarActionStep):
        base.update(
            {
                "calendar_id": step.calendar_id,
                "title": step.title_template,
                "start": step.start_mapping,
                "end": step.end_mapping,
            }
        )
        return base
    raise ValueError(f"Unsupported step type for input building: {type(step)}")


def run_action_sync(
    step: ActionStep,
    inputs: dict[str, Any],
    *,
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    """Run async BaseAction.execute with a hard timeout.

    A per-action timeout is the minimum fault-isolation we can offer without
    running each action in its own process: a runaway or hung HTTP call gets
    cancelled and surfaces as a normal step failure instead of wedging a
    Celery worker forever.
    """
    action = get_action_for_step(step)
    limit = (
        timeout_seconds
        if timeout_seconds is not None
        else settings.action_execution_timeout_seconds
    )

    async def _with_timeout() -> dict[str, Any]:
        try:
            return await asyncio.wait_for(action.execute(inputs), timeout=limit)
        except TimeoutError as exc:
            raise ActionTimeoutError(
                f"Action {type(action).__name__} exceeded {limit:.1f}s timeout"
            ) from exc

    return asyncio.run(_with_timeout())
