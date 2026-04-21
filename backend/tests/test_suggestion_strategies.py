"""Unit tests for the three SuggestionStrategy implementations."""

import asyncio

import pytest
from app.suggestion.base import UserInput
from app.suggestion.strategies.llm import LLMStrategy, _validate_and_fix
from app.suggestion.strategies.rule_based import RuleBasedStrategy
from app.suggestion.strategies.template import TemplateStrategy

# ---------- RuleBasedStrategy ----------


def test_rule_based_matches_daily_email():
    strategy = RuleBasedStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(raw_text="Send a daily email at 9am to team@acme.com")
        )
    )
    assert result.strategy_used == "rule_based"
    assert result.workflow_draft is not None
    assert result.workflow_draft["trigger"]["type"] == "time"
    assert result.workflow_draft["trigger"]["recurrence"]["frequency"] == "daily"
    assert result.workflow_draft["steps"][0]["action_type"] == "send_email"
    assert result.workflow_draft["steps"][0]["to_template"] == "team@acme.com"


def test_rule_based_extracts_subject_and_body():
    strategy = RuleBasedStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(
                raw_text='Send a daily email at 9am to team@acme.com '
                'with subject "Meeting Reminder" and body "Remember the standup meeting"'
            )
        )
    )
    assert result.workflow_draft is not None
    step = result.workflow_draft["steps"][0]
    assert step["subject_template"] == "Meeting Reminder"
    assert step["body_template"] == "Remember the standup meeting"


def test_rule_based_matches_weekly_email():
    strategy = RuleBasedStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(raw_text="Send a weekly email to manager@acme.com")
        )
    )
    assert result.workflow_draft is not None
    assert result.workflow_draft["trigger"]["recurrence"]["frequency"] == "weekly"
    assert result.workflow_draft["steps"][0]["to_template"] == "manager@acme.com"


def test_rule_based_matches_interval_trigger():
    strategy = RuleBasedStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(UserInput(raw_text="call the API every 15 minutes"))
    )
    assert result.workflow_draft is not None
    recurrence = result.workflow_draft["trigger"]["recurrence"]
    assert recurrence["frequency"] == "minutely"
    assert recurrence["interval"] == 15


def test_rule_based_matches_delayed_email():
    strategy = RuleBasedStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(raw_text="send email after 10 minutes to dev@acme.com")
        )
    )
    assert result.workflow_draft is not None
    assert result.workflow_draft["name"] == "Send Email After 10 Minutes"
    assert result.workflow_draft["trigger"]["recurrence"] is None
    assert result.workflow_draft["steps"][0]["to_template"] == "dev@acme.com"


def test_rule_based_matches_webhook_to_email():
    strategy = RuleBasedStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(raw_text="webhook forward payload send to ops@acme.com")
        )
    )
    assert result.workflow_draft is not None
    assert result.workflow_draft["trigger"]["type"] == "webhook"
    assert result.workflow_draft["steps"][0]["action_type"] == "send_email"
    assert result.workflow_draft["steps"][0]["to_template"] == "ops@acme.com"


def test_rule_based_matches_webhook_to_api():
    strategy = RuleBasedStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(raw_text="when webhook fires call API https://deploy.example.com/run")
        )
    )
    assert result.workflow_draft is not None
    assert result.workflow_draft["trigger"]["type"] == "webhook"
    assert result.workflow_draft["steps"][0]["action_type"] == "http_request"
    assert result.workflow_draft["steps"][0]["url_template"] == "https://deploy.example.com/run"


def test_rule_based_matches_health_check_alert():
    strategy = RuleBasedStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(
                raw_text="check health https://api.example.com/health"
                " and email alert to admin@acme.com"
            )
        )
    )
    assert result.workflow_draft is not None
    assert len(result.workflow_draft["steps"]) == 2
    assert result.workflow_draft["steps"][0]["action_type"] == "http_request"
    assert result.workflow_draft["steps"][0]["url_template"] == "https://api.example.com/health"
    assert result.workflow_draft["steps"][1]["action_type"] == "send_email"
    assert result.workflow_draft["steps"][1]["to_template"] == "admin@acme.com"


