from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Annotated, Literal, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ActionType(StrEnum):
    HTTP_REQUEST = "http_request"
    SEND_EMAIL = "send_email"
    CALENDAR_CREATE_EVENT = "calendar_create_event"


# ActionStep hierarchy
# Each concrete step uses a Literal discriminator so Pydantic can deserialize
# a list[ActionStep] field polymorphically from JSON.

class HttpRequestActionStep(BaseModel):
    action_type: Literal[ActionType.HTTP_REQUEST] = ActionType.HTTP_REQUEST
    step_id: UUID = Field(default_factory=uuid4)
    step_order: int
    name: str
    method: str = "GET"
    url_template: str  # supports {{variable}} placeholders
    headers: dict[str, str] = {}
    input_mapping: dict[str, str] = {}  # param name → JSONPath into prior output

    def validate_step(self) -> None:
        if not self.url_template:
            raise ValueError("url_template is required")
        if self.method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            raise ValueError(f"Unsupported HTTP method: {self.method}")


class SendEmailActionStep(BaseModel):
    action_type: Literal[ActionType.SEND_EMAIL] = ActionType.SEND_EMAIL
    step_id: UUID = Field(default_factory=uuid4)
    step_order: int
    name: str
    to_template: str
    subject_template: str
    body_template: str
    input_mapping: dict[str, str] = {}

    def validate_step(self) -> None:
        if not self.to_template:
            raise ValueError("to_template is required")
        if not self.subject_template:
            raise ValueError("subject_template is required")


class CalendarCreateEventActionStep(BaseModel):
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


# Discriminated union, used as the type annotation for WorkflowDefinition.steps
ActionStep = Annotated[
    Union[HttpRequestActionStep, SendEmailActionStep, CalendarCreateEventActionStep],
    Field(discriminator="action_type"),
]


# The stored configuration for a workflow step at runtime
class StepSpec(BaseModel):
    """What the client sends when adding an action step."""
    action_type: ActionType
    name: str
    step_order: int
    parameters: dict = {}


# Action factories
_STEP_CONSTRUCTORS: dict[ActionType, type] = {
    ActionType.HTTP_REQUEST: HttpRequestActionStep,
    ActionType.SEND_EMAIL: SendEmailActionStep,
    ActionType.CALENDAR_CREATE_EVENT: CalendarCreateEventActionStep,
}


class ActionStepFactory:
    @classmethod
    def create(
        cls, spec: StepSpec
    ) -> HttpRequestActionStep | SendEmailActionStep | CalendarCreateEventActionStep:
        step_cls = _STEP_CONSTRUCTORS.get(spec.action_type)
        if step_cls is None:
            raise ValueError(f"Unknown action type: {spec.action_type}")
        step = step_cls(name=spec.name, step_order=spec.step_order, **spec.parameters)
        step.validate_step()
        return step

    @classmethod
    def register(cls, action_type: ActionType, step_cls: type) -> None:
        """Extend the factory with a new action step type at runtime."""
        _STEP_CONSTRUCTORS[action_type] = step_cls


# Action schemas
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


class SendEmailAction(BaseAction):
    schema = ActionSchema(
        id="send_email",
        name="Send Email",
        description="Sends an email via SMTP connector",
        connector_id="smtp",
        config_fields=[
            {"name": "to", "type": "string", "required": True},
            {"name": "subject", "type": "string", "required": True},
            {"name": "body", "type": "string", "required": True},
        ],
    )

    async def execute(self, inputs: dict) -> dict:
        # TODO: wire SMTP host/credentials from settings + connector
        # import smtplib; msg = EmailMessage(); smtplib.SMTP(...).send_message(msg)
        return {"status": "sent", "to": inputs.get("to")}


class HttpRequestAction(BaseAction):
    schema = ActionSchema(
        id="http_request",
        name="HTTP Request",
        description="Makes an HTTP request to an external URL",
        config_fields=[
            {"name": "method", "type": "string", "required": True},
            {"name": "url", "type": "string", "required": True},
            {"name": "headers", "type": "object", "required": False},
            {"name": "body", "type": "string", "required": False},
        ],
    )

    async def execute(self, inputs: dict) -> dict:
        import httpx  # pip install httpx
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=inputs.get("method", "GET"),
                url=inputs["url"],
                headers=inputs.get("headers", {}),
                content=inputs.get("body"),
            )
        return {"status_code": response.status_code, "body": response.text}
