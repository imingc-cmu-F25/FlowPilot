"""Pipes and Filters core — PipeData contract, Filter ABC, Pipeline executor.

Each filter implements `process(data: PipeData) -> PipeData`. The Pipeline
runs filters in order, passing each filter's output as the next filter's
input. No filter is allowed to share mutable state with another — each reads
the fields it needs and writes its own output.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.reporting.report import AggregatedMetrics, MonthlyReport


class PipeData(BaseModel):
    """Standardized data contract shared between filters.

    Filters progressively populate the output fields. Early-stage fields
    (owner_name, period_*) are required inputs; later fields are filled as
    the pipeline runs.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # required inputs
    owner_name: str
    period_start: datetime
    period_end: datetime

    # populated by DataCollectionFilter
    raw_execution_records: list[dict[str, Any]] = Field(default_factory=list)
    external_logs: list[dict[str, Any]] = Field(default_factory=list)

    # populated by AggregationFilter
    aggregated_metrics: AggregatedMetrics | None = None

    # populated by AISummaryFilter
    ai_summary: str = ""

    # populated by FormattingFilter
    formatted_report: MonthlyReport | None = None

    # free-form scratch space for extensions
    metadata: dict[str, Any] = Field(default_factory=dict)


class Filter(ABC):
    """Uniform filter interface. Concrete filters must be stateless across
    pipeline runs — hold only dependencies (repos, clients) in __init__."""

    @abstractmethod
    def process(self, data: PipeData) -> PipeData:
        ...


class PipelineError(RuntimeError):
    """Raised when a filter fails during Pipeline.execute.

    Wraps the underlying exception and includes the failing filter's class
    name so callers (e.g. ReportingService.mark_failed) can record where
    the pipeline broke.
    """

    def __init__(self, filter_name: str, original: Exception) -> None:
        super().__init__(f"{filter_name} failed: {original}")
        self.filter_name = filter_name
        self.original = original


class Pipeline:
    def __init__(self, filters: list[Filter] | None = None) -> None:
        self._filters: list[Filter] = list(filters) if filters else []

    def add_filter(self, f: Filter) -> Pipeline:
        self._filters.append(f)
        return self

    def execute(self, data: PipeData) -> PipeData:
        current = data
        for f in self._filters:
            try:
                current = f.process(current)
            except Exception as exc:
                raise PipelineError(type(f).__name__, exc) from exc
        return current
