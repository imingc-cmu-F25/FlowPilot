"""Tests for trigger configs, factories, and runtime evaluators."""

import asyncio
import pytest

from app.trigger.trigger import (
    ScheduleTriggerConfig,
    ScheduleTriggerFactory,
    ScheduleTrigger,
    TriggerSpec,
    TriggerType,
    TRIGGER_FACTORIES,
    WebhookTriggerConfig,
    WebhookTriggerFactory,
    WebhookTrigger,
)


# ── ScheduleTriggerConfig ─────────────────────────────────────────────────────

class TestScheduleTriggerConfig:
    def test_valid_config_passes_validation(self):
        cfg = ScheduleTriggerConfig(cron_expression="0 9 * * *")
        cfg.validate_config()  # should not raise

    def test_defaults_timezone_to_utc(self):
        cfg = ScheduleTriggerConfig(cron_expression="0 9 * * *")
        assert cfg.timezone == "UTC"

    def test_custom_timezone_stored(self):
        cfg = ScheduleTriggerConfig(cron_expression="0 9 * * *", timezone="US/Eastern")
        assert cfg.timezone == "US/Eastern"

    def test_empty_cron_raises_on_validate(self):
        cfg = ScheduleTriggerConfig(cron_expression="")
        with pytest.raises(ValueError, match="cron_expression is required"):
            cfg.validate_config()

    def test_type_discriminator_is_schedule(self):
        cfg = ScheduleTriggerConfig(cron_expression="* * * * *")
        assert cfg.type == TriggerType.SCHEDULE

    def test_trigger_id_auto_generated(self):
        cfg1 = ScheduleTriggerConfig(cron_expression="* * * * *")
        cfg2 = ScheduleTriggerConfig(cron_expression="* * * * *")
        assert cfg1.trigger_id != cfg2.trigger_id


# ── WebhookTriggerConfig ──────────────────────────────────────────────────────

class TestWebhookTriggerConfig:
    def test_valid_config_passes_validation(self):
        cfg = WebhookTriggerConfig(path="/hooks/my-workflow")
        cfg.validate_config()  # should not raise

    def test_empty_path_raises(self):
        cfg = WebhookTriggerConfig(path="")
        with pytest.raises(ValueError, match="path is required"):
            cfg.validate_config()

    def test_path_without_leading_slash_raises(self):
        cfg = WebhookTriggerConfig(path="hooks/bad")
        with pytest.raises(ValueError, match="path must start with /"):
            cfg.validate_config()

    def test_type_discriminator_is_webhook(self):
        cfg = WebhookTriggerConfig(path="/hooks/x")
        assert cfg.type == TriggerType.WEBHOOK

    def test_optional_fields_default_to_empty_string(self):
        cfg = WebhookTriggerConfig(path="/hooks/x")
        assert cfg.secret_ref == ""
        assert cfg.event_filter == ""

    def test_optional_fields_stored_when_provided(self):
        cfg = WebhookTriggerConfig(path="/hooks/x", secret_ref="my-secret", event_filter="push")
        assert cfg.secret_ref == "my-secret"
        assert cfg.event_filter == "push"


# ── TriggerFactory ────────────────────────────────────────────────────────────

class TestScheduleTriggerFactory:
    factory = ScheduleTriggerFactory()

    def test_creates_schedule_config(self):
        spec = TriggerSpec(type=TriggerType.SCHEDULE, parameters={"cron": "0 8 * * MON"})
        cfg = self.factory.create(spec)
        assert isinstance(cfg, ScheduleTriggerConfig)
        assert cfg.cron_expression == "0 8 * * MON"

    def test_defaults_timezone_when_not_in_parameters(self):
        spec = TriggerSpec(type=TriggerType.SCHEDULE, parameters={"cron": "0 8 * * *"})
        cfg = self.factory.create(spec)
        assert cfg.timezone == "UTC"

    def test_passes_timezone_from_parameters(self):
        spec = TriggerSpec(
            type=TriggerType.SCHEDULE,
            parameters={"cron": "0 8 * * *", "timezone": "Europe/Berlin"},
        )
        cfg = self.factory.create(spec)
        assert cfg.timezone == "Europe/Berlin"

    def test_missing_cron_raises_value_error(self):
        spec = TriggerSpec(type=TriggerType.SCHEDULE, parameters={})
        with pytest.raises(ValueError, match="cron_expression is required"):
            self.factory.create(spec)


