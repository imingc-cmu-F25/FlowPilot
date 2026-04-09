# action/registry.py  &  trigger/registry.py  (same pattern)

from app.action.Action import BaseAction
from app.action.Action import SendEmailAction

class ActionRegistry:
    _actions: dict[str, type[BaseAction]] = {}

    @classmethod
    def register(cls, action_cls: type[BaseAction]):
        cls._actions[action_cls.schema.id] = action_cls
        return action_cls

    @classmethod
    def get(cls, action_id: str) -> type[BaseAction]:
        return cls._actions[action_id]

    @classmethod
    def list_schemas(cls) -> list:
        return [a.schema for a in cls._actions.values()]

# Auto-register on import
ActionRegistry.register(SendEmailAction)