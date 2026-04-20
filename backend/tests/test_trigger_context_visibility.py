"""``{{trigger.*}}`` must be visible to every step, not just step 1.

Before this contract existed, inserting an intermediate HTTP / List
Upcoming Events step between a Slack webhook trigger and a
Create Calendar Event step silently wiped the Slack payload out of the
template context, producing events with empty start/end fields and a
400 Bad Request from Google Calendar. These tests pin that any step in
the pipeline can still reach ``trigger.body.*`` / ``trigger.parsed.*``.
"""

from __future__ import annotations

from uuid import uuid4

from app.action.httpRequestAction import HttpRequestActionStep
from app.action.sendEmailAction import SendEmailActionStep
from app.execution.step_runner import build_execution_inputs


class TestTriggerKeyOnEveryStep:
    def _trigger_payload(self) -> dict:
        return {
            "source": "webhook",
            "body": {"text": "focus 30min", "user_name": "miles"},
            "parsed": {
                "duration": "30m",
                "duration_minutes": 30,
                "subject": "focus",
                "has_duration": True,
            },
        }

    def test_trigger_visible_from_step_one(self):
        step = SendEmailActionStep(
            step_order=1,
            name="Notify on break",
            to_template="miles@example.com",
            subject_template="Break: {{trigger.parsed.subject}}",
            body_template="You typed {{trigger.body.text}}",
        )
        result = build_execution_inputs(
            step,
            run_id=uuid4(),
            workflow_id=uuid4(),
            previous_output=self._trigger_payload(),
            trigger_context=self._trigger_payload(),
        )
        assert result["subject"] == "Break: focus"
        assert result["body"] == "You typed focus 30min"

    def test_trigger_still_visible_when_previous_output_is_a_different_shape(self):
        # Exactly the scenario that broke on real workflows: an HTTP
        # Request step in between. ``previous_output`` is the HTTP
        # response (``{status_code, body}``) but ``trigger`` is still
        # the original Slack payload.
        http_like_previous = {
            "status_code": 200,
            "body": "This URL has no default content configured.",
        }
        step = SendEmailActionStep(
            step_order=2,
            name="Notify after HTTP probe",
            to_template="miles@example.com",
            subject_template="Break: {{trigger.parsed.subject}}",
            body_template=(
                "Duration: {{trigger.parsed.duration}} — HTTP status:"
                " {{previous_output.status_code}}"
            ),
        )
        result = build_execution_inputs(
            step,
            run_id=uuid4(),
            workflow_id=uuid4(),
            previous_output=http_like_previous,
            trigger_context=self._trigger_payload(),
        )
        assert result["subject"] == "Break: focus"
        assert result["body"] == "Duration: 30m — HTTP status: 200"

    def test_trigger_missing_renders_empty_not_crash(self):
        # Cron / custom triggers pass ``trigger_context=None``. Templates
        # referencing ``trigger.*`` must silently render as empty rather
        # than crashing the step — matches the existing ``previous_output``
        # safety contract.
        step = SendEmailActionStep(
            step_order=1,
            name="Daily digest",
            to_template="miles@example.com",
            subject_template="Daily digest",
            body_template="Slack text: '{{trigger.body.text}}'",
        )
        result = build_execution_inputs(
            step,
            run_id=uuid4(),
            workflow_id=uuid4(),
            previous_output=None,
            trigger_context=None,
        )
        assert result["body"] == "Slack text: ''"

    def test_http_step_body_can_template_trigger(self):
        # Smoke-check it works for actions other than email — HTTP body
        # must resolve ``{{trigger.body.text}}`` so users can forward the
        # Slack command text to a downstream API.
        step = HttpRequestActionStep(
            step_order=2,
            name="Forward to logger",
            method="POST",
            url_template="https://example.com/log",
            headers={"x-subject": "{{trigger.parsed.subject}}"},
            body_template='{"text": "{{trigger.body.text}}"}',
        )
        result = build_execution_inputs(
            step,
            run_id=uuid4(),
            workflow_id=uuid4(),
            previous_output={"status_code": 200},  # from a prior step
            trigger_context=self._trigger_payload(),
        )
        assert result["headers"]["x-subject"] == "focus"
        assert result["body"] == '{"text": "focus 30min"}'


class TestCalendarResolvesTriggerDuration:
    """End-to-end: calendar step 2 can still build ``start+30m`` via trigger."""

    def test_end_template_resolves_via_trigger_key(self):
        # We only need to verify the *template-rendered* end value here;
        # the time-token resolver itself is covered in
        # test_calendar_time_tokens.py.
        from app.action.calendarAction import CalendarActionStep

        step = CalendarActionStep(
            step_order=2,
            name="Create break",
            calendar_id="primary",
            title_template="Focus: {{trigger.parsed.subject}}",
            start_mapping="now+5m",
            end_mapping="start+{{trigger.parsed.duration}}",
        )
        result = build_execution_inputs(
            step,
            run_id=uuid4(),
            workflow_id=uuid4(),
            previous_output={"status_code": 200, "body": "..."},
            trigger_context={
                "parsed": {
                    "duration": "45m",
                    "duration_minutes": 45,
                    "subject": "deep work",
                    "has_duration": True,
                }
            },
        )
        # Template rendering happens in build_execution_inputs; the
        # action itself resolves ``start+45m`` to an ISO string later.
        assert result["title"] == "Focus: deep work"
        assert result["start"] == "now+5m"
        assert result["end"] == "start+45m"
