"""GoF State interface for workflow run lifecycle."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.execution.context import ExecutionContext


class StepFailureDecision(StrEnum):
    RETRY = "retry"
    FAILED = "failed"


class ExecutionState(ABC):
    @abstractmethod
    def handle_step_success(
        self,
        ctx: ExecutionContext,
        step_output: dict | None,
        *,
        is_last: bool,
    ) -> None:
        ...

    @abstractmethod
    def handle_step_failure(
        self,
        ctx: ExecutionContext,
        error: Exception,
    ) -> StepFailureDecision:
        ...
