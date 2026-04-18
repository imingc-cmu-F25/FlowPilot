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
    service = SuggestionService(db_session)
    orm = asyncio.run(
        service.suggest(UserInput(raw_text="xyzzy foobar baz", user_name="alice"))
    )
    assert orm.strategy_used == "llm"
