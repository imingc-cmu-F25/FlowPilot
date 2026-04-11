from datetime import UTC, datetime

from app.trigger.trigger import BaseTrigger, TriggerSchema
from app.trigger.triggerConfig import TimeTriggerConfig


class TimeTrigger(BaseTrigger):
    """
    Fires at trigger_at (one-time), or periodically according to recurrence.
    The engine evaluates this trigger every minute.
    """
    schema = TriggerSchema(
        id="time",
        name="Time",
        description="Fires once at a specific datetime, or repeatedly on a schedule",
        config_fields=[
            {
                "name": "trigger_at",
                "type": "datetime",
                "required": True,
                "description": "ISO-8601 datetime with timezone, e.g. 2026-05-01T09:00:00Z",
            },
            {
                "name": "timezone",
                "type": "string",
                "required": False,
                "default": "UTC",
                "description": "IANA timezone name for display purposes",
            },
            {
                "name": "recurrence",
                "type": "object",
                "required": False,
                "default": None,
                "description": (
                    "Optional recurrence rule. "
                    "frequency: minutely | hourly | daily | weekly | custom. "
                    "interval: repeat every N units (default 1). "
                    "days_of_week: [0-6] Mon-Sun, for weekly. "
                    "cron_expression: for custom."
                ),
            },
        ],
    )
    fired: bool = False  # track if a recurring trigger has already fired for the current occurrence

    async def evaluate(self, context: dict) -> bool:
        config: TimeTriggerConfig = context["config"]
        now = datetime.now(UTC)

        if self.fired:
            # already fired
            return False

        if config.recurrence is None:
            # One-time: fire when we reach or pass trigger_at
            due = now >= config.trigger_at
            if due:
                self.fired = True
            return due

        # Recurring: fire if now is within the 60-second window of the current occurrence
        due = config.recurrence.is_due(config.trigger_at, now)
        if due:
            self.fired = True
        return due

