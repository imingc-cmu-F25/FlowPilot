"""CalendarEventTrigger — fires when a new cached Google Calendar event arrives.

Evaluation is cache-driven: the actual "did a new event appear?" decision is
made by ``trigger.dispatch_calendar_event_triggers`` (a beat task) against
``cached_calendar_events``. This trigger class exists to expose a consistent
BaseTrigger + TriggerSchema surface so the frontend registry and AI
suggestion layer can discover calendar-event triggers the same way they
discover time / webhook / custom ones.
"""

from app.trigger.trigger import BaseTrigger, TriggerSchema


class CalendarEventTrigger(BaseTrigger):
    schema = TriggerSchema(
        id="calendar_event",
        name="New Calendar Event",
        description=(
            "Fires when a newly-synced Google Calendar event is detected for "
            "the workflow owner. Requires the user to have linked their "
            "Google account on the Integrations page."
        ),
        config_fields=[
            {
                "name": "calendar_id",
                "type": "string",
                "required": False,
                "default": "primary",
                "description": "Google Calendar id to watch (usually 'primary')",
            },
            {
                "name": "title_contains",
                "type": "string",
                "required": False,
                "default": "",
                "description": (
                    "Case-insensitive substring filter on the event title. "
                    "Empty string means accept any title."
                ),
            },
            {
                "name": "dedup_seconds",
                "type": "integer",
                "required": False,
                "default": 60,
                "description": (
                    "Debounce window. Events whose first_seen_at falls "
                    "within this many seconds of the previous dispatch are "
                    "ignored, preventing duplicate fires from overlapping "
                    "sync ticks."
                ),
            },
        ],
    )

    async def evaluate(self, _context: dict) -> bool:
        # Intentionally a no-op: the real firing decision lives in
        # ``app.trigger.tasks.dispatch_calendar_event_triggers`` which walks
        # cached_calendar_events per workflow. This class exists for schema
        # discovery / registry symmetry.
        return True
