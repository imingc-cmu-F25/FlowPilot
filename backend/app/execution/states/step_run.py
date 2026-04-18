"""StepRun domain model — represents a single step execution within a run."""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class StepRunStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepRun(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    step_order: int
    step_name: str
    action_type: str
    status: StepRunStatus
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    inputs: dict | None = None
    output: dict | None = None
    error: str | None = None
