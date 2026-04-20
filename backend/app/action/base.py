"""Shared base types for the action module — no intra-package imports here."""

from abc import ABC, abstractmethod
from enum import StrEnum

from pydantic import BaseModel


class ActionType(StrEnum):
    HTTP_REQUEST = "http_request"
    SEND_EMAIL = "send_email"
    CALENDAR_CREATE_EVENT = "calendar_create_event"
    CALENDAR_LIST_UPCOMING = "calendar_list_upcoming"


class ActionSchema(BaseModel):
    id: str
    name: str
    description: str
    connector_id: str | None = None
    config_fields: list[dict] = []


class BaseAction(ABC):
    schema: ActionSchema

    @abstractmethod
    async def execute(self, inputs: dict) -> dict:
        """Run the action with resolved inputs; return outputs for the next step."""
        ...


class StepSpec(BaseModel):
    """What the client sends when adding an action step."""
    action_type: ActionType
    name: str
    step_order: int
    parameters: dict = {}