def test_rule_based_matches_fetch_and_email():
    strategy = RuleBasedStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(
                raw_text="fetch data from https://api.example.com/report"
                " and email to boss@acme.com"
            )
        )
    )
    assert result.workflow_draft is not None
    assert len(result.workflow_draft["steps"]) == 2
    assert result.workflow_draft["steps"][0]["action_type"] == "http_request"
    assert result.workflow_draft["steps"][1]["action_type"] == "send_email"
    assert "{{previous_output}}" in result.workflow_draft["steps"][1]["body_template"]


def test_rule_based_no_match_returns_none_draft():
    strategy = RuleBasedStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(raw_text="random gibberish that matches nothing")
        )
    )
    assert result.strategy_used == "rule_based"
    assert result.workflow_draft is None


def test_rule_based_matches_daily_schedule_email():
    strategy = RuleBasedStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(raw_text="every morning email me my schedule to me@acme.com")
        )
    )
    assert result.workflow_draft is not None
    draft = result.workflow_draft
    assert draft["trigger"]["type"] == "time"
    assert draft["trigger"]["recurrence"]["frequency"] == "daily"
    assert [s["action_type"] for s in draft["steps"]] == [
        "calendar_list_upcoming",
        "send_email",
    ]
    assert draft["steps"][0]["window_hours"] == 24
    assert draft["steps"][1]["to_template"] == "me@acme.com"


def test_rule_based_matches_calendar_event_to_email():
    strategy = RuleBasedStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(
                raw_text=(
                    "when a calendar event titled \"1:1\" shows up,"
                    " email me at me@acme.com"
                )
            )
        )
    )
    assert result.workflow_draft is not None
    draft = result.workflow_draft
    assert draft["trigger"]["type"] == "calendar_event"
    assert draft["trigger"]["title_contains"] == "1:1"
    assert draft["steps"][0]["action_type"] == "send_email"
    assert draft["steps"][0]["to_template"] == "me@acme.com"


# ---------- TemplateStrategy ----------


def test_template_picks_delayed_email():
    strategy = TemplateStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(raw_text="send email after 5 minutes to user@acme.com")
        )
    )
    assert result.strategy_used == "template"
    assert result.workflow_draft is not None
    assert result.workflow_draft["name"] == "Send Email After 5 Minutes"
    assert result.workflow_draft["trigger"]["recurrence"] is None
    assert result.workflow_draft["steps"][0]["to_template"] == "user@acme.com"


def test_template_picks_webhook_to_email():
    strategy = TemplateStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(raw_text="webhook forward payload to email ops@acme.com")
        )
    )
    assert result.strategy_used == "template"
    assert result.workflow_draft is not None
    assert result.workflow_draft["trigger"]["type"] == "webhook"
    assert result.workflow_draft["steps"][0]["to_template"] == "ops@acme.com"


def test_template_picks_webhook_to_api():
    strategy = TemplateStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(raw_text="webhook trigger call api https://deploy.example.com")
        )
    )
    assert result.workflow_draft is not None
    assert result.workflow_draft["trigger"]["type"] == "webhook"
    assert result.workflow_draft["steps"][0]["action_type"] == "http_request"
    assert result.workflow_draft["steps"][0]["url_template"] == "https://deploy.example.com"


def test_template_picks_weekly_summary():
    strategy = TemplateStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(raw_text="weekly summary email to me@acme.com")
        )
    )
    assert result.workflow_draft is not None
    assert result.workflow_draft["trigger"]["recurrence"]["frequency"] == "weekly"
    assert result.workflow_draft["steps"][0]["to_template"] == "me@acme.com"


def test_template_picks_daily_email():
    strategy = TemplateStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(raw_text="daily report email to team@acme.com at 8am")
        )
    )
    assert result.workflow_draft is not None
    assert result.workflow_draft["trigger"]["recurrence"]["frequency"] == "daily"
    assert result.workflow_draft["steps"][0]["to_template"] == "team@acme.com"


def test_template_extracts_subject_and_body():
    strategy = TemplateStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(
                raw_text='daily email to dev@acme.com '
                'with subject "Deploy Status" and body "Latest deploy results are in"'
            )
        )
    )
    assert result.workflow_draft is not None
    step = result.workflow_draft["steps"][0]
    assert step["subject_template"] == "Deploy Status"
    assert step["body_template"] == "Latest deploy results are in"


