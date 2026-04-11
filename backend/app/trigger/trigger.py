from abc import ABC, abstractmethod
from enum import StrEnum

from pydantic import BaseModel


class TriggerType(StrEnum):
    TIME = "time"
    WEBHOOK = "webhook"


# API input
class TriggerSpec(BaseModel):
    """What the client sends when configuring a trigger."""
    type: TriggerType
    parameters: dict = {}


# Trigger schemas
class TriggerSchema(BaseModel):
    id: str
    name: str
    description: str
    config_fields: list[dict]


# Base Trigger
class BaseTrigger(ABC):
    schema: TriggerSchema

    @abstractmethod
    async def evaluate(self, context: dict) -> bool:
        """Return True when this trigger should fire."""
        ...
