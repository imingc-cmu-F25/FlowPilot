from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.trigger.recurrence import RecurrenceRule
from app.trigger.trigger import TriggerType


class TimeTriggerConfig(BaseModel):
    """
    Fire the workflow at a specific datetime, optionally on a recurring schedule.

    - recurrence=None  -> one-time trigger (fires when now >= trigger_at)
    - recurrence set   -> periodic trigger starting from trigger_at
    """
    type: Literal[TriggerType.TIME] = TriggerType.TIME
    trigger_id: UUID = Field(default_factory=uuid4)
    trigger_at: datetime    # ISO-8601, must be timezone-aware
    timezone: str = "UTC"   # IANA timezone name for display
    recurrence: RecurrenceRule | None = None

    def validate_config(self) -> None:
        if self.trigger_at is None:
            raise ValueError("trigger_at is required")
        if self.trigger_at.tzinfo is None:
            raise ValueError("trigger_at must be timezone-aware (include UTC offset)")
        if self.recurrence is not None:
            self.recurrence.validate_rule()


class WebhookTriggerConfig(BaseModel):
    """Fire the workflow when an HTTP request arrives at the configured path."""

    type: Literal[TriggerType.WEBHOOK] = TriggerType.WEBHOOK
    trigger_id: UUID = Field(default_factory=uuid4)
    # routing
    path: str
    method: str = "POST"
    # security
    secret_ref: str = ""
    # filtering
    event_filter: str = ""
    header_filters: dict[str, str] = {}

    def validate_config(self) -> None:
        if not self.path:
            raise ValueError("path is required")
        if not self.path.startswith("/"):
            raise ValueError("path must start with /")
        if self.method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            raise ValueError(f"Unsupported HTTP method: {self.method}")


# Discriminated union used as WorkflowDefinition.trigger
TriggerConfig = Annotated[
    TimeTriggerConfig | WebhookTriggerConfig,
    Field(discriminator="type"),
]
