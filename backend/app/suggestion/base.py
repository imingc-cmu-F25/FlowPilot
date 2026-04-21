"""Shared types for the suggestion module — UserInput, AnalysisResult, SuggestionResult."""

from typing import Literal

from pydantic import BaseModel, Field

InputType = Literal[
    "automation_request",
    "task_plan",
    "optimization",
    "question",
    "other",
    "too_short",  # set by SuggestionService when the guard fires
]

StrategyUsed = Literal[
    "rule_based",
    "template",
    "llm",
    "guard",  # short-circuited by SuggestionService (too_short / off_topic)
]


class UserInput(BaseModel):
    raw_text: str
    user_name: str | None = None
    # IANA timezone the user is typing from (e.g. "America/Los_Angeles").
    # Strategies use it to interpret bare wall-clock times like "9 AM" as
    # the user's local 9 AM rather than 9 AM UTC. Defaults to UTC when the
    # frontend doesn't send one (preserves pre-existing behaviour for
    # API tests).
    timezone: str | None = None


class AnalysisResult(BaseModel):
    complexity_level: Literal["simple", "medium", "complex"]
    input_type: InputType
    confidence: float = Field(ge=0.0, le=1.0)


class PendingQuestion(BaseModel):
    """A clarifying question the agent needs the user to answer before
    the draft can be POSTed to /api/workflows.

    `field` is a dotted path into the draft (e.g. "trigger.path",
    "steps.0.parameters.to_template"). The answer endpoint applies
    `draft[field] = value` then re-detects whether more questions remain.
    """
    field: str
    question: str
    example: str = ""
    suggested_value: str = ""


class SuggestionResult(BaseModel):
    content: str
    workflow_draft: dict | None = None
    strategy_used: StrategyUsed
    pending_questions: list[PendingQuestion] = []
