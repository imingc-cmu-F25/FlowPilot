"""Regression tests for the ``first_seen_at`` semantics on cached events.

The calendar_event trigger uses ``CachedCalendarEventRepository.find_since``
to detect genuinely new events. Before this was split from ``synced_at``,
every 10-minute Google Calendar sync would rewrite every event's
``synced_at`` and cause the trigger to re-fire on every cached event
forever — one email per matching event per sync tick. These tests pin
the contract that keeps that bug from regressing.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.connectors.repo import CachedCalendarEventRepository
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


def _seed_user(session, name: str) -> None:
    from app.user.repo import UserRepository

    UserRepository(session).create(name, "x" * 60)


def _upsert(session, *, user: str, event_id: str, title: str = "E") -> None:
    CachedCalendarEventRepository(session).upsert(
        user_name=user,
        calendar_id="primary",
        provider_event_id=event_id,
        title=title,
        description=None,
        start=datetime.now(UTC) + timedelta(hours=1),
        end=datetime.now(UTC) + timedelta(hours=2),
        status="confirmed",
        html_link=None,
        raw=None,
    )


def test_resync_does_not_resurface_event_in_find_since():
    """After insert, re-upserting the same (user, event_id) must NOT make
    ``find_since`` report it again. This is the core regression: a sync
    tick that touches every event should not re-trigger the workflow.
    """
    s = _session()
    try:
        _seed_user(s, "fs-user")
        _upsert(s, user="fs-user", event_id="only-once")
        s.commit()

        # Simulate a later sync cycle bumping synced_at on the same row.
        # The trigger cutoff for "new" is "after this moment" — so we
        # capture it AFTER the original insert but BEFORE the re-upsert.
        import time

        time.sleep(0.01)
        cutoff = datetime.now(UTC)
        time.sleep(0.01)

        _upsert(s, user="fs-user", event_id="only-once", title="E-renamed")
        s.commit()

        rows = CachedCalendarEventRepository(s).find_since(
            user_name="fs-user", since=cutoff
        )
        assert rows == [], (
            "Re-upserted event showed up in find_since — "
            "the calendar_event trigger will spam once per sync."
        )
    finally:
        s.close()


def test_genuinely_new_event_shows_up_in_find_since():
    """Sanity check: a brand-new event inserted after ``since`` must be
    returned by ``find_since``."""
    s = _session()
    try:
        _seed_user(s, "fs-user2")
        cutoff = datetime.now(UTC) - timedelta(seconds=1)
        _upsert(s, user="fs-user2", event_id="brand-new")
        s.commit()

        rows = CachedCalendarEventRepository(s).find_since(
            user_name="fs-user2", since=cutoff
        )
        ids = [r.provider_event_id for r in rows]
        assert ids == ["brand-new"]
    finally:
        s.close()
