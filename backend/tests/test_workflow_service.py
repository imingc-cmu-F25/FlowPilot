"""Tests for WorkflowService (Director) and WorkflowValidator."""

import pytest
from uuid import uuid4

from app.action.action import ActionType, StepSpec
from app.trigger.trigger import TriggerSpec, TriggerType
from app.workflow.service import CreateWorkflowCommand, UpdateWorkflowCommand, WorkflowService
from app.workflow.validator import validate_workflow
from app.workflow.workflow import WorkflowDefinitionBuilder, WorkflowStatus


def make_service() -> WorkflowService:
    return WorkflowService(WorkflowDefinitionBuilder())


TIME_SPEC = TriggerSpec(type=TriggerType.TIME, parameters={"trigger_at": "2026-05-01T09:00:00+00:00"})
WEBHOOK_SPEC = TriggerSpec(type=TriggerType.WEBHOOK, parameters={"path": "/hooks/test"})

EMAIL_STEP = StepSpec(
    action_type=ActionType.SEND_EMAIL,
    name="Send report",
    step_order=0,
    parameters={
        "to_template": "a@b.com",
        "subject_template": "Report",
        "body_template": "Body",
    },
)

HTTP_STEP = StepSpec(
    action_type=ActionType.HTTP_REQUEST,
    name="Fetch data",
    step_order=1,
    parameters={"url_template": "https://api.example.com"},
)


def base_create_cmd(**overrides) -> CreateWorkflowCommand:
    defaults = dict(
        owner_id=uuid4(),
        name="My Workflow",
        trigger=TIME_SPEC,
        steps=[EMAIL_STEP],
    )
    return CreateWorkflowCommand(**{**defaults, **overrides})


#  WorkflowService.create_workflow 

class TestWorkflowServiceCreate:
    def test_returns_workflow_definition(self):
        svc = make_service()
        wf = svc.create_workflow(base_create_cmd())
        assert wf.name == "My Workflow"

    def test_owner_id_set_correctly(self):
        owner = uuid4()
        wf = make_service().create_workflow(base_create_cmd(owner_id=owner))
        assert wf.owner_id == owner

    def test_trigger_type_stored(self):
        wf = make_service().create_workflow(base_create_cmd(trigger=TIME_SPEC))
        assert wf.trigger.type == TriggerType.TIME

    def test_webhook_trigger_stored(self):
        wf = make_service().create_workflow(base_create_cmd(trigger=WEBHOOK_SPEC))
        assert wf.trigger.type == TriggerType.WEBHOOK

    def test_steps_stored_in_order(self):
        cmd = base_create_cmd(steps=[HTTP_STEP, EMAIL_STEP])
        wf = make_service().create_workflow(cmd)
        assert wf.steps[0].step_order == 0
        assert wf.steps[1].step_order == 1

    def test_default_status_is_draft(self):
        wf = make_service().create_workflow(base_create_cmd())
        assert wf.status == WorkflowStatus.DRAFT

    def test_enabled_false_by_default(self):
        wf = make_service().create_workflow(base_create_cmd())
        assert wf.enabled is False

    def test_enabled_true_when_set(self):
        wf = make_service().create_workflow(base_create_cmd(enabled=True))
        assert wf.enabled is True

    def test_description_stored(self):
        wf = make_service().create_workflow(base_create_cmd(description="My desc"))
        assert wf.description == "My desc"

    def test_multiple_steps_all_stored(self):
        cmd = base_create_cmd(steps=[EMAIL_STEP, HTTP_STEP])
        wf = make_service().create_workflow(cmd)
        assert len(wf.steps) == 2


#  WorkflowService.update_workflow 

