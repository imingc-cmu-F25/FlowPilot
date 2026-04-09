# workflow/models.py

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class StepType(StrEnum):
    TRIGGER = "trigger"
    ACTION = "action"
    CONDITION = "condition"

class WorkflowStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"

class Position(BaseModel):
    """Canvas coordinates for the frontend node."""
    x: float
    y: float

class StepConfig(BaseModel):
    """Dynamic config payload — shape depends on the step's connector/action type."""
    connector_id: str | None = None
    action_id: str | None = None
    parameters: dict = Field(default_factory=dict)

class Edge(BaseModel):
    """A directed connection between two steps."""
    id: UUID = Field(default_factory=uuid4)
    source_step_id: UUID
    target_step_id: UUID
    condition: str | None = None  # optional branch label

class Step(BaseModel):
    """A single node on the workflow canvas."""
    id: UUID = Field(default_factory=uuid4)
    name: str
    step_type: StepType
    config: StepConfig = Field(default_factory=StepConfig)
    position: Position
    timeout_seconds: int = 300

class Workflow(BaseModel):
    """Top-level workflow definition stored in Postgres."""
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str = ""
    status: WorkflowStatus = WorkflowStatus.DRAFT
    steps: list[Step] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)