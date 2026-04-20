"""Time-token resolution for CalendarCreateEventAction.

This is the feature that lets Slack-webhook demos actually be dynamic:
``/break`` at 10:30 turns into a calendar event at 10:35 without any
hand-written ISO 8601. The rules are small on purpose (``now``,
``now+30m``, ``start+30m``) so the grammar is easy to audit and doesn't
grow into a second template engine.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.action.calendarAction import (
    CalendarActionStep,
    CalendarCreateEventAction,
    _resolve_time_token,
)
from app.execution.step_runner import build_execution_inputs

FIXED_NOW = datetime(2026, 4, 20, 15, 30, 0, tzinfo=UTC)


class TestResolveTimeToken:
    def test_plain_iso_passes_through_untouched(self):
        # Users who still hand-write ISO (e.g. chained after List Upcoming
        # Events) must not be mangled by the resolver.
        assert (
            _resolve_time_token("2026-05-01T09:00:00+00:00", clock=FIXED_NOW)
            == "2026-05-01T09:00:00+00:00"
        )

    def test_empty_string_passes_through(self):
        assert _resolve_time_token("", clock=FIXED_NOW) == ""

    def test_bare_now_returns_clock_iso(self):
        assert _resolve_time_token("now", clock=FIXED_NOW) == FIXED_NOW.isoformat()

    def test_now_is_case_insensitive(self):
        assert _resolve_time_token("NOW", clock=FIXED_NOW) == FIXED_NOW.isoformat()

    @pytest.mark.parametrize(
        ("token", "delta"),
        [
            ("now+5m", timedelta(minutes=5)),
            ("now+30m", timedelta(minutes=30)),
            ("now-15m", -timedelta(minutes=15)),
            ("now+2h", timedelta(hours=2)),
            ("now-1h", -timedelta(hours=1)),
            ("now+1d", timedelta(days=1)),
        ],
    )
    def test_now_with_offset(self, token: str, delta: timedelta):
        expected = (FIXED_NOW + delta).isoformat()
        assert _resolve_time_token(token, clock=FIXED_NOW) == expected

    def test_whitespace_inside_token_is_tolerated(self):
        # Users copy-pasting from email / Slack occasionally leave a
        # stray space ("now + 30m"). Accepting it avoids an unhelpful
        # "falls back to verbatim" silent bug at run-time.
        assert (
            _resolve_time_token("  now + 30m ", clock=FIXED_NOW)
            == (FIXED_NOW + timedelta(minutes=30)).isoformat()
        )

    def test_start_plus_offset_uses_start_reference(self):
        start = datetime(2026, 4, 20, 10, 0, 0, tzinfo=UTC)
        assert (
            _resolve_time_token("start+30m", start_reference=start, clock=FIXED_NOW)
            == (start + timedelta(minutes=30)).isoformat()
        )

    def test_start_without_reference_passes_through(self):
        # "start+30m" on the start field itself is meaningless; we refuse
        # to silently resolve it to "now" since that would mask a
        # misconfigured workflow.
        assert (
            _resolve_time_token("start+30m", start_reference=None, clock=FIXED_NOW)
            == "start+30m"
        )

    def test_unknown_token_passes_through(self):
        # Anything that isn't now/start stays verbatim — protects
        # future non-token values (arbitrary user strings) from being
        # mangled by the resolver.
        assert _resolve_time_token("tomorrow", clock=FIXED_NOW) == "tomorrow"


class TestCalendarActionExecuteResolvesTokens:
    """End-to-end: execute() must resolve tokens before the mock / API call."""

    def _run(self, start: str, end: str) -> dict:
        action = CalendarCreateEventAction()
        inputs = {
            "calendar_id": "primary",
            "title": "Focus block",
            "start": start,
            "end": end,
            # No owner_name → always take the mock branch, which is
            # exactly what we want for deterministic tests.
            "owner_name": None,
        }
        return asyncio.run(action.execute(inputs))

    def test_mock_event_contains_resolved_iso_times(self):
        with patch("app.action.calendarAction.datetime") as mock_dt:
            # Pin ``datetime.now`` while preserving ``fromisoformat``
            # so the resolver can still parse the ISO it just produced
            # to derive ``start+30m``. Cleanest way to freeze the clock
            # without pulling in freezegun.
            mock_dt.now.return_value = FIXED_NOW
            mock_dt.fromisoformat = datetime.fromisoformat
            result = self._run("now+5m", "start+30m")
        event = result["event"]
        assert event["start"] == (FIXED_NOW + timedelta(minutes=5)).isoformat()
        assert event["end"] == (
            FIXED_NOW + timedelta(minutes=5) + timedelta(minutes=30)
        ).isoformat()

    def test_literal_iso_is_forwarded_unchanged(self):
        result = self._run(
            "2026-05-01T09:00:00+00:00",
            "2026-05-01T09:30:00+00:00",
        )
        assert result["event"]["start"] == "2026-05-01T09:00:00+00:00"
        assert result["event"]["end"] == "2026-05-01T09:30:00+00:00"

    def test_start_offset_tracks_timezone_aware_start(self):
        # Start in Asia/Taipei offset; end uses start+1h. The resolver
        # should preserve the offset on the end field so the calendar
        # API doesn't accidentally shift the event into UTC.
        tpe = timezone(timedelta(hours=8))
        start_iso = datetime(2026, 4, 20, 15, 30, tzinfo=tpe).isoformat()
        result = self._run(start_iso, "start+1h")
        assert result["event"]["end"] == datetime(
            2026, 4, 20, 16, 30, tzinfo=tpe
        ).isoformat()


class TestBuildExecutionInputsInjectsNow:
    """``{{now}}`` must be available to every action's templates."""

    def test_now_is_iso_utc_in_context(self):
        # Use a step that exposes the rendered template directly (email).
        from app.action.sendEmailAction import SendEmailActionStep

        step = SendEmailActionStep(
            step_order=1,
            name="Echo now",
            to_template="user@example.com",
            subject_template="Report",
            body_template="generated at {{now}}",
        )
        result = build_execution_inputs(
            step,
            run_id=uuid4(),
            workflow_id=uuid4(),
            previous_output=None,
        )
        body = result["body"]
        assert body.startswith("generated at ")
        # Must be an ISO 8601 string with a UTC offset so downstream
        # consumers (email, HTTP, Calendar) can parse unambiguously.
        iso = body.removeprefix("generated at ")
        parsed = datetime.fromisoformat(iso)
        assert parsed.tzinfo is not None
        assert parsed.utcoffset() == timedelta(0)

    def test_now_is_also_available_to_calendar_templates(self):
        step = CalendarActionStep(
            step_order=1,
            name="Now-based event",
            calendar_id="primary",
            title_template="{{now}}",
            start_mapping="now",
            end_mapping="now+15m",
        )
        result = build_execution_inputs(
            step,
            run_id=uuid4(),
            workflow_id=uuid4(),
            previous_output=None,
        )
        # Title goes through templating → rendered to an ISO string.
        datetime.fromisoformat(result["title"])
        # Start/end stay as tokens (they're resolved inside execute()).
        assert result["start"] == "now"
        assert result["end"] == "now+15m"
