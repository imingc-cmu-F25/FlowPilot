from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.action.base import ActionSchema, ActionType, BaseAction


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
