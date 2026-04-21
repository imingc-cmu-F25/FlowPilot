"""Integration tests for SuggestionService (SQLite in-memory, no OpenAI)."""

import asyncio

import pytest
from app.db.connector import get_engine
from app.db.session import SessionFactory
from app.suggestion.base import UserInput
from app.suggestion.service import SuggestionService
from sqlalchemy import text


@pytest.fixture
def db_session():
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO users (name, password_hash) VALUES ('alice', 'x')")
        )
    session = SessionFactory(bind=engine)
    try:
        yield session
        session.commit()
    finally:
        session.close()


@pytest.fixture(autouse=True)
def disable_openai(monkeypatch):
    from app.suggestion import openai_client as oc

    oc._cached_client = None
    oc._cached_key = None
    monkeypatch.setattr("app.core.config.settings.openai_api_key", "")
    yield
    oc._cached_client = None
    oc._cached_key = None


def test_service_persists_suggestion(db_session):
    service = SuggestionService(db_session)
    orm = asyncio.run(
        service.suggest(
            UserInput(
                raw_text="Send a daily email to team@acme.com at 9am",
                user_name="alice",
            )
        )
    )
    assert orm.user_name == "alice"
    assert orm.strategy_used in ("rule_based", "template", "llm")
    assert orm.workflow_draft is not None  # rule-based should match
    assert orm.content


def test_service_repo_lists_user_history(db_session):
    service = SuggestionService(db_session)
    asyncio.run(
        service.suggest(UserInput(raw_text="daily email to a@b.com", user_name="alice"))
    )
    asyncio.run(
        service.suggest(
            UserInput(raw_text="weekly summary to a@b.com", user_name="alice")
        )
    )
    history = service.repo.list_for_user("alice")
    assert len(history) == 2


def test_service_falls_back_to_llm_when_non_llm_returns_no_draft(db_session):
    """Workflow-relevant phrasing that none of the rule_based / template
    patterns match should still reach the LLM fallback (and be marked as
    such even when the LLM itself produces no draft due to no API key)."""
    service = SuggestionService(db_session)
    orm = asyncio.run(
        service.suggest(
            UserInput(
                raw_text="please send the report when the deploy finishes",
                user_name="alice",
            )
        )
    )
    assert orm.strategy_used == "llm"


@pytest.mark.parametrize(
    "raw_text",
    [
        "tell me a joke about cats",
        "what is the meaning of life",
        "hello how are you doing",
    ],
)
def test_service_returns_guard_for_off_topic_input(db_session, raw_text):
    """Inputs the analyzer flags as not-a-workflow with high confidence
    must skip the strategy pipeline and return a friendly nudge."""
    service = SuggestionService(db_session)
    orm = asyncio.run(
        service.suggest(UserInput(raw_text=raw_text, user_name="alice"))
    )
    assert orm.strategy_used == "guard"
    assert orm.workflow_draft is None
    assert "automation" in orm.content.lower()


@pytest.mark.parametrize(
    "raw_text",
    [
        "hi",         # too short
        "?",          # punctuation only
        "1 2 3 4 5",  # no alpha words
        "a b c d",    # no 3+ char word
    ],
)
def test_service_returns_guard_message_for_short_or_garbage_input(db_session, raw_text):
    service = SuggestionService(db_session)
    orm = asyncio.run(
        service.suggest(UserInput(raw_text=raw_text, user_name="alice"))
    )
    assert orm.strategy_used == "guard"
    assert orm.workflow_draft is None
    assert "too short" in orm.content.lower()


def test_service_does_not_guard_legitimate_short_prompts(db_session):
    """Make sure the guard isn't so aggressive that it rejects valid asks
    like 'send daily email'."""
    service = SuggestionService(db_session)
    orm = asyncio.run(
        service.suggest(UserInput(raw_text="send daily email to a@b.com", user_name="alice"))
    )
    assert orm.strategy_used != "guard"
    assert orm.workflow_draft is not None


def test_detect_pending_questions_flags_slack_channel_url():
    """A user pasting their Slack channel viewer URL should be re-prompted
    for the actual Incoming Webhook URL (hooks.slack.com), not allowed to
    create a workflow that POSTs to a non-existent endpoint."""
    from app.suggestion.service import detect_pending_questions

    draft = {
        "trigger": {"type": "time"},
        "steps": [{
            "action_type": "http_request",
            "url_template": "https://app.slack.com/client/T0AU/C0ATPQQU",
        }],
    }
    questions = detect_pending_questions(draft)
    fields = [q.field for q in questions]
    assert "steps.0.url_template" in fields
    # Hint should mention the real Incoming Webhook host.
    msg = next(q.question for q in questions if q.field == "steps.0.url_template")
    assert "hooks.slack.com" in msg.lower() or "incoming webhook" in msg.lower()


def test_detect_pending_questions_flags_placeholder_url():
    from app.suggestion.service import detect_pending_questions

    draft = {
        "trigger": {"type": "time"},
        "steps": [{
            "action_type": "http_request",
            "url_template": "https://example.com/api/foo",
        }],
    }
    questions = detect_pending_questions(draft)
    assert any(q.field == "steps.0.url_template" for q in questions)


def test_detect_pending_questions_passes_real_slack_webhook():
    """A real https://hooks.slack.com/... URL must NOT be flagged."""
    from app.suggestion.service import detect_pending_questions

    draft = {
        "trigger": {"type": "time"},
        "steps": [{
            "action_type": "http_request",
            "url_template": "https://hooks.slack.com/services/T0/B0/abc",
        }],
    }
    assert detect_pending_questions(draft) == []


def test_detect_pending_questions_flags_slack_token_pasted_as_url():
    """User pasted a Slack OAuth token into url_template — would have
    failed at runtime with 'URL is missing http(s)://'. Catch it here.

    The literal string below is deliberately short and obviously
    synthetic (no random-looking entropy after the prefix) so GitHub's
    secret scanner doesn't flag it as a real Slack credential.
    """
    from app.suggestion.service import detect_pending_questions

    fake_slack_token = "xoxe-" + "test-fake-not-a-real-token"
    draft = {
        "trigger": {"type": "time"},
        "steps": [{
            "action_type": "http_request",
            "url_template": fake_slack_token,
        }],
    }
    questions = detect_pending_questions(draft)
    assert any(q.field == "steps.0.url_template" for q in questions)
    msg = next(q.question for q in questions if q.field == "steps.0.url_template")
    assert "token" in msg.lower()


def test_detect_pending_questions_flags_url_missing_protocol():
    from app.suggestion.service import detect_pending_questions

    draft = {
        "trigger": {"type": "time"},
        "steps": [{
            "action_type": "http_request",
            "url_template": "api.example.com/foo",  # missing https://
        }],
    }
    questions = detect_pending_questions(draft)
    assert any(q.field == "steps.0.url_template" for q in questions)
