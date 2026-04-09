# action/base.py

from abc import ABC, abstractmethod
from pydantic import BaseModel

class ActionSchema(BaseModel):
    id: str
    name: str
    description: str
    connector_id: str | None = None
    config_fields: list[dict]

class BaseAction(ABC):
    schema: ActionSchema

    @abstractmethod
    async def execute(self, inputs: dict) -> dict:
        """Run the action; return outputs for the next step."""
        ...

# action/send_email.py
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
        ...