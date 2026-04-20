"""Map persisted ActionStep models to BaseAction and build execute() inputs."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from app.action.action import ActionStep
from app.action.base import BaseAction
from app.action.calendarAction import CalendarActionStep, CalendarCreateEventAction
from app.action.calendarListUpcomingAction import (
    CalendarListUpcomingAction,
    CalendarListUpcomingActionStep,
)
from app.action.httpRequestAction import HttpRequestAction, HttpRequestActionStep
from app.action.sendEmailAction import SendEmailAction, SendEmailActionStep
from app.core.config import settings
from app.execution.contracts import (
    EXECUTION_INPUT_OWNER_NAME,
    EXECUTION_INPUT_PREVIOUS_OUTPUT,
    EXECUTION_INPUT_RUN_ID,
    EXECUTION_INPUT_WORKFLOW_ID,
)
from app.execution.templating import render_template


class ActionTimeoutError(RuntimeError):
    """Raised when a single action exceeds the configured timeout."""


def get_action_for_step(step: ActionStep) -> BaseAction:
    if isinstance(step, HttpRequestActionStep):
        return HttpRequestAction()
    if isinstance(step, SendEmailActionStep):
        return SendEmailAction()
    if isinstance(step, CalendarActionStep):
        return CalendarCreateEventAction()
    if isinstance(step, CalendarListUpcomingActionStep):
        return CalendarListUpcomingAction()
    raise ValueError(
        f"Execution not implemented for action type: {getattr(step, 'action_type', step)}"
    )


def build_execution_inputs(
    step: ActionStep,
    *,
    run_id: UUID,
    workflow_id: UUID,
    previous_output: dict[str, Any] | None,
    owner_name: str | None = None,
) -> dict[str, Any]:
    """Stable keys for all actions; action-specific keys merged on top.

    ``owner_name`` is populated for connector-backed actions (e.g. Google
    Calendar) that need to resolve the end-user's stored OAuth tokens from
    the engine-visible DB.
    """
    base: dict[str, Any] = {
        EXECUTION_INPUT_RUN_ID: str(run_id),
        EXECUTION_INPUT_WORKFLOW_ID: str(workflow_id),
        EXECUTION_INPUT_PREVIOUS_OUTPUT: previous_output or {},
        EXECUTION_INPUT_OWNER_NAME: owner_name,
    }

    # Template context passed to every ``{{path}}`` substitution. Keeping
    # the full ``base`` means users can also reach ``{{run_id}}``,
    # ``{{workflow_id}}``, ``{{owner_name}}`` if they want — useful for
    # debugging emails and idempotency tokens in downstream APIs.
    ctx = base

    def _r(value: str | None) -> str:
        """Render templates and tolerate ``None`` as empty."""
        return render_template(value or "", ctx)

    if isinstance(step, HttpRequestActionStep):
        rendered_body = _r(step.body_template)
        # Only send a body for methods that actually carry one. GET/HEAD
        # technically can, but most servers reject it and httpx would still
        # set Content-Length: 0 when the template is empty — passing None
        # here keeps the wire format clean.
        body: str | None = (
            rendered_body
            if rendered_body and step.method in {"POST", "PUT", "PATCH", "DELETE"}
            else None
        )
        base.update(
            {
                "method": step.method,
                "url": _r(step.url_template),
                "headers": {k: _r(v) for k, v in step.headers.items()},
                "body": body,
            }
        )
        return base
    if isinstance(step, SendEmailActionStep):
        base.update(
            {
                "to": _r(step.to_template),
                "subject": _r(step.subject_template),
                "body": _r(step.body_template),
            }
        )
        return base
    if isinstance(step, CalendarActionStep):
        base.update(
            {
                "calendar_id": step.calendar_id,
                "title": _r(step.title_template),
                "start": _r(step.start_mapping),
                "end": _r(step.end_mapping),
            }
        )
        return base
    if isinstance(step, CalendarListUpcomingActionStep):
        # No templating here — these are short identifiers / filters the
        # user picks directly in the builder, not free-form strings that
        # need to reference prior step output.
        base.update(
            {
                "calendar_id": step.calendar_id,
                "max_results": step.max_results,
                "title_contains": step.title_contains,
                "window_hours": step.window_hours,
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
