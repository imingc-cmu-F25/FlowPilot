"""Tests for trigger configs, factories, and runtime evaluators."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from app.trigger.recurrence import RecurrenceFrequency, RecurrenceRule
from app.trigger.timeTrigger import TimeTrigger
from app.trigger.trigger import TriggerSpec, TriggerType
from app.trigger.triggerConfig import TimeTriggerConfig, WebhookTriggerConfig
from app.trigger.triggerFactories import (
    TRIGGER_FACTORIES,
    TimeTriggerFactory,
    WebhookTriggerFactory,
)
from app.trigger.webhookTrigger import WebhookTrigger

#  RecurrenceRule validation 
class TestRecurrenceRuleValidation:
    def test_daily_valid(self):
        rule = RecurrenceRule(frequency="daily", interval=1)
        rule.validate_rule()  # should not raise

    def test_interval_zero_raises(self):
        rule = RecurrenceRule(frequency="daily", interval=0)
        with pytest.raises(ValueError, match="interval must be >= 1"):
            rule.validate_rule()

    def test_weekly_without_days_raises(self):
        rule = RecurrenceRule(frequency="weekly")
        with pytest.raises(ValueError, match="days_of_week is required"):
            rule.validate_rule()

    def test_weekly_with_invalid_day_raises(self):
        rule = RecurrenceRule(frequency="weekly", days_of_week=[7])
        with pytest.raises(ValueError, match="Invalid days_of_week"):
            rule.validate_rule()

    def test_weekly_valid(self):
        rule = RecurrenceRule(frequency="weekly", days_of_week=[0, 4])
        rule.validate_rule()  # should not raise

    def test_custom_without_cron_raises(self):
        rule = RecurrenceRule(frequency="custom")
        with pytest.raises(ValueError, match="cron_expression is required"):
            rule.validate_rule()

    def test_custom_with_invalid_cron_raises(self):
        rule = RecurrenceRule(frequency="custom", cron_expression="not a cron")
        with pytest.raises(ValueError, match="Invalid cron expression"):
            rule.validate_rule()

    def test_custom_valid(self):
        rule = RecurrenceRule(frequency="custom", cron_expression="0 9 * * 1-5")
        rule.validate_rule()  # should not raise


#  RecurrenceRule.is_due 
class TestRecurrenceRuleIsDue:
    BASE = datetime(2026, 1, 1, 9, 0, 0, tzinfo=UTC)  # Thursday

    def test_before_start_returns_false(self):
        rule = RecurrenceRule(frequency="daily", interval=1)
        assert rule.is_due(self.BASE, self.BASE - timedelta(seconds=1)) is False

    def test_daily_at_start_is_due(self):
        rule = RecurrenceRule(frequency="daily", interval=1)
        assert rule.is_due(self.BASE, self.BASE) is True

    def test_daily_interval_2_due_on_day_2(self):
        rule = RecurrenceRule(frequency="daily", interval=2)
        now = self.BASE + timedelta(days=2)
        assert rule.is_due(self.BASE, now) is True

    def test_daily_interval_2_not_due_on_day_1(self):
        rule = RecurrenceRule(frequency="daily", interval=2)
        now = self.BASE + timedelta(days=1)
        assert rule.is_due(self.BASE, now) is False

    def test_hourly_due_every_hour(self):
        rule = RecurrenceRule(frequency="hourly", interval=1)
        now = self.BASE + timedelta(hours=3)
        assert rule.is_due(self.BASE, now) is True

    def test_minutely_due_every_minute(self):
        rule = RecurrenceRule(frequency="minutely", interval=1)
        now = self.BASE + timedelta(minutes=5)
        assert rule.is_due(self.BASE, now) is True

    def test_weekly_on_correct_day_is_due(self):
        # BASE is Thursday (weekday=3)
        rule = RecurrenceRule(frequency="weekly", days_of_week=[3])
        now = self.BASE + timedelta(weeks=1)
        assert rule.is_due(self.BASE, now) is True

    def test_weekly_on_wrong_day_not_due(self):
        # BASE is Thursday (weekday=3); check on Friday (weekday=4)
        rule = RecurrenceRule(frequency="weekly", days_of_week=[3])
        now = self.BASE + timedelta(days=1)
        assert rule.is_due(self.BASE, now) is False

    def test_weekly_interval_2_skips_odd_weeks(self):
        rule = RecurrenceRule(frequency="weekly", interval=2, days_of_week=[3])
        now = self.BASE + timedelta(weeks=1)  # week 1, should skip
        assert rule.is_due(self.BASE, now) is False

    def test_weekly_interval_2_fires_on_even_weeks(self):
        rule = RecurrenceRule(frequency="weekly", interval=2, days_of_week=[3])
        now = self.BASE + timedelta(weeks=2)  # week 2, should fire
        assert rule.is_due(self.BASE, now) is True

    def test_custom_cron_due_within_window(self):
        # "0 9 * * *" fires at 9:00 every day; BASE is 09:00, so last was just now
        rule = RecurrenceRule(frequency="custom", cron_expression="0 9 * * *")
        assert rule.is_due(self.BASE, self.BASE + timedelta(seconds=5)) is True

    def test_custom_cron_not_due_outside_window(self):
        # 10 minutes after 9:00 → last cron fire was 09:00, ~600s ago
        rule = RecurrenceRule(frequency="custom", cron_expression="0 9 * * *")
        now = self.BASE + timedelta(minutes=10)
        assert rule.is_due(self.BASE, now) is False


#  TimeTriggerConfig 
class TestTimeTriggerConfig:
    def _future(self) -> datetime:
        return datetime.now(UTC) + timedelta(hours=1)

    def test_valid_config_passes_validation(self):
        cfg = TimeTriggerConfig(trigger_at=self._future())
        cfg.validate_config()  # should not raise

    def test_defaults_timezone_to_utc(self):
        cfg = TimeTriggerConfig(trigger_at=self._future())
        assert cfg.timezone == "UTC"

    def test_custom_timezone_stored(self):
        cfg = TimeTriggerConfig(trigger_at=self._future(), timezone="US/Eastern")
        assert cfg.timezone == "US/Eastern"

    def test_naive_datetime_raises_on_validate(self):
        cfg = TimeTriggerConfig(trigger_at=datetime(2026, 5, 1, 9, 0, 0))
        with pytest.raises(ValueError, match="timezone-aware"):
            cfg.validate_config()

    def test_type_discriminator_is_time(self):
        cfg = TimeTriggerConfig(trigger_at=self._future())
        assert cfg.type == TriggerType.TIME

    def test_trigger_id_auto_generated_and_unique(self):
        cfg1 = TimeTriggerConfig(trigger_at=self._future())
        cfg2 = TimeTriggerConfig(trigger_at=self._future())
        assert cfg1.trigger_id != cfg2.trigger_id

    def test_recurrence_default_is_none(self):
        cfg = TimeTriggerConfig(trigger_at=self._future())
        assert cfg.recurrence is None

    def test_valid_recurrence_passes_validation(self):
        rule = RecurrenceRule(frequency="daily", interval=2)
        cfg = TimeTriggerConfig(trigger_at=self._future(), recurrence=rule)
        cfg.validate_config()  # should not raise

    def test_invalid_recurrence_fails_validation(self):
        rule = RecurrenceRule(frequency="weekly")  # missing days_of_week
        cfg = TimeTriggerConfig(trigger_at=self._future(), recurrence=rule)
        with pytest.raises(ValueError, match="days_of_week is required"):
            cfg.validate_config()


#  WebhookTriggerConfig 
class TestWebhookTriggerConfig:
    def test_valid_config_passes_validation(self):
        cfg = WebhookTriggerConfig(path="/hooks/my-workflow")
        cfg.validate_config()

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

    def test_default_method_is_post(self):
        cfg = WebhookTriggerConfig(path="/hooks/x")
        assert cfg.method == "POST"

    def test_invalid_method_raises(self):
        cfg = WebhookTriggerConfig(path="/hooks/x", method="PURGE")
        with pytest.raises(ValueError, match="Unsupported HTTP method"):
            cfg.validate_config()

    def test_optional_fields_default_to_empty(self):
        cfg = WebhookTriggerConfig(path="/hooks/x")
        assert cfg.secret_ref == ""
        assert cfg.event_filter == ""
        assert cfg.header_filters == {}

    def test_optional_fields_stored_when_provided(self):
        cfg = WebhookTriggerConfig(
            path="/hooks/x",
            secret_ref="my-secret",
            event_filter="push",
            header_filters={"X-Source": "github"},
        )
        assert cfg.secret_ref == "my-secret"
        assert cfg.event_filter == "push"
        assert cfg.header_filters == {"X-Source": "github"}


#  TimeTriggerFactory 
class TestTimeTriggerFactory:
    factory = TimeTriggerFactory()

    def test_creates_time_config(self):
        spec = TriggerSpec(
            type=TriggerType.TIME,
            parameters={"trigger_at": "2026-05-01T09:00:00+00:00"},
        )
        cfg = self.factory.create(spec)
        assert isinstance(cfg, TimeTriggerConfig)
        assert cfg.trigger_at == datetime(2026, 5, 1, 9, 0, 0, tzinfo=UTC)

    def test_no_recurrence_by_default(self):
        spec = TriggerSpec(
            type=TriggerType.TIME,
            parameters={"trigger_at": "2026-05-01T09:00:00+00:00"},
        )
        cfg = self.factory.create(spec)
        assert cfg.recurrence is None

    def test_daily_recurrence_parsed(self):
        spec = TriggerSpec(
            type=TriggerType.TIME,
            parameters={
                "trigger_at": "2026-05-01T09:00:00+00:00",
                "recurrence": {"frequency": "daily", "interval": 3},
            },
        )
        cfg = self.factory.create(spec)
        assert cfg.recurrence is not None
        assert cfg.recurrence.frequency == RecurrenceFrequency.DAILY
        assert cfg.recurrence.interval == 3

    def test_weekly_recurrence_parsed(self):
        spec = TriggerSpec(
            type=TriggerType.TIME,
            parameters={
                "trigger_at": "2026-05-01T09:00:00+00:00",
                "recurrence": {"frequency": "weekly", "days_of_week": [0, 4]},
            },
        )
        cfg = self.factory.create(spec)
        assert cfg.recurrence.days_of_week == [0, 4]

    def test_custom_recurrence_parsed(self):
        spec = TriggerSpec(
            type=TriggerType.TIME,
            parameters={
                "trigger_at": "2026-05-01T09:00:00+00:00",
                "recurrence": {"frequency": "custom", "cron_expression": "0 9 * * 1-5"},
            },
        )
        cfg = self.factory.create(spec)
        assert cfg.recurrence.cron_expression == "0 9 * * 1-5"

    def test_missing_trigger_at_raises(self):
        spec = TriggerSpec(type=TriggerType.TIME, parameters={})
        with pytest.raises(ValueError, match="trigger_at is required"):
            self.factory.create(spec)

    def test_naive_trigger_at_raises(self):
        spec = TriggerSpec(
            type=TriggerType.TIME,
            parameters={"trigger_at": "2026-05-01T09:00:00"},
        )
        with pytest.raises(ValueError, match="timezone-aware"):
            self.factory.create(spec)

    def test_invalid_recurrence_raises(self):
        spec = TriggerSpec(
            type=TriggerType.TIME,
            parameters={
                "trigger_at": "2026-05-01T09:00:00+00:00",
                "recurrence": {"frequency": "weekly"},  # missing days_of_week
            },
        )
        with pytest.raises(ValueError, match="days_of_week is required"):
            self.factory.create(spec)


#  WebhookTriggerFactory 
class TestWebhookTriggerFactory:
    factory = WebhookTriggerFactory()

    def test_creates_webhook_config(self):
        spec = TriggerSpec(type=TriggerType.WEBHOOK, parameters={"path": "/hooks/gh"})
        cfg = self.factory.create(spec)
        assert isinstance(cfg, WebhookTriggerConfig)
        assert cfg.path == "/hooks/gh"

    def test_default_method_is_post(self):
        spec = TriggerSpec(type=TriggerType.WEBHOOK, parameters={"path": "/hooks/gh"})
        cfg = self.factory.create(spec)
        assert cfg.method == "POST"

    def test_passes_optional_fields(self):
        spec = TriggerSpec(
            type=TriggerType.WEBHOOK,
            parameters={
                "path": "/hooks/gh",
                "secret_ref": "gh-secret",
                "event_filter": "push",
                "header_filters": {"X-Source": "github"},
            },
        )
        cfg = self.factory.create(spec)
        assert cfg.secret_ref == "gh-secret"
        assert cfg.event_filter == "push"
        assert cfg.header_filters == {"X-Source": "github"}

    def test_missing_path_raises(self):
        spec = TriggerSpec(type=TriggerType.WEBHOOK, parameters={})
        with pytest.raises(ValueError, match="path is required"):
            self.factory.create(spec)

    def test_path_without_slash_raises(self):
        spec = TriggerSpec(type=TriggerType.WEBHOOK, parameters={"path": "no-slash"})
        with pytest.raises(ValueError, match="path must start with /"):
            self.factory.create(spec)


#  TRIGGER_FACTORIES registry 
class TestTriggerFactoriesRegistry:
    def test_time_factory_is_registered(self):
        assert TriggerType.TIME in TRIGGER_FACTORIES
        assert isinstance(TRIGGER_FACTORIES[TriggerType.TIME], TimeTriggerFactory)

    def test_webhook_factory_is_registered(self):
        assert TriggerType.WEBHOOK in TRIGGER_FACTORIES
        assert isinstance(TRIGGER_FACTORIES[TriggerType.WEBHOOK], WebhookTriggerFactory)

    def test_all_trigger_types_are_registered(self):
        for t in TriggerType:
            assert t in TRIGGER_FACTORIES, f"Missing factory for {t}"

#  build_trigger_config entry point
class TestBuildTriggerConfigEntryPoint:
    def test_builds_time_config_via_registry(self):
        from app.trigger.triggerFactories import build_trigger_config

        spec = TriggerSpec(
            type=TriggerType.TIME,
            parameters={"trigger_at": "2026-05-01T09:00:00+00:00"},
        )

        cfg = build_trigger_config(spec)
        assert isinstance(cfg, TimeTriggerConfig)

    def test_unknown_type_raises_value_error(self):
        from app.trigger.triggerFactories import TRIGGER_FACTORIES, build_trigger_config

        spec = TriggerSpec(
            type=TriggerType.TIME,
            parameters={"trigger_at": "2026-05-01T09:00:00+00:00"},
        )

        # Temporarily remove and restore to validate entry point error path.
        old = TRIGGER_FACTORIES.pop(TriggerType.TIME)
        try:
            with pytest.raises(ValueError, match="No factory registered"):
                build_trigger_config(spec)
        finally:
            TRIGGER_FACTORIES[TriggerType.TIME] = old

#  JSON round-trip 
class TestTriggerConfigRoundTrip:
    def test_time_config_without_recurrence_roundtrips(self):
        from typing import Annotated

        from pydantic import BaseModel, Field

        TriggerConfigUnion = Annotated[
            TimeTriggerConfig | WebhookTriggerConfig,
            Field(discriminator="type"),
        ]

        class Wrapper(BaseModel):
            trigger: TriggerConfigUnion  # type: ignore[valid-type]

        cfg = TimeTriggerConfig(trigger_at=datetime(2026, 5, 1, 9, 0, 0, tzinfo=UTC))
        w = Wrapper(trigger=cfg)
        restored = Wrapper.model_validate(w.model_dump(mode="json"))
        assert isinstance(restored.trigger, TimeTriggerConfig)
        assert restored.trigger.trigger_at == cfg.trigger_at
        assert restored.trigger.recurrence is None

    def test_time_config_with_recurrence_roundtrips(self):
        from typing import Annotated

        from pydantic import BaseModel, Field

        TriggerConfigUnion = Annotated[
            TimeTriggerConfig | WebhookTriggerConfig,
            Field(discriminator="type"),
        ]

        class Wrapper(BaseModel):
            trigger: TriggerConfigUnion  # type: ignore[valid-type]

        rule = RecurrenceRule(frequency="weekly", days_of_week=[0, 4])
        cfg = TimeTriggerConfig(
            trigger_at=datetime(2026, 5, 1, 9, 0, 0, tzinfo=UTC),
            recurrence=rule,
        )
        w = Wrapper(trigger=cfg)
        restored = Wrapper.model_validate(w.model_dump(mode="json"))
        assert restored.trigger.recurrence is not None
        assert restored.trigger.recurrence.days_of_week == [0, 4]

    def test_webhook_config_roundtrips(self):
        from typing import Annotated

        from pydantic import BaseModel, Field

        TriggerConfigUnion = Annotated[
            TimeTriggerConfig | WebhookTriggerConfig,
            Field(discriminator="type"),
        ]

        class Wrapper(BaseModel):
            trigger: TriggerConfigUnion  # type: ignore[valid-type]

        cfg = WebhookTriggerConfig(path="/hooks/test", method="POST")
        w = Wrapper(trigger=cfg)
        restored = Wrapper.model_validate(w.model_dump(mode="json"))
        assert isinstance(restored.trigger, WebhookTriggerConfig)
        assert restored.trigger.path == "/hooks/test"


#  Runtime evaluators 

class TestTimeTriggerEvaluate:
    def test_past_time_one_shot_returns_true(self):
        trigger = TimeTrigger()
        cfg = TimeTriggerConfig(
            trigger_at=datetime.now(UTC) - timedelta(seconds=1)
        )
        assert asyncio.run(trigger.evaluate({"config": cfg})) is True

    def test_future_time_one_shot_returns_false(self):
        trigger = TimeTrigger()
        cfg = TimeTriggerConfig(
            trigger_at=datetime.now(UTC) + timedelta(hours=1)
        )
        assert asyncio.run(trigger.evaluate({"config": cfg})) is False

    def test_recurring_daily_due_returns_true(self):
        trigger = TimeTrigger()
        start = datetime.now(UTC) - timedelta(days=1)
        rule = RecurrenceRule(frequency="daily", interval=1)
        cfg = TimeTriggerConfig(trigger_at=start, recurrence=rule)
        # now is exactly 1 day after start → should be due
        assert asyncio.run(trigger.evaluate({"config": cfg})) is True

    def test_recurring_before_start_returns_false(self):
        trigger = TimeTrigger()
        start = datetime.now(UTC) + timedelta(hours=1)
        rule = RecurrenceRule(frequency="daily", interval=1)
        cfg = TimeTriggerConfig(trigger_at=start, recurrence=rule)
        assert asyncio.run(trigger.evaluate({"config": cfg})) is False

    def test_schema_id_is_time(self):
        assert TimeTrigger.schema.id == "time"


class TestWebhookTriggerEvaluate:
    def test_always_returns_true(self):
        trigger = WebhookTrigger()
        assert asyncio.run(trigger.evaluate({})) is True

    def test_schema_id_is_webhook(self):
        assert WebhookTrigger.schema.id == "webhook"
