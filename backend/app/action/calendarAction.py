from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.action.base import ActionType


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

