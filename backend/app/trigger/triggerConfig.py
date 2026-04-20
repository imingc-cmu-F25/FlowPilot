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

class CustomTriggerConfig(BaseModel):
    """User-defined condition trigger evaluated against runtime context.

    ``timezone`` is an IANA zone (e.g. "Asia/Taipei"). The evaluator
    resolves time-related names (``hour``, ``minute``, ``weekday`` …)
    in this zone, matching the way TimeTriggerConfig interprets its
    stored wall-clock moment. Defaults to UTC both for backwards
    compatibility with pre-existing rows and because the dispatcher
    runs in UTC — users are expected to pick their own zone in the
    builder UI (which pre-fills browserTimezone()).
    """
    type: Literal[TriggerType.CUSTOM] = TriggerType.CUSTOM
    trigger_id: UUID = Field(default_factory=uuid4)
    condition: str
    source: str = "event_payload"
    description: str = ""
    timezone: str = "UTC"

    def validate_config(self) -> None:
        if not self.condition.strip():
            raise ValueError("condition is required")


class CalendarEventTriggerConfig(BaseModel):
    """Fire when a new event lands in the user's cached Google Calendar.

    Evaluation is cache-driven, not API-driven: the
    ``connectors.sync_google_calendars`` beat task keeps
    ``cached_calendar_events`` fresh every 10 minutes, and
    ``trigger.dispatch_calendar_event_triggers`` (every minute) looks for
    rows whose ``first_seen_at`` is newer than the last dispatch for this
    workflow. Exactly one workflow run is emitted per tick no matter how
    many events matched — the workflow's own steps (e.g.
    ``CalendarListUpcoming``) are how it observes the event data.
    """

    type: Literal[TriggerType.CALENDAR_EVENT] = TriggerType.CALENDAR_EVENT
    trigger_id: UUID = Field(default_factory=uuid4)
    calendar_id: str = "primary"
    title_contains: str = ""
    # Debounce window: ignore first-seen events whose ``first_seen_at``
    # falls inside this many seconds before the workflow was last
    # dispatched. Keeps overlapping sync ticks from firing the same
    # workflow twice for the same set of newly-added events.
    dedup_seconds: int = 60

    def validate_config(self) -> None:
        if self.dedup_seconds < 0:
            raise ValueError("dedup_seconds must be non-negative")


# Add more trigger configs classes here

# Discriminated union used as WorkflowDefinition.trigger
TriggerConfig = Annotated[
    TimeTriggerConfig
    | WebhookTriggerConfig
    | CustomTriggerConfig
    | CalendarEventTriggerConfig,
    Field(discriminator="type"),
]