def test_template_picks_health_check_alert():
    strategy = TemplateStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(raw_text="monitor health https://api.example.com and notify admin@acme.com")
        )
    )
    assert result.workflow_draft is not None
    assert len(result.workflow_draft["steps"]) == 2
    assert result.workflow_draft["steps"][0]["action_type"] == "http_request"
    assert result.workflow_draft["steps"][1]["action_type"] == "send_email"


def test_template_picks_fetch_and_email():
    strategy = TemplateStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(raw_text="fetch report from https://data.example.com and send email")
        )
    )
    assert result.workflow_draft is not None
    assert len(result.workflow_draft["steps"]) == 2
    assert result.workflow_draft["steps"][0]["url_template"] == "https://data.example.com"


def test_template_no_match_returns_none():
    strategy = TemplateStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(UserInput(raw_text="tell me a joke about cats"))
    )
    assert result.workflow_draft is None


def test_rule_based_matches_delayed_email_seconds():
    strategy = RuleBasedStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(raw_text="send email to yianchen189@gmail.com after 30 seconds")
        )
    )
    assert result.workflow_draft is not None
    draft = result.workflow_draft
    assert draft["name"] == "Send Email After 30 Seconds"
    assert draft["trigger"]["type"] == "time"
    assert draft["trigger"]["recurrence"] is None
    assert draft["steps"][0]["action_type"] == "send_email"
    assert draft["steps"][0]["to_template"] == "yianchen189@gmail.com"


def test_rule_based_does_not_treat_email_digits_as_hour():
    """Regression: '_extract_hour' previously matched any digit, so an
    email handle like 'alice2@acme.com' was parsed as 2 AM and the daily
    schedule fired at the wrong time. The anchored regex requires
    am/pm or 'at HH'."""
    strategy = RuleBasedStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(raw_text="send a daily email to alice2@acme.com")
        )
    )
    assert result.workflow_draft is not None
    # No explicit hour in the prompt → default 9 AM.
    description = result.workflow_draft["description"]
    assert "9:00" in description, description


def test_rule_based_matches_one_time_email_tomorrow():
    """Regression: 'send email at 9AM tomorrow' used to fall through to the
    LLM and trigger the Groq tool-call refusal scolding. Rule_based now
    handles it directly."""
    strategy = RuleBasedStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(
                raw_text="send an email to imingc@andrew.cmu.edu at 9AM tomorrow"
            )
        )
    )
    assert result.workflow_draft is not None
    draft = result.workflow_draft
    assert draft["trigger"]["type"] == "time"
    assert draft["trigger"]["recurrence"] is None
    assert "tomorrow" in draft["name"].lower()
    assert draft["steps"][0]["to_template"] == "imingc@andrew.cmu.edu"


def test_rule_based_matches_bare_at_hour_no_day_anchor():
    """Regression: 'send email to X at 11PM' (no tomorrow/today) should
    hit rule_based, not fall through to LLM. Previously the LLM was
    interpreting bare hours in UTC, producing schedules at the wrong
    time."""
    strategy = RuleBasedStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(
                raw_text="send an email to yiranchen189@gmail.com at 11PM",
                timezone="America/Los_Angeles",
            )
        )
    )
    assert result.workflow_draft is not None
    assert result.strategy_used == "rule_based"
    draft = result.workflow_draft
    assert draft["trigger"]["type"] == "time"
    assert draft["trigger"]["recurrence"] is None
    # 11 PM Pacific = 06:00 UTC (PDT) or 07:00 UTC (PST). Must NOT be
    # 23:00 UTC (which would be the bug we're fixing).
    trigger_at = draft["trigger"]["trigger_at"]
    assert "T06:00:00" in trigger_at or "T07:00:00" in trigger_at, trigger_at
    assert "T23:00:00" not in trigger_at


