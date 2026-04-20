"""WorkflowRun domain model — represents a single execution of a workflow."""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RunStatus(StrEnum):
    PENDING = "pending"  # created, waiting to be picked up by worker
    RUNNING = "running"  # worker is executing steps
    RETRYING = "retrying"  # between retry attempts (optional; persisted in DB)
    SUCCESS = "success"  # all steps completed successfully
    FAILED = "failed"  # one or more steps failed (terminal)


class WorkflowRun(BaseModel):
    run_id: UUID = Field(default_factory=uuid4)
    workflow_id: UUID
    status: RunStatus = RunStatus.PENDING
    trigger_type: str                                        # "time" or "webhook"
    triggered_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    output: dict | None = None  # last step's output
    retry_count: int = 0
    max_retries: int = 0  # per-run cap; 0 means fail on first step error

    # Captured payload from the triggering event, if any. For webhook
    # triggers this holds {source, path, method, headers, query, body,
    # body_text}; time / custom / calendar_event triggers leave it
    # None. The execution engine seeds the first step's
    # ``previous_output`` from this field so user templates can reach
    # the incoming payload via {{previous_output.body.*}} / {{…headers.*}}
    # without a separate "transform" step. Kept as a free-form dict to
    # keep webhook-source specifics out of the domain model; the builder
    # UI is the only place that needs to know the Slack slash-command
    # shape vs generic JSON, for example.
    trigger_context: dict | None = None
