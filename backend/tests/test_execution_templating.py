"""Tests for the ``{{path}}`` template engine and its step-runner wiring.

Before this module existed, the builder advertised ``{{variable}}``
placeholders but the engine never expanded them — ``Send Email`` would
literally email ``{{previous_output.events}}`` as text. These tests pin
the contract that fixed that.
"""

from __future__ import annotations

from uuid import uuid4

from app.action.calendarListUpcomingAction import CalendarListUpcomingActionStep
from app.action.httpRequestAction import HttpRequestActionStep
from app.action.sendEmailAction import SendEmailActionStep
from app.execution.step_runner import build_execution_inputs
from app.execution.templating import render_template


class TestRenderTemplate:
    def test_plain_string_passes_through(self):
        assert render_template("hello", {}) == "hello"

    def test_dotted_path_resolves(self):
        ctx = {"previous_output": {"status": "ok", "count": 3}}
        assert (
            render_template("done: {{previous_output.status}}", ctx)
            == "done: ok"
        )

    def test_missing_path_renders_empty(self):
        # Key safety: a typo in the builder must not crash the run.
        assert render_template("x={{nope.nothere}}", {}) == "x="

    def test_integer_renders_as_digits(self):
        assert render_template("{{n}}", {"n": 42}) == "42"

    def test_list_of_dicts_renders_as_bullets(self):
        ctx = {
            "previous_output": {
                "events": [
                    {"title": "Standup", "start": "2026-04-20T09:00:00Z"},
                    {"title": "1:1 Alice"},
                ]
            }
        }
        out = render_template("{{previous_output.events}}", ctx)
        assert "- Standup" in out
        assert "- 1:1 Alice" in out

    def test_agenda_text_pass_through(self):
        # This is the happy-path a user actually writes in the body.
        ctx = {"previous_output": {"agenda_text": "- 09:00 · Standup\n- 11:00 · 1:1"}}
        body = render_template(
            "Today's agenda:\n{{previous_output.agenda_text}}", ctx
        )
        assert "Today's agenda:" in body
        assert "09:00 · Standup" in body
        assert "11:00 · 1:1" in body

    def test_whitespace_in_braces_tolerated(self):
        ctx = {"x": "hi"}
        assert render_template("{{  x  }}", ctx) == "hi"

    def test_list_index_access(self):
        ctx = {"events": [{"title": "first"}, {"title": "second"}]}
        assert render_template("{{events.1.title}}", ctx) == "second"

    def test_non_string_input_returned_unchanged(self):
        # build_execution_inputs should be able to pass arbitrary field
        # values through — only str templates get rendered.
        assert render_template(42, {}) == 42  # type: ignore[arg-type]
        assert render_template(None, {}) is None  # type: ignore[arg-type]


class TestBuildExecutionInputsRendersTemplates:
    """The real regression: without this wiring the user's email came out
    literally containing ``{{previous_output.events}}``."""

    def _prev(self):
        return {
            "status": "ok",
            "count": 2,
            "agenda_text": "- 09:00 Standup\n- 10:30 1:1 Alice",
        }

    def test_send_email_body_gets_rendered(self):
        step = SendEmailActionStep(
            name="email",
            step_order=0,
            to_template="me@example.com",
            subject_template="Agenda ({{previous_output.count}})",
            body_template="Today:\n{{previous_output.agenda_text}}",
        )
        inputs = build_execution_inputs(
            step,
            run_id=uuid4(),
            workflow_id=uuid4(),
            previous_output=self._prev(),
            owner_name="alice",
        )
        assert inputs["to"] == "me@example.com"
        assert inputs["subject"] == "Agenda (2)"
        assert "09:00 Standup" in inputs["body"]
        assert "{{" not in inputs["body"], (
            "template placeholder leaked into rendered body — users will see raw "
            "`{{previous_output.agenda_text}}` in the email."
        )

    def test_http_request_url_and_headers_get_rendered(self):
        step = HttpRequestActionStep(
            name="http",
            step_order=1,
            method="POST",
            url_template="https://example.com/hook?count={{previous_output.count}}",
            headers={"X-Count": "{{previous_output.count}}"},
            body_template='{"status":"{{previous_output.status}}"}',
        )
        inputs = build_execution_inputs(
            step,
            run_id=uuid4(),
            workflow_id=uuid4(),
            previous_output=self._prev(),
            owner_name="alice",
        )
        assert inputs["url"] == "https://example.com/hook?count=2"
        assert inputs["headers"]["X-Count"] == "2"
        assert inputs["body"] == '{"status":"ok"}'

    def test_calendar_list_upcoming_includes_window_hours(self):
        step = CalendarListUpcomingActionStep(
            name="list",
            step_order=0,
            window_hours=24,
        )
        inputs = build_execution_inputs(
            step,
            run_id=uuid4(),
            workflow_id=uuid4(),
            previous_output=None,
            owner_name="alice",
        )
        assert inputs["window_hours"] == 24
