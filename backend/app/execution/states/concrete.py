"""Concrete states: Running, Retrying, Succeeded, Failed."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.execution.states.base import ExecutionState, StepFailureDecision

if TYPE_CHECKING:
    from app.execution.context import ExecutionContext


class RunningState(ExecutionState):
    def handle_step_success(
        self,
        ctx: ExecutionContext,
        step_output: dict | None,
        *,
        is_last: bool,
    ) -> None:
        ctx.run.output = step_output
        if is_last:
            ctx.persister.persist_success(step_output)
            ctx.transition_to(SucceededState())

    def handle_step_failure(
        self,
        ctx: ExecutionContext,
        error: Exception,
    ) -> StepFailureDecision:
        if ctx.run.retry_count < ctx.run.max_retries:
            new_count = ctx.run.retry_count + 1
            ctx.run.retry_count = new_count
            ctx.persister.persist_retrying(new_count)
            ctx.persister.persist_running_after_retry()
            return StepFailureDecision.RETRY
        ctx.persister.persist_failed(str(error))
        ctx.transition_to(FailedState())
        return StepFailureDecision.FAILED


class RetryingState(ExecutionState):
    """Optional marker state — engine may go Running -> (DB retrying) -> Running again."""

    def handle_step_success(
        self,
        ctx: ExecutionContext,
        step_output: dict | None,
        *,
        is_last: bool,
    ) -> None:
        RunningState().handle_step_success(ctx, step_output, is_last=is_last)

    def handle_step_failure(
        self,
        ctx: ExecutionContext,
        error: Exception,
    ) -> StepFailureDecision:
        return RunningState().handle_step_failure(ctx, error)


class SucceededState(ExecutionState):
    def handle_step_success(
        self,
        ctx: ExecutionContext,
        step_output: dict | None,
        *,
        is_last: bool,
    ) -> None:
        pass

    def handle_step_failure(
        self,
        ctx: ExecutionContext,
        error: Exception,
    ) -> StepFailureDecision:
        return StepFailureDecision.FAILED


class FailedState(ExecutionState):
    def handle_step_success(
        self,
        ctx: ExecutionContext,
        step_output: dict | None,
        *,
        is_last: bool,
    ) -> None:
        pass

    def handle_step_failure(
        self,
        ctx: ExecutionContext,
        error: Exception,
    ) -> StepFailureDecision:
        return StepFailureDecision.FAILED
