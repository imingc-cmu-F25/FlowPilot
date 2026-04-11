"""GoF Context — holds current ExecutionState and delegates handle_* for polymorphic behavior."""

from __future__ import annotations

from app.execution.persistence import RunStatePersister
from app.execution.states.base import ExecutionState, StepFailureDecision
from app.execution.states.concrete import RunningState
from app.workflow.run import WorkflowRun


class ExecutionContext:
    """
    Context (GoF State pattern): stores run data and current_state;
    request_* methods delegate to current_state.handle_*.
    """

    def __init__(
        self,
        run: WorkflowRun,
        persister: RunStatePersister,
        initial_state: ExecutionState | None = None,
    ) -> None:
        self.run = run
        self.persister = persister
        self.current_state: ExecutionState = initial_state or RunningState()

    def transition_to(self, state: ExecutionState) -> None:
        self.current_state = state

    def request_step_success(
        self,
        step_output: dict | None,
        *,
        is_last: bool,
    ) -> None:
        self.current_state.handle_step_success(self, step_output, is_last=is_last)

    def request_step_failure(self, error: Exception) -> StepFailureDecision:
        return self.current_state.handle_step_failure(self, error)
