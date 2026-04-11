from app.trigger.trigger import BaseTrigger
from app.trigger.timeTrigger import TimeTrigger
from app.trigger.webhookTrigger import WebhookTrigger


class TriggerRegistry:
    _triggers: dict[str, type[BaseTrigger]] = {}

    @classmethod
    def register(cls, trigger_cls: type[BaseTrigger]) -> type[BaseTrigger]:
        cls._triggers[trigger_cls.schema.id] = trigger_cls
        return trigger_cls

    @classmethod
    def get(cls, trigger_id: str) -> type[BaseTrigger]:
        if trigger_id not in cls._triggers:
            raise KeyError(f"No trigger registered for id: {trigger_id!r}")
        return cls._triggers[trigger_id]

    @classmethod
    def list_schemas(cls) -> list:
        return [t.schema for t in cls._triggers.values()]


TriggerRegistry.register(TimeTrigger)
TriggerRegistry.register(WebhookTrigger)
