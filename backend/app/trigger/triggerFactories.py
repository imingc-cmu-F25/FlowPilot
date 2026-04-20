from abc import ABC, abstractmethod
from datetime import datetime

from app.trigger.recurrence import RecurrenceRule
from app.trigger.trigger import TriggerSpec, TriggerType
from app.trigger.triggerConfig import (
    CalendarEventTriggerConfig,
    CustomTriggerConfig,
    TimeTriggerConfig,
    TriggerConfig,
    WebhookTriggerConfig,
)


class TriggerFactory(ABC):
    @abstractmethod
    def create(
        self, spec: TriggerSpec
    ) -> (
        TimeTriggerConfig
        | WebhookTriggerConfig
        | CustomTriggerConfig
        | CalendarEventTriggerConfig
    ):
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

class CustomTriggerFactory(TriggerFactory):
    def create(self, spec: TriggerSpec) -> CustomTriggerConfig:
        config = CustomTriggerConfig(
            condition=spec.parameters.get("condition", ""),
            source=spec.parameters.get("source", "event_payload"),
            description=spec.parameters.get("description", ""),
            timezone=spec.parameters.get("timezone", "UTC") or "UTC",
        )
        config.validate_config()
        return config


class CalendarEventTriggerFactory(TriggerFactory):
    def create(self, spec: TriggerSpec) -> CalendarEventTriggerConfig:
        config = CalendarEventTriggerConfig(
            calendar_id=spec.parameters.get("calendar_id", "primary") or "primary",
            title_contains=spec.parameters.get("title_contains", "") or "",
            dedup_seconds=int(spec.parameters.get("dedup_seconds", 60)),
        )
        config.validate_config()
        return config


# Keep all trigger constructors in one registry for easy extension.
TRIGGER_FACTORIES: dict[TriggerType, TriggerFactory] = {
    TriggerType.TIME: TimeTriggerFactory(),
    TriggerType.WEBHOOK: WebhookTriggerFactory(),
    TriggerType.CUSTOM: CustomTriggerFactory(),
    TriggerType.CALENDAR_EVENT: CalendarEventTriggerFactory(),
    # Add more trigger factories here
}

# Single entry point for trigger config construction.
def build_trigger_config(spec: TriggerSpec) -> TriggerConfig:
    factory = TRIGGER_FACTORIES.get(spec.type)
    if factory is None:
        raise ValueError(f"No factory registered for trigger type: {spec.type}")

    return factory.create(spec)