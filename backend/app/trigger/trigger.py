from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Literal, Union
from uuid import UUID, uuid4
from croniter import croniter

from pydantic import BaseModel, Field


class TriggerType(StrEnum):
    SCHEDULE = "schedule"
    WEBHOOK = "webhook"


# TriggerConfig hierarchy
# Uses Literal discriminator fields so Pydantic can deserialize polymorphically

class ScheduleTriggerConfig(BaseModel):
    type: Literal[TriggerType.SCHEDULE] = TriggerType.SCHEDULE
    trigger_id: UUID = Field(default_factory=uuid4)
    cron_expression: str
    timezone: str = "UTC"

    def validate_config(self) -> None:
        if not self.cron_expression:
            raise ValueError("cron_expression is required")


class WebhookTriggerConfig(BaseModel):
    type: Literal[TriggerType.WEBHOOK] = TriggerType.WEBHOOK
    trigger_id: UUID = Field(default_factory=uuid4)
    path: str
    secret_ref: str = ""
    event_filter: str = ""

    def validate_config(self) -> None:
        if not self.path:
            raise ValueError("path is required")
        if not self.path.startswith("/"):
            raise ValueError("path must start with /")


# Discriminated union
# Used as the type annotation for WorkflowDefinition.trigger
TriggerConfig = Annotated[
    Union[ScheduleTriggerConfig, WebhookTriggerConfig],
    Field(discriminator="type"),
]


# API input before factory resolution
class TriggerSpec(BaseModel):
    """What the client sends when configuring a trigger."""
    type: TriggerType
    parameters: dict = {}


# Trigger factories
class TriggerFactory(ABC):
    @abstractmethod
    def create(self, spec: TriggerSpec) -> ScheduleTriggerConfig | WebhookTriggerConfig:
        ...


class ScheduleTriggerFactory(TriggerFactory):
    def create(self, spec: TriggerSpec) -> ScheduleTriggerConfig:
        config = ScheduleTriggerConfig(
            cron_expression=spec.parameters.get("cron", ""),
            timezone=spec.parameters.get("timezone", "UTC"),
        )
        config.validate_config()
        return config


class WebhookTriggerFactory(TriggerFactory):
    def create(self, spec: TriggerSpec) -> WebhookTriggerConfig:
        config = WebhookTriggerConfig(
            path=spec.parameters.get("path", ""),
            secret_ref=spec.parameters.get("secret_ref", ""),
            event_filter=spec.parameters.get("event_filter", ""),
        )
        config.validate_config()
        return config


# Registry of factories, indexed by TriggerType
TRIGGER_FACTORIES: dict[TriggerType, TriggerFactory] = {
    TriggerType.SCHEDULE: ScheduleTriggerFactory(),
    TriggerType.WEBHOOK: WebhookTriggerFactory(),
}


# Trigger schema
class TriggerSchema(BaseModel):
    id: str
    name: str
    description: str
    config_fields: list[dict]


class BaseTrigger(ABC):
    schema: TriggerSchema

    @abstractmethod
    async def evaluate(self, context: dict) -> bool:
        """Return True when this trigger should fire."""
        ...


class ScheduleTrigger(BaseTrigger):
    """
    Fires on the schedule defined by a cron expression.
    The engine evaluates the trigger every minute.
    """
    schema = TriggerSchema(
        id="schedule",
        name="Schedule",
        description="Fires on a cron expression",
        config_fields=[
            {"name": "cron", "type": "string", "required": True},
            {"name": "timezone", "type": "string", "required": False, "default": "UTC"},
        ],
    )

    async def evaluate(self, context: dict) -> bool:
        """Evaluate the cron expression against the current time."""
        config: ScheduleTriggerConfig = context["config"]
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        prev = croniter(config.cron_expression, now).get_prev(datetime)
        return (now - prev).total_seconds() < 60


class WebhookTrigger(BaseTrigger):
    """
    Fires when an HTTP request is received at the configured path.
    The HTTP handler evaluates the trigger and fires the engine directly.
    """
    schema = TriggerSchema(
        id="webhook",
        name="Webhook",
        description="Fires when an HTTP request is received at the configured path",
        config_fields=[
            {"name": "path", "type": "string", "required": True},
            {"name": "secret_ref", "type": "string", "required": False, "default": ""},
            {"name": "event_filter", "type": "string", "required": False, "default": ""},
        ],
    )

    async def evaluate(self, _context: dict) -> bool:
        # Webhooks are push-driven, the HTTP handler fires the engine directly
        return True
