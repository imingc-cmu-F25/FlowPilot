"""Tests for action step configs, factory, and runtime executors."""

import asyncio

import pytest
from app.action.action import (
    ActionStepFactory,
    ActionType,
    CalendarCreateEventActionStep,
    HttpRequestAction,
    HttpRequestActionStep,
    SendEmailAction,
    SendEmailActionStep,
    StepSpec,
)
from app.action.actionRegistry import ActionRegistry


class TestHttpRequestActionStep:
    def test_valid_step_passes_validation(self):
        step = HttpRequestActionStep(
            name="Call API",
            step_order=0,
            url_template="https://api.example.com/data",
        )
        step.validate_step()  # should not raise

    def test_defaults_method_to_get(self):
        step = HttpRequestActionStep(name="x", step_order=0, url_template="https://x.com")
        assert step.method == "GET"

    def test_empty_url_template_raises(self):
        step = HttpRequestActionStep(name="x", step_order=0, url_template="")
        with pytest.raises(ValueError, match="url_template is required"):
            step.validate_step()

    def test_invalid_method_raises(self):
        step = HttpRequestActionStep(
            name="x", step_order=0, url_template="https://x.com", method="PURGE"
        )
        with pytest.raises(ValueError, match="Unsupported HTTP method"):
            step.validate_step()

    def test_all_valid_methods_accepted(self):
        for method in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            step = HttpRequestActionStep(
                name="x", step_order=0, url_template="https://x.com", method=method
            )
            step.validate_step()  # should not raise

    def test_action_type_discriminator(self):
        step = HttpRequestActionStep(name="x", step_order=0, url_template="https://x.com")
        assert step.action_type == ActionType.HTTP_REQUEST

    def test_step_id_auto_generated_and_unique(self):
        s1 = HttpRequestActionStep(name="x", step_order=0, url_template="https://x.com")
        s2 = HttpRequestActionStep(name="x", step_order=0, url_template="https://x.com")
        assert s1.step_id != s2.step_id


class TestSendEmailActionStep:
    """
    Tests for SendEmailActionStep validation logic, including required fields
    and action_type discriminator.
    """

    def test_valid_step_passes_validation(self):
        step = SendEmailActionStep(
            name="Send",
            step_order=0,
            to_template="a@b.com",
            subject_template="Hi",
            body_template="Hello",
        )
        step.validate_step()  # should not raise

    def test_empty_to_template_raises(self):
        """
        Empty to_template causes validation to fail.
        """
        step = SendEmailActionStep(
            name="Send", step_order=0, to_template="", subject_template="Hi", body_template="x"
        )
        with pytest.raises(ValueError, match="to_template is required"):
            step.validate_step()

    def test_empty_subject_template_raises(self):
        """
        Empty subject_template causes validation to fail.
        """
        step = SendEmailActionStep(
            name="Send",
            step_order=0,
            to_template="a@b.com",
            subject_template="",
            body_template="x",
        )
        with pytest.raises(ValueError, match="subject_template is required"):
            step.validate_step()

    def test_action_type_discriminator(self):
        """
        The action_type discriminator correctly identifies SendEmailActionStep.
        """
        step = SendEmailActionStep(
            name="x", step_order=0, to_template="a@b.com", subject_template="s", body_template="b"
        )
        assert step.action_type == ActionType.SEND_EMAIL


class TestCalendarCreateEventActionStep:
    def test_valid_step_passes_validation(self):
        """
A CalendarCreateEventActionStep with all required fields should pass validation.
        """
        step = CalendarCreateEventActionStep(
            name="Create event",
            step_order=0,
            calendar_id="primary",
            title_template="Meeting: {{name}}",
            start_mapping="$.trigger.start",
            end_mapping="$.trigger.end",
        )
        step.validate_step()  # should not raise

    def test_empty_calendar_id_raises(self):
        """
        Empty calendar_id causes validation to fail.
        """
        step = CalendarCreateEventActionStep(
            name="x",
            step_order=0,
            calendar_id="",
            title_template="Meeting",
            start_mapping="$.start",
            end_mapping="$.end",
        )
        with pytest.raises(ValueError, match="calendar_id is required"):
            step.validate_step()

    def test_empty_title_template_raises(self):
        """
        Empty title_template causes validation to fail.
        """
        step = CalendarCreateEventActionStep(
            name="x",
            step_order=0,
            calendar_id="primary",
            title_template="",
            start_mapping="$.start",
            end_mapping="$.end",
        )
        with pytest.raises(ValueError, match="title_template is required"):
            step.validate_step()

    def test_action_type_discriminator(self):
        """
        The action_type discriminator correctly identifies CalendarCreateEventActionStep.
        """
        step = CalendarCreateEventActionStep(
            name="x",
            step_order=0,
            calendar_id="primary",
            title_template="T",
            start_mapping="$.s",
            end_mapping="$.e",
        )
        assert step.action_type == ActionType.CALENDAR_CREATE_EVENT


