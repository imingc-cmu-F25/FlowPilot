"""Ensures a hung action is cancelled by the engine's timeout wrapper."""

import asyncio
from uuid import uuid4

import pytest

from app.action.action import ActionType
from app.action.sendEmailAction import SendEmailActionStep
from app.execution.step_runner import ActionTimeoutError, run_action_sync


class _SlowAction:
    """Fake action that blocks forever — stands in for any hung external call."""

    async def execute(self, _inputs):
        await asyncio.sleep(60)
        return {"ok": True}


def test_run_action_sync_raises_action_timeout_error(monkeypatch):
    step = SendEmailActionStep(
        step_id=uuid4(),
        action_type=ActionType.SEND_EMAIL,
        name="email",
        step_order=0,
        to_template="a@b.com",
        subject_template="s",
        body_template="b",
    )

    monkeypatch.setattr(
        "app.execution.step_runner.get_action_for_step",
        lambda _s: _SlowAction(),
    )

    with pytest.raises(ActionTimeoutError):
        run_action_sync(step, {"run_id": "r", "workflow_id": "w"}, timeout_seconds=0.05)
