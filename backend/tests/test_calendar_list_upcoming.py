"""Tests for the Calendar.ListUpcoming action and the upcoming-only cache filter."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from app.action.action import ActionStepFactory, ActionType, StepSpec
from app.action.calendarListUpcomingAction import (
    CalendarListUpcomingAction,
    CalendarListUpcomingActionStep,
)
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


def _seed_user(session, name: str = "lister") -> None:
    from app.user.repo import UserRepository

    UserRepository(session).create(name, "x" * 60)


def _add_event(
    session,
    *,
    user_name: str,
    provider_event_id: str,
    title: str,
    start: datetime | None,
    end: datetime | None,
    calendar_id: str = "primary",
) -> None:
    CachedCalendarEventRepository(session).upsert(
        user_name=user_name,
        calendar_id=calendar_id,
        provider_event_id=provider_event_id,
        title=title,
        description=None,
        start=start,
        end=end,
        status="confirmed",
        html_link=None,
        raw=None,
    )


class TestUpcomingFilter:
    def test_past_events_are_hidden_by_default(self):
        s = _session()
        try:
            _seed_user(s)
            now = datetime.now(UTC)
            _add_event(
                s,
                user_name="lister",
                provider_event_id="past-1",
                title="Done",
                start=now - timedelta(days=2),
                end=now - timedelta(days=2, hours=-1),  # ended ~1h after start
            )
            _add_event(
                s,
                user_name="lister",
                provider_event_id="future-1",
                title="Upcoming",
                start=now + timedelta(hours=1),
                end=now + timedelta(hours=2),
            )
            s.commit()

            rows = CachedCalendarEventRepository(s).list_for_user("lister")
            titles = [r.title for r in rows]
            assert titles == ["Upcoming"]
        finally:
            s.close()

    def test_include_past_when_requested(self):
        s = _session()
        try:
            _seed_user(s)
            now = datetime.now(UTC)
            _add_event(
                s,
                user_name="lister",
                provider_event_id="past-1",
                title="Done",
                start=now - timedelta(days=2),
                end=now - timedelta(days=2) + timedelta(hours=1),
            )
            _add_event(
                s,
                user_name="lister",
                provider_event_id="future-1",
                title="Upcoming",
                start=now + timedelta(hours=1),
                end=now + timedelta(hours=2),
            )
            s.commit()

            rows = CachedCalendarEventRepository(s).list_for_user(
                "lister", upcoming_only=False
            )
            assert len(rows) == 2
        finally:
            s.close()

    def test_in_progress_event_counts_as_upcoming(self):
        """An event that started 10 min ago but ends in 50 min should still appear."""
        s = _session()
        try:
            _seed_user(s)
            now = datetime.now(UTC)
            _add_event(
                s,
                user_name="lister",
                provider_event_id="inprogress",
                title="Happening now",
                start=now - timedelta(minutes=10),
                end=now + timedelta(minutes=50),
            )
            s.commit()

            rows = CachedCalendarEventRepository(s).list_for_user("lister")
            assert len(rows) == 1
            assert rows[0].title == "Happening now"
        finally:
            s.close()


class TestCalendarListUpcomingStep:
    def test_factory_builds_step(self):
        step = ActionStepFactory.create(
            StepSpec(
                action_type=ActionType.CALENDAR_LIST_UPCOMING,
                name="list",
                step_order=0,
                parameters={"max_results": 5, "title_contains": "standup"},
            )
        )
        assert isinstance(step, CalendarListUpcomingActionStep)
        assert step.max_results == 5
        assert step.title_contains == "standup"

    def test_validate_rejects_out_of_range_max_results(self):
        step = CalendarListUpcomingActionStep(
            name="list", step_order=0, max_results=0
        )
        try:
            step.validate_step()
        except ValueError:
            return
        raise AssertionError("expected ValueError")


class TestCalendarListUpcomingAction:
    def test_execute_returns_cached_upcoming_events(self):
        s = _session()
        try:
            _seed_user(s, "exec-user")
            now = datetime.now(UTC)
            _add_event(
                s,
                user_name="exec-user",
                provider_event_id="fut",
                title="Standup with team",
                start=now + timedelta(hours=1),
                end=now + timedelta(hours=1, minutes=30),
            )
            _add_event(
                s,
                user_name="exec-user",
                provider_event_id="past",
                title="Yesterday sync",
                start=now - timedelta(days=1),
                end=now - timedelta(days=1) + timedelta(hours=1),
            )
            s.commit()
        finally:
            s.close()

        action = CalendarListUpcomingAction()
        result = asyncio.run(
            action.execute({"owner_name": "exec-user", "max_results": 10})
        )
        assert result["status"] == "ok"
        assert result["count"] == 1
        assert result["events"][0]["title"] == "Standup with team"
        assert result["events"][0]["id"] == "fut"
        assert result["source"] == "cache"

    def test_execute_filters_by_title_contains(self):
        s = _session()
        try:
            _seed_user(s, "filt-user")
            now = datetime.now(UTC)
            _add_event(
                s,
                user_name="filt-user",
                provider_event_id="a",
                title="Weekly standup",
                start=now + timedelta(hours=1),
                end=now + timedelta(hours=2),
            )
            _add_event(
                s,
                user_name="filt-user",
                provider_event_id="b",
                title="1:1 with Alice",
                start=now + timedelta(hours=3),
                end=now + timedelta(hours=4),
            )
            s.commit()
        finally:
            s.close()

        action = CalendarListUpcomingAction()
        result = asyncio.run(
            action.execute(
                {
                    "owner_name": "filt-user",
                    "max_results": 10,
                    "title_contains": "standup",
                }
            )
        )
        assert result["count"] == 1
        assert result["events"][0]["title"] == "Weekly standup"

    def test_execute_returns_empty_envelope_without_owner(self):
        # Without owner_name the action should succeed with an empty list
        # (engine always supplies owner_name, this is a guard for unit tests).
        with patch("app.db.session.new_session") as m:
            action = CalendarListUpcomingAction()
            result = asyncio.run(action.execute({"owner_name": None}))
            assert result == {
                "status": "ok",
                "count": 0,
                "events": [],
                "agenda_text": "(no upcoming events)",
                "source": "empty",
            }
            m.assert_not_called()

    def test_window_hours_caps_events_to_time_frame(self):
        """window_hours=24 must hide an event starting three days from now."""
        s = _session()
        try:
            _seed_user(s, "win-user")
            now = datetime.now(UTC)
            _add_event(
                s,
                user_name="win-user",
                provider_event_id="soon",
                title="Today lunch",
                start=now + timedelta(hours=3),
                end=now + timedelta(hours=4),
            )
            _add_event(
                s,
                user_name="win-user",
                provider_event_id="later",
                title="Next week meeting",
                start=now + timedelta(days=3),
                end=now + timedelta(days=3, hours=1),
            )
            s.commit()
        finally:
            s.close()

        action = CalendarListUpcomingAction()
        result = asyncio.run(
            action.execute(
                {
                    "owner_name": "win-user",
                    "max_results": 10,
                    "window_hours": 24,
                }
            )
        )
        titles = [e["title"] for e in result["events"]]
        assert titles == ["Today lunch"]
        assert "Today lunch" in result["agenda_text"]

    def test_agenda_text_is_bulleted_and_human_readable(self):
        s = _session()
        try:
            _seed_user(s, "fmt-user")
            now = datetime.now(UTC)
            _add_event(
                s,
                user_name="fmt-user",
                provider_event_id="e1",
                title="Standup",
                start=now + timedelta(hours=1),
                end=now + timedelta(hours=1, minutes=30),
            )
            s.commit()
        finally:
            s.close()

        action = CalendarListUpcomingAction()
        result = asyncio.run(
            action.execute({"owner_name": "fmt-user", "max_results": 5})
        )
        # Don't assert the exact date format (depends on locale / now()),
        # but the bullet + title shape must be stable.
        assert result["agenda_text"].startswith("- ")
        assert "Standup" in result["agenda_text"]
