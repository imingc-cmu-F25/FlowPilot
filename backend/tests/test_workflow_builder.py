"""Tests for WorkflowDefinitionBuilder (Concrete Builder) and WorkflowDefinition (Product)."""

import pytest
from uuid import uuid4

from app.action.action import ActionType, StepSpec
from app.trigger.trigger import TriggerSpec, TriggerType
from app.workflow.workflow import WorkflowDefinition, WorkflowDefinitionBuilder, WorkflowStatus


#  Shared fixtures 

TIME_SPEC = TriggerSpec(
    type=TriggerType.TIME,
    parameters={"trigger_at": "2026-05-01T09:00:00+00:00"},
)

EMAIL_STEP = StepSpec(
    action_type=ActionType.SEND_EMAIL,
    name="Send report",
    step_order=0,
    parameters={
        "to_template": "team@example.com",
        "subject_template": "Report",
        "body_template": "Here it is.",
    },
)


def make_builder() -> WorkflowDefinitionBuilder:
    return WorkflowDefinitionBuilder()


#  Builder guard: reset() must be called first 

class TestBuilderRequiresReset:
    def test_set_metadata_without_reset_raises(self):
        b = make_builder()
        with pytest.raises(RuntimeError, match="reset()"):
            b.set_metadata("name")

    def test_set_trigger_without_reset_raises(self):
        b = make_builder()
        with pytest.raises(RuntimeError, match="reset()"):
            b.set_trigger(TIME_SPEC)

    def test_add_step_without_reset_raises(self):
        b = make_builder()
        with pytest.raises(RuntimeError, match="reset()"):
            b.add_step(EMAIL_STEP)

    def test_build_without_reset_raises(self):
        b = make_builder()
        with pytest.raises(RuntimeError, match="reset()"):
            b.build()


#  Builder validation before build() 

class TestBuilderValidation:
    def test_build_without_name_raises(self):
        b = make_builder()
        b.reset(uuid4())
        b.set_trigger(TIME_SPEC)
        b.add_step(EMAIL_STEP)
        with pytest.raises(ValueError, match="name is required"):
            b.build()

    def test_build_without_trigger_raises(self):
        b = make_builder()
        b.reset(uuid4())
        b.set_metadata("My Workflow")
        b.add_step(EMAIL_STEP)
        with pytest.raises(ValueError, match="trigger is required"):
            b.build()

    def test_build_without_steps_raises(self):
        b = make_builder()
        b.reset(uuid4())
        b.set_metadata("My Workflow")
        b.set_trigger(TIME_SPEC)
        with pytest.raises(ValueError, match="at least one action step is required"):
            b.build()


#  Happy-path build 

class TestBuilderHappyPath:
    def test_build_returns_workflow_definition(self):
        b = make_builder()
        owner = uuid4()
        b.reset(owner)
        b.set_metadata("Daily Report", "Sends every morning")
        b.set_trigger(TIME_SPEC)
        b.add_step(EMAIL_STEP)
        wf = b.build()

        assert isinstance(wf, WorkflowDefinition)
        assert wf.name == "Daily Report"
        assert wf.description == "Sends every morning"
        assert wf.owner_id == owner
        assert wf.trigger.type == TriggerType.TIME
        assert len(wf.steps) == 1
        assert wf.steps[0].action_type == ActionType.SEND_EMAIL

    def test_build_with_enabled_true(self):
        b = make_builder()
        b.reset(uuid4())
        b.set_metadata("W")
        b.set_trigger(TIME_SPEC)
        b.add_step(EMAIL_STEP)
        b.set_enabled(True)
        wf = b.build()
        assert wf.enabled is True

    def test_default_status_is_draft(self):
        b = make_builder()
        b.reset(uuid4())
        b.set_metadata("W")
        b.set_trigger(TIME_SPEC)
        b.add_step(EMAIL_STEP)
        wf = b.build()
        assert wf.status == WorkflowStatus.DRAFT

    def test_build_assigns_unique_workflow_ids(self):
        def build_one():
            b = make_builder()
            b.reset(uuid4())
            b.set_metadata("W")
            b.set_trigger(TIME_SPEC)
            b.add_step(EMAIL_STEP)
            return b.build()

        wf1 = build_one()
        wf2 = build_one()
        assert wf1.workflow_id != wf2.workflow_id

    def test_builder_resets_after_build(self):
        b = make_builder()
        b.reset(uuid4())
        b.set_metadata("W")
        b.set_trigger(TIME_SPEC)
        b.add_step(EMAIL_STEP)
        b.build()

        # After build, internal state is cleared
        with pytest.raises(RuntimeError, match="reset()"):
            b.build()

    def test_builder_can_be_reused_after_build(self):
        b = make_builder()
        for _ in range(2):
            b.reset(uuid4())
            b.set_metadata("W")
            b.set_trigger(TIME_SPEC)
            b.add_step(EMAIL_STEP)
            wf = b.build()
            assert isinstance(wf, WorkflowDefinition)


