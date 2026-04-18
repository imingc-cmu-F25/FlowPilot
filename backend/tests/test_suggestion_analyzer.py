"""Unit tests for AIAnalyzer heuristic fallback (no LLM call)."""

import asyncio

import pytest
from app.suggestion.analyzer import AIAnalyzer
from app.suggestion.base import UserInput


@pytest.fixture(autouse=True)
def disable_openai(monkeypatch):
    from app.suggestion import openai_client as oc

    oc.get_openai_client.cache_clear()
    monkeypatch.setattr("app.core.config.settings.openai_api_key", "")
    yield
    oc.get_openai_client.cache_clear()


def test_analyzer_classifies_daily_as_simple():
    result = asyncio.run(AIAnalyzer().analyze(UserInput(raw_text="send a daily email")))
    assert result.complexity_level == "simple"
    assert result.confidence >= 0.8
    assert result.input_type == "automation_request"


def test_analyzer_long_complex_input():
    long_text = " ".join(["complex"] * 40)
    result = asyncio.run(AIAnalyzer().analyze(UserInput(raw_text=long_text)))
    assert result.complexity_level == "complex"


def test_analyzer_short_ambiguous_input():
    result = asyncio.run(AIAnalyzer().analyze(UserInput(raw_text="notify me")))
    assert result.complexity_level == "medium"
    assert 0.0 <= result.confidence <= 1.0