class TestActionStepFactory:
    def test_creates_http_request_step(self):
        """
        A HttpRequestActionStep with all required fields should pass validation.
        """
        spec = StepSpec(
            action_type=ActionType.HTTP_REQUEST,
            name="Call",
            step_order=0,
            parameters={"url_template": "https://api.example.com"},
        )
        step = ActionStepFactory.create(spec)
        assert isinstance(step, HttpRequestActionStep)
        assert step.url_template == "https://api.example.com"

    def test_creates_send_email_step(self):
        """
        A SendEmailActionStep with all required fields should pass validation.
        """
        spec = StepSpec(
            action_type=ActionType.SEND_EMAIL,
            name="Email",
            step_order=1,
            parameters={
                "to_template": "a@b.com",
                "subject_template": "Hi",
                "body_template": "Hello",
            },
        )
        step = ActionStepFactory.create(spec)
        assert isinstance(step, SendEmailActionStep)
        assert step.to_template == "a@b.com"

    def test_creates_calendar_step(self):
        spec = StepSpec(
            action_type=ActionType.CALENDAR_CREATE_EVENT,
            name="Cal",
            step_order=2,
            parameters={
                "calendar_id": "primary",
                "title_template": "T",
                "start_mapping": "$.s",
                "end_mapping": "$.e",
            },
        )
        step = ActionStepFactory.create(spec)
        assert isinstance(step, CalendarCreateEventActionStep)

    def test_step_order_preserved_from_spec(self):
        spec = StepSpec(
            action_type=ActionType.HTTP_REQUEST,
            name="x",
            step_order=42,
            parameters={"url_template": "https://x.com"},
        )
        step = ActionStepFactory.create(spec)
        assert step.step_order == 42

    def test_unknown_action_type_raises(self):
        from pydantic import ValidationError as PydanticValidationError
        with pytest.raises((ValueError, KeyError, PydanticValidationError)):
            spec = StepSpec(action_type="nonexistent", name="x", step_order=0)  # type: ignore[arg-type]
            ActionStepFactory.create(spec)

    def test_invalid_step_fields_raise_on_create(self):
        # Factory calls validate_step(), so invalid params propagate
        spec = StepSpec(
            action_type=ActionType.HTTP_REQUEST,
            name="x",
            step_order=0,
            parameters={"url_template": ""},  # empty URL
        )
        with pytest.raises(ValueError, match="url_template is required"):
            ActionStepFactory.create(spec)
        

class TestActionStepRoundTrip:
    def test_http_step_serializes_and_restores(self):
        from typing import Annotated

        from pydantic import BaseModel, Field

        ActionStepUnion = Annotated[
            HttpRequestActionStep | SendEmailActionStep | CalendarCreateEventActionStep,
            Field(discriminator="action_type"),
        ]

        class Wrapper(BaseModel):
            steps: list[ActionStepUnion]  # type: ignore[valid-type]

        steps = [
            HttpRequestActionStep(name="A", step_order=0, url_template="https://a.com"),
            SendEmailActionStep(
                name="B",
                step_order=1,
                to_template="x@y.com",
                subject_template="s",
                body_template="b",
            ),
        ]
        w = Wrapper(steps=steps)
        restored = Wrapper.model_validate(w.model_dump(mode="json"))
        assert isinstance(restored.steps[0], HttpRequestActionStep)
        assert isinstance(restored.steps[1], SendEmailActionStep)
        assert restored.steps[0].url_template == "https://a.com"


class TestActionRegistry:
    def test_send_email_is_registered(self):
        schema = ActionRegistry.get("send_email").schema
        assert schema.id == "send_email"

    def test_http_request_is_registered(self):
        schema = ActionRegistry.get("http_request").schema
        assert schema.id == "http_request"

    def test_list_schemas_returns_all(self):
        schemas = ActionRegistry.list_schemas()
        ids = {s.id for s in schemas}
        assert "send_email" in ids
        assert "http_request" in ids

    def test_unknown_id_raises_key_error(self):
        with pytest.raises(KeyError):
            ActionRegistry.get("does_not_exist")


class TestSendEmailAction:
    def test_execute_returns_sent_status(self):
        from unittest.mock import MagicMock, patch

        mock_smtp = MagicMock()
        mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp.__exit__ = MagicMock(return_value=False)

        with patch("smtplib.SMTP", return_value=mock_smtp):
            action = SendEmailAction()
            result = asyncio.run(
                action.execute({"to": "a@b.com", "subject": "Hi", "body": "Hello"})
            )

        assert result["status"] == "sent"
        assert result["to"] == "a@b.com"
        mock_smtp.send_message.assert_called_once()

    def test_schema_connector_is_smtp(self):
        assert SendEmailAction.schema.connector_id == "smtp"


class TestHttpRequestAction:
    def test_schema_has_required_fields(self):
        fields = {f["name"] for f in HttpRequestAction.schema.config_fields}
        assert "method" in fields
        assert "url" in fields
