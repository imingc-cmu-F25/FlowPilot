# trigger/base.py

from abc import ABC, abstractmethod

from pydantic import BaseModel


class TriggerSchema(BaseModel):
    """Describes a trigger type so the frontend can render its config form."""
    id: str
    name: str
    description: str
    config_fields: list[dict]  # [{name, type, required, default, options}]

class BaseTrigger(ABC):
    schema: TriggerSchema

    @abstractmethod
    async def evaluate(self, context: dict) -> bool:
        """Return True when this trigger should fire."""
        ...

# trigger/schedule.py
class ScheduleTrigger(BaseTrigger):
    schema = TriggerSchema(
        id="schedule",
        name="Schedule",
        description="Fires on a cron expression",
        config_fields=[
            {"name": "cron", "type": "string", "required": True}
        ],
    )

    async def evaluate(self, context: dict) -> bool:
        # cron matching logic
        ...

# trigger/webhook.py
class WebhookTrigger(BaseTrigger):
    schema = TriggerSchema(
        id="webhook",
        name="Webhook",
        description="Fires when an HTTP request is received",
        config_fields=[
            {"name": "path", "type": "string", "required": True},
            {"name": "method", "type": "string", "required": False, "default": "POST"},
        ],
    )
    ...