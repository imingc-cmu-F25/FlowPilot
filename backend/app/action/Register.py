from app.action.action import BaseAction, HttpRequestAction, SendEmailAction


class ActionRegistry:
    _actions: dict[str, type[BaseAction]] = {}

    @classmethod
    def register(cls, action_cls: type[BaseAction]) -> type[BaseAction]:
        cls._actions[action_cls.schema.id] = action_cls
        return action_cls

    @classmethod
    def get(cls, action_id: str) -> type[BaseAction]:
        if action_id not in cls._actions:
            raise KeyError(f"No action registered for id: {action_id!r}")
        return cls._actions[action_id]

    @classmethod
    def list_schemas(cls) -> list:
        return [a.schema for a in cls._actions.values()]


ActionRegistry.register(SendEmailAction)
ActionRegistry.register(HttpRequestAction)
