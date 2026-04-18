"""Shared types for the suggestion module — UserInput, AnalysisResult, SuggestionResult."""

from typing import Literal

from pydantic import BaseModel, Field


class UserInput(BaseModel):
    raw_text: str
    user_name: str | None = None


class AnalysisResult(BaseModel):
    complexity_level: Literal["simple", "medium", "complex"]
    input_type: str
    confidence: float = Field(ge=0.0, le=1.0)


class SuggestionResult(BaseModel):
    content: str
    workflow_draft: dict | None = None
    strategy_used: str