def test_rule_based_resolves_local_timezone_for_one_time_trigger():
    """'9 AM tomorrow' with timezone='America/Los_Angeles' should produce
    a trigger_at corresponding to 9 AM PT (16:00 or 17:00 UTC depending
    on DST), NOT 9 AM UTC. Regression for the issue where users in PDT
    saw their schedule fire 7 hours early."""
    strategy = RuleBasedStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(
                raw_text="send an email to me@acme.com at 9AM tomorrow",
                timezone="America/Los_Angeles",
            )
        )
    )
    assert result.workflow_draft is not None
    trigger_at = result.workflow_draft["trigger"]["trigger_at"]
    # America/Los_Angeles is UTC-7 (PDT) or UTC-8 (PST). 9 AM local =
    # either 16:00 or 17:00 UTC. Must NOT be 09:00 UTC.
    assert "T16:00:00" in trigger_at or "T17:00:00" in trigger_at, trigger_at
    assert "T09:00:00+00:00" not in trigger_at
    # Trigger.timezone should record the user's zone (not silently UTC).
    assert result.workflow_draft["trigger"]["timezone"] == "America/Los_Angeles"


def test_rule_based_falls_back_to_utc_when_no_timezone():
    """Pre-existing behaviour: with no timezone the schedule is UTC."""
    strategy = RuleBasedStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(raw_text="send an email to me@acme.com at 9AM tomorrow")
        )
    )
    assert result.workflow_draft is not None
    trigger_at = result.workflow_draft["trigger"]["trigger_at"]
    assert "T09:00:00+00:00" in trigger_at
    assert result.workflow_draft["trigger"]["timezone"] == "UTC"


def test_rule_based_does_not_treat_seconds_as_hour():
    """Regression: 'after 30 seconds' would set hour=30 (clamped to 23)."""
    strategy = RuleBasedStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(
                raw_text="send daily email to ops@acme.com after 30 seconds"
            )
        )
    )
    # Prompt ambiguity here — but importantly, the hour must NOT be 30/23/0.
    # We expect either the seconds-delay rule (fires once) OR the daily rule
    # at 9 AM. Both are acceptable; "0:00 UTC" or "23:00 UTC" are not.
    if result.workflow_draft is not None:
        description = result.workflow_draft["description"]
        assert "0:00" not in description
        assert "23:00" not in description


def test_template_picks_delayed_email_seconds():
    strategy = TemplateStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(raw_text="send email to user@acme.com after 45 sec")
        )
    )
    assert result.workflow_draft is not None
    draft = result.workflow_draft
    assert draft["name"] == "Send Email After 45 Seconds"
    assert draft["trigger"]["recurrence"] is None
    assert draft["steps"][0]["to_template"] == "user@acme.com"


# ---------- LLMStrategy (no API key = graceful fallback) ----------


def test_llm_strategy_without_api_key_returns_no_draft(monkeypatch):
    import app.suggestion.openai_client as oc

    oc._cached_client = None
    oc._cached_key = None
    monkeypatch.setattr("app.core.config.settings.openai_api_key", "")
    strategy = LLMStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(UserInput(raw_text="complex request"))
    )
    assert result.strategy_used == "llm"
    assert result.workflow_draft is None
    assert "OPENAI_API_KEY" in result.content


def test_llm_strategy_sanitizes_no_tool_call_response(monkeypatch):
    """Some providers (Groq/Llama) ignore tool_choice and return a bare
    chat message with misleading 'fix the recurrence error' text. We must
    not surface that content to the user — return a neutral fallback."""
    import app.suggestion.openai_client as oc

    # Stub OpenAI response: content filled, tool_calls None
    class _Msg:
        tool_calls = None
        content = (
            "LLM call failed: To fix the error, ensure the recurrence "
            "parameter in your trigger is an object, not null."
        )

    class _Choice:
        message = _Msg()

    class _Resp:
        choices = [_Choice()]

    class _Completions:
        async def create(self, **_kwargs):
            return _Resp()

    class _Chat:
        completions = _Completions()

    class _Client:
        chat = _Chat()

    monkeypatch.setattr(
        "app.suggestion.strategies.llm.get_openai_client", lambda: _Client()
    )

    strategy = LLMStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(raw_text="send email to yianchen189@gmail.com after 30 seconds")
        )
    )
    assert result.strategy_used == "llm"
    assert result.workflow_draft is None
    # The scolding text must be stripped.
    assert "recurrence" not in result.content.lower()
    assert "error" not in result.content.lower()
    # And a helpful nudge must remain.
    assert "rephras" in result.content.lower()

    # Clean up
    oc._cached_client = None
    oc._cached_key = None


