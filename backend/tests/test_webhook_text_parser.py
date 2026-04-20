"""Slack-text duration parser.

The parser lets users write ``start+{{previous_output.parsed.duration}}``
in a Create Calendar Event step and have the event length track whatever
they typed into the slash command (``/block focus 30min``). Tests pin:

* the grammar accepted (single letter, plural, ``min``/``minute``, etc.)
* fallback behaviour when no duration is present
* that the parser only runs for payloads that actually expose a ``text``
  field — we don't want to invent ``parsed.duration`` for a GitHub push.
"""

from __future__ import annotations

import json

from app.api.router import _build_trigger_context, _parse_text_duration


class TestParseTextDuration:
    def test_canonical_slack_shape(self):
        r = _parse_text_duration("focus 30min")
        assert r == {
            "duration": "30m",
            "duration_minutes": 30,
            "subject": "focus",
            "has_duration": True,
        }

    def test_single_letter_unit_is_accepted(self):
        r = _parse_text_duration("deep work 45m")
        assert r["duration"] == "45m"
        assert r["duration_minutes"] == 45
        assert r["subject"] == "deep work"

    def test_space_between_number_and_unit(self):
        # Users copy-paste " 30 m" from other tools all the time; make
        # sure that trivial whitespace doesn't silently skip the match
        # and collapse to the 30-minute fallback.
        r = _parse_text_duration("lunch 30 m")
        assert r["has_duration"] is True
        assert r["duration"] == "30m"

    def test_hours_short_form(self):
        r = _parse_text_duration("long meeting 2h")
        assert r["duration"] == "2h"
        assert r["duration_minutes"] == 120
        assert r["subject"] == "long meeting"

    def test_hours_long_form(self):
        assert _parse_text_duration("review 1 hour")["duration"] == "1h"
        assert _parse_text_duration("review 3 hours")["duration"] == "3h"

    def test_days(self):
        r = _parse_text_duration("vacation 1d")
        assert r["duration"] == "1d"
        assert r["duration_minutes"] == 60 * 24

    def test_duration_at_start_of_text(self):
        # "/block 30m focus" should still parse and strip cleanly.
        r = _parse_text_duration("30m focus")
        assert r["duration"] == "30m"
        assert r["subject"] == "focus"

    def test_first_match_wins(self):
        # We intentionally don't sum "1h 30m" — keeps the grammar tiny
        # and auditable. Users who need 90 minutes can type "90m".
        r = _parse_text_duration("1h then 30m")
        assert r["duration"] == "1h"

    def test_fallback_when_no_duration(self):
        r = _parse_text_duration("focus")
        assert r == {
            "duration": "30m",
            "duration_minutes": 30,
            "subject": "focus",
            "has_duration": False,
        }

    def test_fallback_on_empty_text(self):
        r = _parse_text_duration("")
        assert r["duration"] == "30m"
        assert r["subject"] == ""
        assert r["has_duration"] is False

    def test_case_insensitive(self):
        assert _parse_text_duration("FOCUS 30MIN")["duration"] == "30m"
        assert _parse_text_duration("Deep 2 HOURS")["duration"] == "2h"

    def test_whitespace_collapsed_in_subject(self):
        # Stripping the duration must not leave double spaces — email
        # bodies using this as a subject shouldn't look mangled.
        r = _parse_text_duration("write   tests  30m  please")
        assert r["subject"] == "write tests please"


class TestBuildTriggerContextParsedField:
    def _build(self, raw_body: bytes, content_type: str) -> dict:
        return _build_trigger_context(
            normalized_path="/hooks/slack",
            method="POST",
            headers={"content-type": content_type},
            query={},
            raw_body=raw_body,
            content_type=content_type,
        )

    def test_slack_form_body_produces_parsed(self):
        ctx = self._build(
            b"text=focus+30min&command=%2Fblock",
            "application/x-www-form-urlencoded",
        )
        assert ctx["parsed"]["duration"] == "30m"
        assert ctx["parsed"]["duration_minutes"] == 30
        assert ctx["parsed"]["subject"] == "focus"

    def test_json_body_with_text_field_also_parses(self):
        # Generic webhooks that happen to adopt the Slack shape
        # (e.g. a test harness sending JSON) still benefit — keeps the
        # parser field-driven, not protocol-driven.
        ctx = self._build(
            json.dumps({"text": "deep work 1h"}).encode(),
            "application/json",
        )
        assert ctx["parsed"]["duration"] == "1h"

    def test_json_body_without_text_field_has_empty_parsed(self):
        # GitHub-style payloads must not sprout spurious duration fields.
        # Templates referencing ``parsed.duration`` would resolve empty,
        # which keeps the failure visible (the Calendar step will error
        # instead of silently shipping a 30-minute event).
        ctx = self._build(
            json.dumps({"zen": "Keep it logically awesome."}).encode(),
            "application/json",
        )
        assert ctx["parsed"] == {}

    def test_empty_body_has_empty_parsed(self):
        ctx = self._build(b"", "application/json")
        assert ctx["parsed"] == {}

    def test_unparseable_body_has_empty_parsed(self):
        # Malformed JSON with a text-like Content-Type shouldn't crash
        # the ingress nor accidentally invent a 30m duration.
        ctx = self._build(b"not json", "application/json")
        assert ctx["parsed"] == {}
