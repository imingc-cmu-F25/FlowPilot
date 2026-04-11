"""WorkflowRun domain model — represents a single execution of a workflow."""

from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RunStatus(StrEnum):
    PENDING  = "pending"   # created, waiting to be picked up by worker
    RUNNING  = "running"   # worker is executing steps
    SUCCESS  = "success"   # all steps completed successfully
    FAILED   = "failed"    # one or more steps failed


class WorkflowRun(BaseModel):
    run_id: UUID = Field(default_factory=uuid4)
    workflow_id: UUID
    status: RunStatus = RunStatus.PENDING
    trigger_type: str                                        # "time" or "webhook"
    triggered_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    output: dict | None = None                               # last step's output
