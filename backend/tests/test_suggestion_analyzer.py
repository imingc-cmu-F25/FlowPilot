"""Unit tests for AIAnalyzer heuristic fallback (no LLM call)."""

import asyncio

import pytest
from app.suggestion.analyzer import AIAnalyzer
from app.suggestion.base import UserInput


@pytest.fixture(autouse=True)
def disable_openai(monkeypatch):
    import app.suggestion.openai_client as oc

    oc._cached_client = None
    oc._cached_key = None
    monkeypatch.setattr("app.core.config.settings.openai_api_key", "")
    yield
    oc._cached_client = None
    oc._cached_key = None


def test_analyzer_classifies_daily_as_simple():
    result = asyncio.run(AIAnalyzer().analyze(UserInput(raw_text="send a daily email")))
    assert result.complexity_level == "simple"
    assert result.confidence >= 0.8
    assert result.input_type == "automation_request"


def test_analyzer_classifies_weekly_as_simple():
    result = asyncio.run(AIAnalyzer().analyze(UserInput(raw_text="every week send report")))
    assert result.complexity_level == "simple"
    assert result.confidence >= 0.8


def test_analyzer_classifies_webhook_as_simple():
    result = asyncio.run(AIAnalyzer().analyze(UserInput(raw_text="webhook trigger deploy")))
    assert result.complexity_level == "simple"
    assert result.input_type == "automation_request"


def test_analyzer_medium_with_action_keyword():
    result = asyncio.run(
        AIAnalyzer().analyze(
            UserInput(raw_text="send email to team after 5 minutes")
        )
    )
    assert result.complexity_level == "medium"
    assert result.confidence >= 0.7
    assert result.input_type == "automation_request"


def test_analyzer_medium_with_check_keyword():
    result = asyncio.run(AIAnalyzer().analyze(UserInput(raw_text="check health and notify admin")))
    assert result.complexity_level == "medium"
    assert result.confidence >= 0.7


def test_analyzer_short_vague_input():
    result = asyncio.run(AIAnalyzer().analyze(UserInput(raw_text="notify me")))
    assert result.complexity_level == "medium"
    assert result.confidence >= 0.7


def test_analyzer_long_complex_input():
    long_text = " ".join(["complex"] * 40)
    result = asyncio.run(AIAnalyzer().analyze(UserInput(raw_text=long_text)))
    assert result.complexity_level == "complex"
    assert result.confidence < 0.7


@pytest.mark.parametrize(
    "raw_text",
    [
        "tell me a joke about cats",
        "what is the meaning of life",
        "hello how are you doing",
        "explain quantum physics please",
        # English keyboard mash — only stray latin letters, no workflow words.
        "asdfgh qwerty zxcvb hjkl",
    ],
)
def test_analyzer_flags_off_topic_input_as_other_high_confidence(raw_text):
    """The relevance gate must mark non-workflow input as 'other' with high
    confidence so the service layer can short-circuit the pipeline."""
    result = asyncio.run(AIAnalyzer().analyze(UserInput(raw_text=raw_text)))
    assert result.input_type == "other"
    assert result.confidence >= 0.8
