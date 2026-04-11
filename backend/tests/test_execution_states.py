"""Unit tests for State pattern (execution states)."""

from unittest.mock import MagicMock
from uuid import uuid4

from app.execution.context import ExecutionContext
from app.execution.persistence import RunStatePersister
from app.execution.states.base import StepFailureDecision
from app.execution.states.concrete import RunningState, SucceededState
from app.workflow.run import RunStatus, WorkflowRun


def test_running_state_success_last_step_persists_success():
    repo = MagicMock()
    run_id = uuid4()
    wf_id = uuid4()
    persister = RunStatePersister(repo, run_id)
    run = WorkflowRun(
        run_id=run_id,
        workflow_id=wf_id,
        status=RunStatus.RUNNING,
        trigger_type="manual",
        max_retries=0,
    )
    ctx = ExecutionContext(run, persister, initial_state=RunningState())
    ctx.request_step_success({"a": 1}, is_last=True)
    assert isinstance(ctx.current_state, SucceededState)
    repo.mark_success.assert_called_once_with(run_id, {"a": 1})


def test_running_state_failure_exhausted_marks_failed():
    repo = MagicMock()
    run_id = uuid4()
    wf_id = uuid4()
    persister = RunStatePersister(repo, run_id)
    run = WorkflowRun(
        run_id=run_id,
        workflow_id=wf_id,
        status=RunStatus.RUNNING,
        trigger_type="manual",
        retry_count=0,
        max_retries=0,
    )
    ctx = ExecutionContext(run, persister, initial_state=RunningState())
    d = ctx.request_step_failure(RuntimeError("boom"))
    assert d == StepFailureDecision.FAILED
    repo.mark_failed.assert_called_once()
