"""Google Calendar connector wiring tests.

These tests don't talk to Google — they cover the parts we own:

* ``is_configured`` + ``build_authorize_url`` gate on env credentials.
* ``UserConnectionRepository`` upsert semantics (refresh_token preserved).
* ``CalendarCreateEventAction`` falls back to the mock when the server is
  unconfigured or the user has not linked, and calls the real connector
  when both are true.
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

from app.action.calendarAction import CalendarCreateEventAction
from app.connectors import google_calendar as gcal
from app.connectors.repo import UserConnectionRepository
from app.core.config import settings
from app.db.connector import get_engine
from app.db.session import init_db
from sqlalchemy.orm import sessionmaker


def _session():
    init_db()
    return sessionmaker(
        bind=get_engine(),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )()


def test_is_configured_reflects_env(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "")
    monkeypatch.setattr(settings, "google_client_secret", "")
    assert gcal.is_configured() is False

    monkeypatch.setattr(settings, "google_client_id", "id")
    monkeypatch.setattr(settings, "google_client_secret", "secret")
    assert gcal.is_configured() is True


def test_build_authorize_url_raises_without_config(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "")
    monkeypatch.setattr(settings, "google_client_secret", "")
    s = _session()
    try:
        gcal.build_authorize_url(s, state="tok")
    except gcal.GoogleCalendarNotConfigured:
        return
    finally:
        s.close()
    raise AssertionError("expected GoogleCalendarNotConfigured")


def test_build_authorize_url_persists_code_verifier(monkeypatch):
    """authorize must stash PKCE verifier so callback can complete the exchange."""
    monkeypatch.setattr(settings, "google_client_id", "id")
    monkeypatch.setattr(settings, "google_client_secret", "secret")
    monkeypatch.setattr(
        settings,
        "google_redirect_uri",
        "http://localhost:8000/api/connectors/google/callback",
    )

    from app.db.schema import UserSessionORM
    from app.user.repo import UserRepository

    s = _session()
    try:
        UserRepository(s).create("pkce-user", "x" * 60)
        s.add(UserSessionORM(token="pkce-tok", user_name="pkce-user"))
        s.commit()

        result = gcal.build_authorize_url(s, state="pkce-tok")
        assert "code_challenge=" in result.url
        assert "code_challenge_method=S256" in result.url

        s.expire_all()
        row = s.get(UserSessionORM, "pkce-tok")
        assert row is not None
        assert row.oauth_code_verifier  # non-empty string persisted
        assert len(row.oauth_code_verifier) >= 43  # RFC 7636 min length
    finally:
        s.close()


def test_user_connection_repo_preserves_refresh_token_on_silent_reauth():
    from app.user.repo import UserRepository

    s = _session()
    try:
        UserRepository(s).create("gc-user", "x" * 60)
        repo = UserConnectionRepository(s)
        first = repo.upsert(
            user_name="gc-user",
            provider="google_calendar",
            access_token="at-1",
            refresh_token="rt-1",
            token_uri="https://oauth2.googleapis.com/token",
            scopes=["openid"],
            expiry=None,
        )
        assert first.refresh_token == "rt-1"

        # Silent re-auth (no new refresh_token) must NOT clear the stored one.
        second = repo.upsert(
            user_name="gc-user",
            provider="google_calendar",
            access_token="at-2",
            refresh_token=None,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=["openid"],
            expiry=None,
        )
        assert second.refresh_token == "rt-1"
        assert second.access_token == "at-2"
    finally:
        s.close()


def test_calendar_action_falls_back_to_mock_when_unconfigured(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "")
    monkeypatch.setattr(settings, "google_client_secret", "")
    action = CalendarCreateEventAction()
    result = asyncio.run(
        action.execute(
            {
                "owner_name": "gc-user",
                "calendar_id": "primary",
                "title": "Mock",
                "start": "2026-04-19T10:00:00Z",
                "end": "2026-04-19T11:00:00Z",
            }
        )
    )
    assert result["source"] == "mock"
    assert result["status"] == "created"


def test_calendar_action_falls_back_when_user_not_connected(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "id")
    monkeypatch.setattr(settings, "google_client_secret", "secret")
    action = CalendarCreateEventAction()
    result = asyncio.run(
        action.execute(
            {
                "owner_name": "nobody-linked-yet",
                "calendar_id": "primary",
                "title": "No link",
                "start": "2026-04-19T10:00:00Z",
                "end": "2026-04-19T11:00:00Z",
            }
        )
    )
    assert result["source"] == "mock"
    assert result.get("note") == "fallback_mock_user_not_connected"


def test_calendar_action_uses_real_connector_when_linked(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "id")
    monkeypatch.setattr(settings, "google_client_secret", "secret")

    fake_created = {
        "id": "evt-xyz",
        "summary": "Real event",
        "start": {"dateTime": "2026-04-19T10:00:00Z"},
        "end": {"dateTime": "2026-04-19T11:00:00Z"},
        "htmlLink": "https://calendar.google.com/evt-xyz",
        "organizer": {"email": "linked@example.com"},
    }

    from app.user.repo import UserRepository

    s = _session()
    try:
        UserRepository(s).create("linked-user", "x" * 60)
        UserConnectionRepository(s).upsert(
            user_name="linked-user",
            provider="google_calendar",
            access_token="at",
            refresh_token="rt",
            token_uri="https://oauth2.googleapis.com/token",
            scopes=["openid"],
            expiry=None,
        )
        s.commit()
    finally:
        s.close()

    with patch("app.connectors.google_calendar.create_event", return_value=fake_created):
        result = asyncio.run(
            CalendarCreateEventAction().execute(
                {
                    "owner_name": "linked-user",
                    "calendar_id": "primary",
                    "title": "Real event",
                    "start": "2026-04-19T10:00:00Z",
                    "end": "2026-04-19T11:00:00Z",
                }
            )
        )

    assert result["source"] == "google_calendar"
    assert result["event"]["id"] == "evt-xyz"
    assert result["event"]["html_link"] == "https://calendar.google.com/evt-xyz"
