# action/registry.py  &  trigger/registry.py  (same pattern)

from app.trigger.Trigger import BaseTrigger, ScheduleTrigger


class TriggerRegistry:
    _actions: dict[str, type[BaseTrigger]] = {}

    @classmethod
    def register(cls, action_cls: type[BaseTrigger]):
        cls._actions[action_cls.schema.id] = action_cls
        return action_cls

    @classmethod
    def get(cls, action_id: str) -> type[BaseTrigger]:
        return cls._actions[action_id]

    @classmethod
    def list_schemas(cls) -> list:
        return [a.schema for a in cls._actions.values()]

# Auto-register on import
TriggerRegistry.register(ScheduleTrigger)