from abc import ABC, abstractmethod
from datetime import datetime

from app.trigger.recurrence import RecurrenceRule
from app.trigger.trigger import TriggerSpec, TriggerType
from app.trigger.triggerConfig import TimeTriggerConfig, WebhookTriggerConfig


class TriggerFactory(ABC):
    @abstractmethod
    def create(self, spec: TriggerSpec) -> TimeTriggerConfig | WebhookTriggerConfig:
        ...


class TimeTriggerFactory(TriggerFactory):
    def create(self, spec: TriggerSpec) -> TimeTriggerConfig:
        raw = spec.parameters.get("trigger_at")
        if not raw:
            raise ValueError("trigger_at is required")
        trigger_at = datetime.fromisoformat(str(raw))
        if trigger_at.tzinfo is None:
            raise ValueError("trigger_at must be timezone-aware (include UTC offset)")

        recurrence: RecurrenceRule | None = None
        raw_rec = spec.parameters.get("recurrence")
        if raw_rec:
            recurrence = RecurrenceRule(**raw_rec)

        config = TimeTriggerConfig(
            trigger_at=trigger_at,
            timezone=spec.parameters.get("timezone", "UTC"),
            recurrence=recurrence,
        )
        config.validate_config()
        return config


class WebhookTriggerFactory(TriggerFactory):
    def create(self, spec: TriggerSpec) -> WebhookTriggerConfig:
        config = WebhookTriggerConfig(
            path=spec.parameters.get("path", ""),
            method=spec.parameters.get("method", "POST"),
            secret_ref=spec.parameters.get("secret_ref", ""),
            event_filter=spec.parameters.get("event_filter", ""),
            header_filters=spec.parameters.get("header_filters", {}),
        )
        config.validate_config()
        return config


# Registry of factories
TRIGGER_FACTORIES: dict[TriggerType, TriggerFactory] = {
    TriggerType.TIME: TimeTriggerFactory(),
    TriggerType.WEBHOOK: WebhookTriggerFactory(),
}
