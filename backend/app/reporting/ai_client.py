"""AI summary client abstraction.

Defines the `AISummaryClient` Protocol so the pipeline can depend on an
interface rather than a concrete provider. The MVP ships a deterministic
`FakeAISummaryClient` so the pipeline is runnable and testable without any
third-party API access. A real OpenAI-backed implementation is a follow-up.
"""

from __future__ import annotations

from typing import Protocol


class AISummaryClient(Protocol):
    """Anything that can turn a metrics dict into a natural-language summary."""

    def summarize(self, metrics: dict) -> str:
        ...


class FakeAISummaryClient:
    """Deterministic stub for tests and local dev.

    Produces a compact, predictable one-liner derived from the metrics dict
    so tests can assert exact strings without depending on a real model.
    """

    def summarize(self, metrics: dict) -> str:
        total = metrics.get("total_runs", 0)
        success_rate = metrics.get("success_rate", 0.0)
        pct = round(success_rate * 100)
        return f"Monthly report: {total} runs, {pct}% success."
