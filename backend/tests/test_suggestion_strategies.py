"""Unit tests for the three SuggestionStrategy implementations."""

import asyncio

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


def test_rule_based_matches_interval_trigger():
    strategy = RuleBasedStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(UserInput(raw_text="call the API every 15 minutes"))
    )
    assert result.workflow_draft is not None
    recurrence = result.workflow_draft["trigger"]["recurrence"]
    assert recurrence["frequency"] == "minutely"
    assert recurrence["interval"] == 15


def test_rule_based_no_match_returns_none_draft():
    strategy = RuleBasedStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(raw_text="random gibberish that matches nothing")
        )
    )
    assert result.strategy_used == "rule_based"
    assert result.workflow_draft is None


# ---------- TemplateStrategy ----------

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


def test_template_picks_weekly_summary():
    strategy = TemplateStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(
            UserInput(raw_text="weekly summary email to me@acme.com")
        )
    )
    assert result.workflow_draft is not None
    assert result.workflow_draft["trigger"]["recurrence"]["frequency"] == "weekly"


def test_template_no_match_returns_none():
    strategy = TemplateStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(UserInput(raw_text="tell me a joke about cats"))
    )
    assert result.workflow_draft is None


# ---------- LLMStrategy (no API key = graceful fallback) ----------

def test_llm_strategy_without_api_key_returns_no_draft(monkeypatch):
    from app.suggestion import openai_client as oc

    oc.get_openai_client.cache_clear()
    monkeypatch.setattr("app.core.config.settings.openai_api_key", "")
    strategy = LLMStrategy()
    result = asyncio.run(
        strategy.generate_suggestion(UserInput(raw_text="complex request"))
    )
    assert result.strategy_used == "llm"
    assert result.workflow_draft is None
    assert "OPENAI_API_KEY" in result.content


def test_validate_and_fix_fills_defaults():
    draft = {"trigger": {"type": "time"}, "steps": [{"action_type": "send_email"}]}
    fixed = _validate_and_fix(draft)
    assert fixed["name"] == "AI-Generated Workflow"
    assert fixed["trigger"]["timezone"] == "UTC"
    assert fixed["steps"][0]["to_template"] == "recipient@example.com"
    assert fixed["steps"][0]["step_order"] == 0
