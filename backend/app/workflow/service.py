from datetime import UTC, datetime

from pydantic import BaseModel

from app.action.action import ActionStepFactory, StepSpec
from app.trigger.service import TriggerService
from app.trigger.trigger import TriggerSpec
from app.workflow.workflow import IWorkflowBuilder, WorkflowDefinition, WorkflowDefinitionBuilder


class CreateWorkflowCommand(BaseModel):
    owner_name: str
    name: str
    description: str = ""
    trigger: TriggerSpec
    steps: list[StepSpec]
    enabled: bool = False


class UpdateWorkflowCommand(BaseModel):
    """All fields are optional — only provided fields are updated."""
    name: str | None = None
    description: str | None = None
    trigger: TriggerSpec | None = None
    steps: list[StepSpec] | None = None
    enabled: bool | None = None


class WorkflowService:
    """Director — controls the workflow construction sequence.

    Uses the Builder for creation (enforces completeness before persistence).
    Uses model_copy for partial updates (preserves existing fields).
    """

    def __init__(self, builder: IWorkflowBuilder, trigger_service: TriggerService) -> None:
        self._builder = builder
        self._trigger_service = trigger_service

    def create_workflow(self, cmd: CreateWorkflowCommand) -> WorkflowDefinition:
        b = self._builder
        b.reset(cmd.owner_name)
        b.set_metadata(cmd.name, cmd.description)
        b.set_trigger(cmd.trigger)
        for step_spec in cmd.steps:
            b.add_step(step_spec)
        b.set_enabled(cmd.enabled)
        return b.build()

    def update_workflow(
        self, existing: WorkflowDefinition, cmd: UpdateWorkflowCommand
    ) -> WorkflowDefinition:
        """Apply partial updates on top of the existing definition."""
        updates: dict = {"updated_at": datetime.now(UTC)}

        if cmd.name is not None:
            updates["name"] = cmd.name
        if cmd.description is not None:
            updates["description"] = cmd.description
        if cmd.enabled is not None:
            updates["enabled"] = cmd.enabled

        if cmd.trigger is not None:
            updates["trigger"] = self._trigger_service.build_config(cmd.trigger)

        if cmd.steps is not None:
            new_steps = [ActionStepFactory.create(s) for s in cmd.steps]
            updates["steps"] = sorted(new_steps, key=lambda s: s.step_order)

        return existing.model_copy(update=updates)


def make_workflow_service() -> WorkflowService:
    """FastAPI dependency factory — returns a fresh service per request."""
    return WorkflowService(WorkflowDefinitionBuilder(), TriggerService())
