"""AI summary client abstraction.

Defines the `AISummaryClient` Protocol so the pipeline can depend on an
interface rather than a concrete provider. Two concrete implementations:
    FakeAISummaryClient — deterministic stub for tests/local dev.
    OpenAIAISummaryClient — real client hitting the OpenAI Chat Completions
        API (gpt-4o-mini by default). Errors propagate to AISummaryFilter,
        which owns the fallback text.
"""

from __future__ import annotations

import json
from typing import Protocol

from app.core.config import settings as _settings

_OPENAI_CHAT_URL = _settings.openai_base_url + "/chat/completions" if _settings.openai_base_url else "https://api.openai.com/v1/chat/completions"
_DEFAULT_MODEL = _settings.openai_model or "gpt-4o-mini"
_DEFAULT_TIMEOUT_S = 15.0
_SYSTEM_PROMPT = (
    "You are a concise reporting assistant. Given a JSON blob of monthly "
    "workflow automation metrics, return a 1-3 sentence natural-language "
    "summary a product owner would find useful. Do not invent numbers."
)


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


class OpenAIAISummaryClient:
    """AISummaryClient backed by the OpenAI Chat Completions REST API.

    Uses a sync httpx.Client because the reporting pipeline itself is sync.
    Any network/HTTP/parse error propagates — AISummaryFilter catches it
    and writes a fallback string, so the client stays dumb.
    """

    def __init__(
        self,
        api_key: str,
        model: str = _DEFAULT_MODEL,
        base_url: str = _OPENAI_CHAT_URL,
        timeout_seconds: float = _DEFAULT_TIMEOUT_S,
    ) -> None:
        if not api_key:
            raise ValueError("OpenAIAISummaryClient requires a non-empty api_key")
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._timeout = timeout_seconds

    def summarize(self, metrics: dict) -> str:
        import httpx  # deferred: httpx is installed at runtime, not baked into the image

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(metrics, default=str)},
            ],
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(self._base_url, json=payload, headers=headers)
            response.raise_for_status()
            body = response.json()
        return body["choices"][0]["message"]["content"].strip()
