from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.action.action import ActionStep, ActionStepFactory, StepSpec
from app.trigger.trigger import TriggerSpec
from app.trigger.triggerConfig import TriggerConfig
from app.trigger.triggerFactories import build_trigger_config


class WorkflowStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class WorkflowDefinition(BaseModel):
    """
    The final workflow object produced by the builder.

    Contains exactly one trigger config and an ordered list of action steps.
    Stored in WorkflowORM.payload as JSON.
    """
    workflow_id: UUID = Field(default_factory=uuid4)
    owner_name: str
    name: str
    description: str = ""
    enabled: bool = False
    status: WorkflowStatus = WorkflowStatus.DRAFT
    trigger: TriggerConfig
    steps: list[ActionStep] = []
    # Per-workflow retry budget. Every run emitted by any trigger (time,
    # webhook, calendar_event, custom) inherits this as its starting
    # `max_retries` unless the caller explicitly overrides it. Capped at 10
    # both here and at the API layer so a bad policy can't produce a retry
    # storm. 0 keeps the existing "fail on first error" behaviour.
    max_retries: int = Field(default=0, ge=0, le=10)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# Builder interface
class IWorkflowBuilder(ABC):
    @abstractmethod
    def reset(self, owner_name: str) -> None: ...

    @abstractmethod
    def set_metadata(self, name: str, description: str) -> None: ...

    @abstractmethod
    def set_trigger(self, spec: TriggerSpec) -> None: ...

    @abstractmethod
    def add_step(self, spec: StepSpec) -> None: ...

    @abstractmethod
    def reorder_steps(self, step_ids: list[UUID]) -> None: ...

    @abstractmethod
    def set_enabled(self, enabled: bool) -> None: ...

    @abstractmethod
    def set_max_retries(self, max_retries: int) -> None: ...

    @abstractmethod
    def build(self) -> WorkflowDefinition: ...


class WorkflowDefinitionBuilder(IWorkflowBuilder):
    """
    Assembles a WorkflowDefinition incrementally.

    Sequence: reset() → set_metadata() → set_trigger() → add_step()* → build()
    
    build() validates completeness then returns the immutable product and clears
    internal state so the builder instance can be reused.
    """

    def __init__(self) -> None:
        self._draft: dict = {}

    def reset(self, owner_name: str) -> None:
        self._draft = {
            "workflow_id": uuid4(),
            "owner_name": owner_name,
            "steps": [],
            "enabled": False,
            "status": WorkflowStatus.DRAFT,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

    def set_metadata(self, name: str, description: str = "") -> None:
        self._require_reset()
        self._draft["name"] = name
        self._draft["description"] = description

    def set_trigger(self, spec: TriggerSpec) -> None:
        self._require_reset()
        self._draft["trigger"] = build_trigger_config(spec)

    def add_step(self, spec: StepSpec) -> None:
        self._require_reset()
        step = ActionStepFactory.create(spec)
        self._draft["steps"].append(step)
        self._draft["steps"].sort(key=lambda s: s.step_order)

    def reorder_steps(self, step_ids: list[UUID]) -> None:
        self._require_reset()
        index = {sid: i for i, sid in enumerate(step_ids)}
        for step in self._draft["steps"]:
            if step.step_id in index:
                step.step_order = index[step.step_id]
        self._draft["steps"].sort(key=lambda s: s.step_order)

    def set_enabled(self, enabled: bool) -> None:
        self._require_reset()
        self._draft["enabled"] = enabled

    def set_max_retries(self, max_retries: int) -> None:
        self._require_reset()
        if max_retries < 0 or max_retries > 10:
            raise ValueError("max_retries must be between 0 and 10")
        self._draft["max_retries"] = max_retries

    def build(self) -> WorkflowDefinition:
        self._require_reset()
        self._validate_before_build()
        result = WorkflowDefinition(**self._draft)
        self._draft = {}
        return result

    # private methods
    def _require_reset(self) -> None:
        if not self._draft:
            raise RuntimeError("Call reset() before using the builder")

    def _validate_before_build(self) -> None:
        errors: list[str] = []
        if not self._draft.get("name"):
            errors.append("name is required")
        if "trigger" not in self._draft:
            errors.append("trigger is required")
        if not self._draft["steps"]:
            errors.append("at least one action step is required")
        if errors:
            raise ValueError(f"Incomplete workflow: {errors}")
