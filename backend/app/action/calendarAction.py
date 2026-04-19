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
    """
    Creates an event on an external calendar.

    The real Google Calendar integration will live in app.connectors.calendar;
    this implementation performs a local no-op so workflows using this action
    can still run end-to-end. It returns an event record the next step can
    reference through the usual context mechanism.
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
        """
        @param inputs: A dict with keys "calendar_id", "title", "start", "end"
        @return: A dict representing the (mock) created event
        """
        return {
            "status": "created",
            "calendar_id": inputs["calendar_id"],
            "event": {
                "title": inputs.get("title"),
                "start": inputs.get("start"),
                "end": inputs.get("end"),
            },
        }