# ---------- _validate_and_fix ----------


def test_validate_and_fix_fills_time_trigger_defaults():
    draft = {"trigger": {"type": "time"}, "steps": [{"action_type": "send_email"}]}
    fixed = _validate_and_fix(draft)
    assert fixed["name"] == "AI-Generated Workflow"
    assert fixed["trigger"]["timezone"] == "UTC"
    assert fixed["trigger"]["trigger_at"] is not None
    assert fixed["trigger"]["recurrence"] is None
    assert fixed["steps"][0]["step_order"] == 0
    assert "to_template" in fixed["steps"][0]


def test_validate_and_fix_rejects_recurring_trigger_without_trigger_at():
    """Regression: a recurring trigger anchored to 'now + 1h' would fire at
    a random minute the user never asked for. Refuse instead."""
    from app.suggestion.strategies.llm import DraftFillError

    draft = {
        "trigger": {
            "type": "time",
            "recurrence": {"frequency": "daily", "interval": 1},
        },
        "steps": [{"action_type": "send_email"}],
    }
    with pytest.raises(DraftFillError):
        _validate_and_fix(draft)


def test_validate_and_fix_keeps_one_time_default_when_no_recurrence():
    """One-time triggers without trigger_at can still default to soon —
    only recurrence makes 'silent default' dangerous."""
    draft = {"trigger": {"type": "time"}, "steps": []}
    fixed = _validate_and_fix(draft)
    assert fixed["trigger"]["trigger_at"] is not None
    assert fixed["trigger"]["recurrence"] is None


def test_validate_and_fix_fills_webhook_trigger_defaults():
    draft = {"trigger": {"type": "webhook"}, "steps": [{"action_type": "http_request"}]}
    fixed = _validate_and_fix(draft)
    assert fixed["trigger"]["path"] == "/hooks/incoming"
    assert fixed["trigger"]["method"] == "POST"
    assert fixed["steps"][0]["method"] == "GET"
    assert "url_template" in fixed["steps"][0]


def test_validate_and_fix_fills_custom_trigger_defaults():
    draft = {"trigger": {"type": "custom"}, "steps": []}
    fixed = _validate_and_fix(draft)
    assert fixed["trigger"]["condition"] == "true"
    assert fixed["trigger"]["source"] == "event_payload"


def test_validate_and_fix_fills_calendar_step_defaults():
    draft = {
        "trigger": {"type": "time"},
        "steps": [{"action_type": "calendar_create_event"}],
    }
    fixed = _validate_and_fix(draft)
    step = fixed["steps"][0]
    assert step["action_type"] == "calendar_create_event"
    assert "calendar_id" in step
    assert "title_template" in step
    assert "start_mapping" in step
    assert "end_mapping" in step


def test_validate_and_fix_preserves_existing_values():
    draft = {
        "name": "My Workflow",
        "description": "Custom description",
        "trigger": {
            "type": "time",
            "trigger_at": "2026-05-01T09:00:00+00:00",
            "timezone": "America/New_York",
        },
        "steps": [
            {
                "action_type": "send_email",
                "name": "Notify Team",
                "step_order": 0,
                "to_template": "team@company.com",
                "subject_template": "Alert",
                "body_template": "Something happened.",
            }
        ],
    }
    fixed = _validate_and_fix(draft)
    assert fixed["name"] == "My Workflow"
    assert fixed["description"] == "Custom description"
    assert fixed["trigger"]["timezone"] == "America/New_York"
    assert fixed["steps"][0]["to_template"] == "team@company.com"
    assert fixed["steps"][0]["subject_template"] == "Alert"


def test_validate_and_fix_multi_step():
    draft = {
        "trigger": {"type": "time"},
        "steps": [
            {"action_type": "http_request", "name": "Fetch", "step_order": 0},
            {"action_type": "send_email", "name": "Email", "step_order": 1},
        ],
    }
    fixed = _validate_and_fix(draft)
    assert len(fixed["steps"]) == 2
    assert fixed["steps"][0]["action_type"] == "http_request"
    assert fixed["steps"][0]["step_order"] == 0
    assert fixed["steps"][1]["action_type"] == "send_email"
    assert fixed["steps"][1]["step_order"] == 1