class TestWebhookTriggerFactory:
    factory = WebhookTriggerFactory()

    def test_creates_webhook_config(self):
        spec = TriggerSpec(type=TriggerType.WEBHOOK, parameters={"path": "/hooks/gh"})
        cfg = self.factory.create(spec)
        assert isinstance(cfg, WebhookTriggerConfig)
        assert cfg.path == "/hooks/gh"

    def test_passes_optional_fields(self):
        spec = TriggerSpec(
            type=TriggerType.WEBHOOK,
            parameters={"path": "/hooks/gh", "secret_ref": "gh-secret", "event_filter": "push"},
        )
        cfg = self.factory.create(spec)
        assert cfg.secret_ref == "gh-secret"
        assert cfg.event_filter == "push"

    def test_missing_path_raises_value_error(self):
        spec = TriggerSpec(type=TriggerType.WEBHOOK, parameters={})
        with pytest.raises(ValueError, match="path is required"):
            self.factory.create(spec)

    def test_path_without_slash_raises_value_error(self):
        spec = TriggerSpec(type=TriggerType.WEBHOOK, parameters={"path": "no-slash"})
        with pytest.raises(ValueError, match="path must start with /"):
            self.factory.create(spec)


# ── TRIGGER_FACTORIES registry ────────────────────────────────────────────────

class TestTriggerFactoriesRegistry:
    def test_schedule_factory_is_registered(self):
        assert TriggerType.SCHEDULE in TRIGGER_FACTORIES
        assert isinstance(TRIGGER_FACTORIES[TriggerType.SCHEDULE], ScheduleTriggerFactory)

    def test_webhook_factory_is_registered(self):
        assert TriggerType.WEBHOOK in TRIGGER_FACTORIES
        assert isinstance(TRIGGER_FACTORIES[TriggerType.WEBHOOK], WebhookTriggerFactory)

    def test_all_trigger_types_are_registered(self):
        for t in TriggerType:
            assert t in TRIGGER_FACTORIES, f"Missing factory for {t}"


# ── JSON round-trip via discriminated union ───────────────────────────────────

class TestTriggerConfigRoundTrip:
    def test_schedule_config_serializes_and_restores(self):
        from typing import Annotated, Union
        from pydantic import BaseModel, Field

        # Use the same union that WorkflowDefinition uses
        TriggerConfig = Annotated[
            Union[ScheduleTriggerConfig, WebhookTriggerConfig],
            Field(discriminator="type"),
        ]

        class Wrapper(BaseModel):
            trigger: TriggerConfig  # type: ignore[valid-type]

        cfg = ScheduleTriggerConfig(cron_expression="0 9 * * *")
        w = Wrapper(trigger=cfg)
        restored = Wrapper.model_validate(w.model_dump(mode="json"))
        assert isinstance(restored.trigger, ScheduleTriggerConfig)
        assert restored.trigger.cron_expression == "0 9 * * *"

    def test_webhook_config_serializes_and_restores(self):
        from typing import Annotated, Union
        from pydantic import BaseModel, Field

        TriggerConfig = Annotated[
            Union[ScheduleTriggerConfig, WebhookTriggerConfig],
            Field(discriminator="type"),
        ]

        class Wrapper(BaseModel):
            trigger: TriggerConfig  # type: ignore[valid-type]

        cfg = WebhookTriggerConfig(path="/hooks/test")
        w = Wrapper(trigger=cfg)
        restored = Wrapper.model_validate(w.model_dump(mode="json"))
        assert isinstance(restored.trigger, WebhookTriggerConfig)
        assert restored.trigger.path == "/hooks/test"


# ── Runtime evaluators ────────────────────────────────────────────────────────

class TestScheduleTriggerEvaluate:
    def test_every_minute_cron_returns_true(self):
        trigger = ScheduleTrigger()
        cfg = ScheduleTriggerConfig(cron_expression="* * * * *")
        result = asyncio.run(trigger.evaluate({"config": cfg}))
        assert result is True

    def test_evaluate_returns_bool(self):
        trigger = ScheduleTrigger()
        cfg = ScheduleTriggerConfig(cron_expression="* * * * *")
        result = asyncio.run(trigger.evaluate({"config": cfg}))
        assert isinstance(result, bool)

    def test_schema_id_is_schedule(self):
        assert ScheduleTrigger.schema.id == "schedule"


class TestWebhookTriggerEvaluate:
    def test_always_returns_true(self):
        trigger = WebhookTrigger()
        result = asyncio.run(trigger.evaluate({}))
        assert result is True

    def test_schema_id_is_webhook(self):
        assert WebhookTrigger.schema.id == "webhook"
