"""dispatch_action_step routing — local vs Celery-isolated execution."""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

from app.action.action import ActionType
from app.action.sendEmailAction import SendEmailActionStep
from app.action.tasks import dispatch_action_step, execute_action_step
from app.core.config import settings

# Importing the worker attaches shared_tasks to the FlowPilot Celery app
# (so apply_async doesn't fall back to the default amqp broker). The worker
# module also flips CELERY_TASK_ALWAYS_EAGER on from the env var set in
# conftest, which is what makes the eager dispatch path testable.
from app.worker import celery_app  # noqa: F401


def _step() -> SendEmailActionStep:
    return SendEmailActionStep(
        step_id=uuid4(),
        action_type=ActionType.SEND_EMAIL,
        name="email",
        step_order=0,
        to_template="a@b.com",
        subject_template="s",
        body_template="b",
    )


def test_dispatch_runs_locally_by_default(monkeypatch):
    monkeypatch.setattr(settings, "action_worker_enabled", False)
    with patch(
        "app.execution.step_runner.run_action_sync", return_value={"status": "sent"}
    ) as run_mock:
        out = dispatch_action_step(_step(), {"run_id": "r", "workflow_id": "w"})
    assert out == {"status": "sent"}
    run_mock.assert_called_once()


def test_dispatch_routes_via_celery_when_enabled(monkeypatch):
    monkeypatch.setattr(settings, "action_worker_enabled", True)
    # CELERY_TASK_ALWAYS_EAGER is on in tests, so apply_async runs the task
    # inline — but it still goes through the dedicated queue/worker codepath.
    with patch(
        "app.execution.step_runner.run_action_sync", return_value={"status": "sent"}
    ) as run_mock:
        out = dispatch_action_step(_step(), {"run_id": "r", "workflow_id": "w"})
    assert out == {"status": "sent"}
    assert run_mock.called


def test_execute_action_step_task_roundtrips_pydantic_step():
    """Task payload is plain dicts; task reconstructs the right ActionStep."""
    step = _step()
    with patch(
        "app.execution.step_runner.run_action_sync", return_value={"ok": True}
    ) as run_mock:
        out = execute_action_step(
            step.model_dump(mode="json"),
            {"run_id": "r", "workflow_id": "w"},
        )
    assert out == {"ok": True}
    called_step = run_mock.call_args.args[0]
    assert isinstance(called_step, SendEmailActionStep)
    assert called_step.to_template == "a@b.com"
