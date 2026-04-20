"""``Calendar.ListUpcoming`` action.

Reads upcoming events from the local ``cached_calendar_events`` table —
the cache is refreshed in the background by ``connectors.sync_google_calendars``
so this action never touches the Google API at runtime. That's the whole
point of the local-cache design: workflow latency + reliability stop
depending on a flaky third-party.

Output shape (stable for downstream steps):
    {
        "status": "ok",
        "count": <int>,
        "events": [
            {
                "id": str,
                "calendar_id": str,
                "title": str,
                "start": iso | None,
                "end": iso | None,
                "html_link": str | None,
            },
            ...
        ],
        "agenda_text": str,  # pre-rendered human-readable bullet list,
                             # exactly what a "Send Email" step wants to
                             # drop into its body via
                             # ``{{previous_output.agenda_text}}``.
        "source": "cache" | "empty",
    }
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.action.base import ActionSchema, ActionType, BaseAction


class CalendarListUpcomingActionStep(BaseModel):
    action_type: Literal[ActionType.CALENDAR_LIST_UPCOMING] = (
        ActionType.CALENDAR_LIST_UPCOMING
    )
    step_id: UUID = Field(default_factory=uuid4)
    step_order: int
    name: str
    calendar_id: str = "primary"
    max_results: int = 10
    title_contains: str = ""  # optional filter; empty means no filter
    # Upper bound on how far ahead to look, in hours. 0 = no cap (just
    # rely on max_results). The most common useful values are 24
    # ("today + rollover") and 168 ("this week").
    window_hours: int = 0

    def validate_step(self) -> None:
        if self.max_results <= 0 or self.max_results > 100:
            raise ValueError("max_results must be between 1 and 100")
        if self.window_hours < 0 or self.window_hours > 24 * 365:
            raise ValueError("window_hours must be between 0 and 8760 (1 year)")


def _format_agenda(events: list[dict]) -> str:
    """Render a bullet list like ``- Mon Apr 21, 09:00 · Standup``.

    Used as the default ``agenda_text`` output so workflow authors can
    get a useful email body with a single ``{{previous_output.agenda_text}}``
    placeholder. Keep it plain ASCII so it drops cleanly into either a
    text/plain SMTP body or a terminal print without extra encoding
    quirks. Callers who want HTML can iterate ``events`` themselves.
    """
    if not events:
        return "(no upcoming events)"

    lines: list[str] = []
    for ev in events:
        title = ev.get("title") or "(untitled)"
        start = ev.get("start")
        if start:
            try:
                dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                when = dt.strftime("%a %b %d, %H:%M")
            except ValueError:
                when = start
        else:
            when = "no start time"
        lines.append(f"- {when} · {title}")
    return "\n".join(lines)


class CalendarListUpcomingAction(BaseAction):
    """List upcoming calendar events from the local cache."""

    schema = ActionSchema(
        id="calendar_list_upcoming",
        name="List Upcoming Calendar Events",
        description=(
            "Read upcoming events from the user's cached Google Calendar. "
            "Only returns events that have not ended yet."
        ),
        connector_id="google_calendar",
        config_fields=[
            {"name": "calendar_id", "type": "string", "required": False},
            {"name": "max_results", "type": "integer", "required": False},
            {"name": "title_contains", "type": "string", "required": False},
            {"name": "window_hours", "type": "integer", "required": False},
        ],
    )

    async def execute(self, inputs: dict) -> dict:
        owner_name = inputs.get("owner_name")
        max_results = int(inputs.get("max_results") or 10)
        calendar_id = str(inputs.get("calendar_id") or "primary")
        title_contains = str(inputs.get("title_contains") or "").strip()
        window_hours = int(inputs.get("window_hours") or 0)

        if not owner_name:
            # Engine always injects owner_name for every step, so this is
            # really only reachable from direct unit tests. Return an
            # empty-but-valid envelope rather than raising so callers can
            # still iterate the "events" key.
            return {
                "status": "ok",
                "count": 0,
                "events": [],
                "agenda_text": "(no upcoming events)",
                "source": "empty",
            }

        # Import late so importing this module in tests that never touch
        # the DB stays cheap (mirrors the pattern in calendarAction.py).
        from app.connectors.repo import CachedCalendarEventRepository
        from app.db.session import new_session

        session = new_session()
        try:
            now = datetime.now(UTC)
            max_start = (
                now + timedelta(hours=window_hours) if window_hours > 0 else None
            )
            rows = CachedCalendarEventRepository(session).list_for_user(
                owner_name,
                limit=max_results,
                upcoming_only=True,
                now=now,
                max_start=max_start,
            )
        finally:
            session.close()

        events: list[dict] = []
        for r in rows:
            if calendar_id and calendar_id != "primary" and r.calendar_id != calendar_id:
                # Keep "primary" permissive: most demo users haven't set a
                # calendar_id on the step and the cache already filters to
                # primary by default during sync.
                continue
            if title_contains and title_contains.lower() not in (r.title or "").lower():
                continue
            events.append(
                {
                    "id": r.provider_event_id,
                    "calendar_id": r.calendar_id,
                    "title": r.title,
                    "start": r.start.isoformat() if r.start else None,
                    "end": r.end.isoformat() if r.end else None,
                    "html_link": r.html_link,
                }
            )

        return {
            "status": "ok",
            "count": len(events),
            "events": events,
            "agenda_text": _format_agenda(events),
            "source": "cache",
        }
