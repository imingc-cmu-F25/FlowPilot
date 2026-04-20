import re
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.action.base import ActionSchema, ActionType, BaseAction

# Relative time tokens — accepted in ``start_mapping`` / ``end_mapping``
# so Slack-style "create a focus block now" demos don't require the user
# to hand-write ISO 8601 on every trigger. Intentionally tiny grammar:
#
#   now               → current UTC ISO 8601
#   now+30m           → 30 minutes from now
#   now-15m           → 15 minutes ago
#   now+2h            → 2 hours from now
#   start+30m         → (end field only) 30 minutes after the resolved start
#
# Anything that doesn't match passes through untouched so users can still
# paste a literal ISO 8601 value (e.g. from a CalendarListUpcoming step).
_TIME_TOKEN_RE = re.compile(
    r"^\s*(now|start)\s*(?:([+-])\s*(\d+)\s*([mhd]))?\s*$",
    re.IGNORECASE,
)


def _resolve_time_token(
    value: str,
    *,
    start_reference: datetime | None = None,
    clock: "datetime | None" = None,
) -> str:
    """Resolve a relative time token to an ISO 8601 string.

    ``clock`` is injectable for tests; in production we always use
    ``datetime.now(UTC)``. Unrecognised input is returned verbatim so
    the caller can forward literal ISO timestamps to the Calendar API
    without any extra branching.
    """
    match = _TIME_TOKEN_RE.match(value or "")
    if match is None:
        return value
    base_name, sign, amount, unit = match.group(1), match.group(2), match.group(3), match.group(4)

    if base_name.lower() == "now":
        base = clock or datetime.now(UTC)
    elif base_name.lower() == "start":
        # ``start+X`` on the start field itself is nonsense. Leave it
        # verbatim so validation / the Calendar API can complain
        # visibly rather than silently resolving to "now".
        if start_reference is None:
            return value
        base = start_reference
    else:  # pragma: no cover — regex is anchored to these two alternatives
        return value

    if sign is None:
        # Bare ``now`` / ``start`` — no offset.
        return base.isoformat()

    delta_by_unit = {
        "m": timedelta(minutes=int(amount)),
        "h": timedelta(hours=int(amount)),
        "d": timedelta(days=int(amount)),
    }
    delta = delta_by_unit[unit.lower()]
    if sign == "-":
        delta = -delta
    return (base + delta).isoformat()


class CalendarActionStep(BaseModel):
    action_type: Literal[ActionType.CALENDAR_CREATE_EVENT] = ActionType.CALENDAR_CREATE_EVENT
    step_id: UUID = Field(default_factory=uuid4)
    step_order: int
    name: str
    calendar_id: str
    title_template: str
    start_mapping: str  # JSONPath ref to a datetime in prior step output
    end_mapping: str
    input_mapping: dict[str, str] = {}

    def validate_step(self) -> None:
        if not self.calendar_id:
            raise ValueError("calendar_id is required")
        if not self.title_template:
            raise ValueError("title_template is required")


class CalendarCreateEventAction(BaseAction):
    """Create an event on the user's Google Calendar.

    Behaviour depends on the runtime state:

    * Server has Google OAuth credentials configured (``GOOGLE_CLIENT_ID``
      + ``GOOGLE_CLIENT_SECRET``) **and** the workflow's owner has linked
      a Google account via ``/api/connectors/google/authorize`` →
      call the real Google Calendar API and return the created event.
    * Otherwise → fall back to the original mock behaviour so the demo
      workflows still run end-to-end without any external setup.

    The ``owner_name`` input key is populated by
    ``app.execution.step_runner.build_execution_inputs`` using the
    workflow's ``owner_name`` column, which is how we resolve whose
    tokens to load.
    """

    schema = ActionSchema(
        id="calendar_create_event",
        name="Create Calendar Event",
        description="Creates an event on the configured external calendar",
        connector_id="google_calendar",
        config_fields=[
            {"name": "calendar_id", "type": "string", "required": True},
            {"name": "title", "type": "string", "required": True},
            {"name": "start", "type": "datetime", "required": True},
            {"name": "end", "type": "datetime", "required": True},
        ],
    )

    async def execute(self, inputs: dict) -> dict:
        """Try the real Google Calendar; otherwise fall back to the mock."""
        from app.connectors import google_calendar as gcal

        # Resolve relative-time tokens (``now`` / ``now+30m`` / ``start+30m``)
        # on a consistent clock so a single call to execute sees the
        # same "now" for both fields even if ``datetime.now`` would tick
        # between them. We mutate a shallow copy so downstream mock /
        # real paths both see the resolved values.
        clock = datetime.now(UTC)
        start_resolved = _resolve_time_token(
            str(inputs.get("start") or ""), clock=clock
        )
        try:
            start_ref = datetime.fromisoformat(start_resolved) if start_resolved else None
        except ValueError:
            start_ref = None
        end_resolved = _resolve_time_token(
            str(inputs.get("end") or ""),
            start_reference=start_ref,
            clock=clock,
        )
        inputs = {**inputs, "start": start_resolved, "end": end_resolved}

        owner_name = inputs.get("owner_name")
        mock_event = self._mock_event(inputs)

        if not owner_name or not gcal.is_configured():
            return mock_event

        # Defer DB imports so the action module stays cheap to import for
        # tests that never touch the DB.
        from app.db.session import new_session

        session = new_session()
        try:
            try:
                created = gcal.create_event(
                    session,
                    owner_name,
                    calendar_id=inputs["calendar_id"],
                    title=str(inputs.get("title") or ""),
                    start=str(inputs.get("start") or ""),
                    end=str(inputs.get("end") or ""),
                )
                session.commit()
            except gcal.GoogleCalendarNotConnected:
                session.rollback()
                mock_event["note"] = "fallback_mock_user_not_connected"
                return mock_event
            except Exception:  # noqa: BLE001 — propagate to engine as step failure
                session.rollback()
                raise
        finally:
            session.close()

        return {
            "status": "created",
            "calendar_id": created.get("organizer", {}).get("email")
                or inputs["calendar_id"],
            "event": {
                "id": created.get("id"),
                "title": created.get("summary"),
                "start": (created.get("start") or {}).get("dateTime"),
                "end": (created.get("end") or {}).get("dateTime"),
                "html_link": created.get("htmlLink"),
            },
            "source": "google_calendar",
        }

    @staticmethod
    def _mock_event(inputs: dict) -> dict:
        return {
            "status": "created",
            "calendar_id": inputs.get("calendar_id"),
            "event": {
                "title": inputs.get("title"),
                "start": inputs.get("start"),
                "end": inputs.get("end"),
            },
            "source": "mock",
        }