#  Step ordering 

class TestBuilderStepOrdering:
    def test_steps_sorted_by_step_order_on_add(self):
        b = make_builder()
        b.reset(uuid4())
        b.set_metadata("W")
        b.set_trigger(TIME_SPEC)

        http_step = StepSpec(
            action_type=ActionType.HTTP_REQUEST,
            name="Fetch data",
            step_order=1,
            parameters={"url_template": "https://api.example.com"},
        )
        b.add_step(http_step)   # order 1 added first
        b.add_step(EMAIL_STEP)  # order 0 added second

        wf = b.build()
        assert wf.steps[0].step_order == 0
        assert wf.steps[1].step_order == 1

    def test_reorder_steps_updates_order(self):
        b = make_builder()
        b.reset(uuid4())
        b.set_metadata("W")
        b.set_trigger(TIME_SPEC)

        step_a = StepSpec(
            action_type=ActionType.HTTP_REQUEST,
            name="A",
            step_order=0,
            parameters={"url_template": "https://a.com"},
        )
        step_b = StepSpec(
            action_type=ActionType.SEND_EMAIL,
            name="B",
            step_order=1,
            parameters={"to_template": "x@y.com", "subject_template": "S", "body_template": "B"},
        )
        b.add_step(step_a)
        b.add_step(step_b)
        wf_before = b.build()

        # Rebuild and reorder: put B (index 1) before A (index 0)
        b.reset(uuid4())
        b.set_metadata("W")
        b.set_trigger(TIME_SPEC)
        b.add_step(step_a)
        b.add_step(step_b)
        id_a = b._draft["steps"][0].step_id
        id_b = b._draft["steps"][1].step_id
        b.reorder_steps([id_b, id_a])  # B first, A second
        wf_after = b.build()

        assert wf_after.steps[0].name == "B"
        assert wf_after.steps[1].name == "A"


#  Multiple step types 

class TestBuilderMultipleStepTypes:
    def test_builds_workflow_with_multiple_different_step_types(self):
        b = make_builder()
        b.reset(uuid4())
        b.set_metadata("Multi-step")
        b.set_trigger(TIME_SPEC)
        b.add_step(StepSpec(
            action_type=ActionType.HTTP_REQUEST,
            name="Fetch",
            step_order=0,
            parameters={"url_template": "https://api.example.com/data"},
        ))
        b.add_step(EMAIL_STEP)
        wf = b.build()

        assert len(wf.steps) == 2
        assert wf.steps[0].action_type == ActionType.HTTP_REQUEST
        assert wf.steps[1].action_type == ActionType.SEND_EMAIL


#  Webhook trigger variant 

class TestBuilderWebhookTrigger:
    def test_builds_workflow_with_webhook_trigger(self):
        b = make_builder()
        b.reset(uuid4())
        b.set_metadata("Webhook Flow")
        b.set_trigger(TriggerSpec(
            type=TriggerType.WEBHOOK,
            parameters={"path": "/hooks/my-workflow"},
        ))
        b.add_step(EMAIL_STEP)
        wf = b.build()

        assert wf.trigger.type == TriggerType.WEBHOOK

    def test_unknown_trigger_type_raises(self):
        from pydantic import ValidationError as PydanticValidationError
        b = make_builder()
        b.reset(uuid4())
        b.set_metadata("W")
        with pytest.raises((ValueError, KeyError, PydanticValidationError)):
            spec = TriggerSpec(type="nonexistent", parameters={})  # type: ignore[arg-type]
            b.set_trigger(spec)


#  WorkflowDefinition JSON round-trip 

class TestWorkflowDefinitionRoundTrip:
    def _build_wf(self) -> WorkflowDefinition:
        b = make_builder()
        b.reset(uuid4())
        b.set_metadata("Round-trip test", "desc")
        b.set_trigger(TIME_SPEC)
        b.add_step(EMAIL_STEP)
        return b.build()

    def test_model_dump_and_validate_restores_full_object(self):
        wf = self._build_wf()
        payload = wf.model_dump(mode="json")
        restored = WorkflowDefinition.model_validate(payload)

        assert restored.workflow_id == wf.workflow_id
        assert restored.name == wf.name
        assert restored.trigger.type == wf.trigger.type
        assert len(restored.steps) == len(wf.steps)
        assert restored.steps[0].action_type == wf.steps[0].action_type

    def test_restored_trigger_is_correct_concrete_type(self):
        from app.trigger.trigger import TimeTriggerConfig
        wf = self._build_wf()
        restored = WorkflowDefinition.model_validate(wf.model_dump(mode="json"))
        assert isinstance(restored.trigger, TimeTriggerConfig)