class TestWorkflowServiceUpdate:
    def _create(self, **overrides) -> object:
        return make_service().create_workflow(base_create_cmd(**overrides))

    def test_update_name(self):
        wf = self._create()
        updated = make_service().update_workflow(wf, UpdateWorkflowCommand(name="New Name"))
        assert updated.name == "New Name"

    def test_update_description(self):
        wf = self._create(description="old")
        updated = make_service().update_workflow(wf, UpdateWorkflowCommand(description="new"))
        assert updated.description == "new"

    def test_update_enabled(self):
        wf = self._create()
        updated = make_service().update_workflow(wf, UpdateWorkflowCommand(enabled=True))
        assert updated.enabled is True

    def test_no_provided_fields_preserves_existing(self):
        wf = self._create(name="Keep Me")
        updated = make_service().update_workflow(wf, UpdateWorkflowCommand())
        assert updated.name == "Keep Me"
        assert updated.trigger.type == wf.trigger.type

    def test_update_trigger_changes_type(self):
        wf = self._create(trigger=TIME_SPEC)
        updated = make_service().update_workflow(wf, UpdateWorkflowCommand(trigger=WEBHOOK_SPEC))
        assert updated.trigger.type == TriggerType.WEBHOOK

    def test_update_steps_replaces_all(self):
        wf = self._create(steps=[EMAIL_STEP])
        new_steps = [HTTP_STEP]
        updated = make_service().update_workflow(wf, UpdateWorkflowCommand(steps=new_steps))
        assert len(updated.steps) == 1
        assert updated.steps[0].action_type == ActionType.HTTP_REQUEST

    def test_update_touches_updated_at(self):
        wf = self._create()
        original_ts = wf.updated_at
        updated = make_service().update_workflow(wf, UpdateWorkflowCommand(name="X"))
        assert updated.updated_at >= original_ts

    def test_update_preserves_workflow_id(self):
        wf = self._create()
        updated = make_service().update_workflow(wf, UpdateWorkflowCommand(name="X"))
        assert updated.workflow_id == wf.workflow_id


#  validate_workflow 

class TestValidateWorkflow:
    def _valid_wf(self):
        return make_service().create_workflow(base_create_cmd())

    def test_valid_workflow_has_no_errors(self):
        assert validate_workflow(self._valid_wf()) == []

    def test_workflow_without_steps_has_error(self):
        wf = self._valid_wf()
        wf = wf.model_copy(update={"steps": []})
        errors = validate_workflow(wf)
        assert any("action step" in e for e in errors)

    def test_duplicate_step_orders_reported(self):
        from app.action.action import SendEmailActionStep
        step_a = SendEmailActionStep(
            name="A", step_order=0, to_template="x@y.com", subject_template="s", body_template="b"
        )
        step_b = SendEmailActionStep(
            name="B", step_order=0, to_template="x@y.com", subject_template="s", body_template="b"
        )
        wf = self._valid_wf().model_copy(update={"steps": [step_a, step_b]})
        errors = validate_workflow(wf)
        assert any("Duplicate" in e for e in errors)

    def test_step_with_empty_required_field_reported(self):
        from app.action.action import SendEmailActionStep
        bad_step = SendEmailActionStep(
            name="Bad", step_order=0, to_template="", subject_template="s", body_template="b"
        )
        wf = self._valid_wf().model_copy(update={"steps": [bad_step]})
        errors = validate_workflow(wf)
        assert any("Bad" in e for e in errors)

    def test_trigger_with_naive_datetime_reported(self):
        from datetime import datetime
        from app.trigger.trigger import TimeTriggerConfig
        bad_trigger = TimeTriggerConfig(trigger_at=datetime(2026, 5, 1, 9, 0, 0))  # no tzinfo
        wf = self._valid_wf().model_copy(update={"trigger": bad_trigger})
        errors = validate_workflow(wf)
        assert any("Trigger" in e for e in errors)

    def test_valid_webhook_workflow_has_no_errors(self):
        cmd = base_create_cmd(trigger=WEBHOOK_SPEC)
        wf = make_service().create_workflow(cmd)
        assert validate_workflow(wf) == []
