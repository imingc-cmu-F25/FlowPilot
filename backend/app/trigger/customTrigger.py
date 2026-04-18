from app.trigger.trigger import BaseTrigger, TriggerSchema
from app.trigger.triggerConfig import CustomTriggerConfig


class CustomTrigger(BaseTrigger):
    schema = TriggerSchema(
        id="custom",
        name="Custom",
        description="Fires when a simple user-defined condition evaluates to true",
        config_fields=[
            {
                "name": "condition",
                "type": "string",
                "required": True,
                "description": "Simple condition expression evaluated against runtime context",
            },
            {
                "name": "source",
                "type": "string",
                "required": False,
                "default": "event_payload",
                "description": "Context source for condition evaluation",
            },
            {
                "name": "description",
                "type": "string",
                "required": False,
                "default": "",
                "description": "Human-readable explanation of this custom trigger",
            },
        ],
    )

    async def evaluate(self, context: dict) -> bool:
        config: CustomTriggerConfig = context["config"]
        cond = config.condition.strip().lower()
        if cond in {"true", "1", "yes"}:
            return True
        if cond in {"false", "0", "no"}:
            return False
        return False