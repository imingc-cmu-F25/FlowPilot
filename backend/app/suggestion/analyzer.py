"""AIAnalyzer — classifies user intent using OpenAI, with heuristic fallback."""

from __future__ import annotations

import json

from app.suggestion.base import AnalysisResult, UserInput
from app.suggestion.openai_client import OPENAI_MODEL, get_openai_client

KNOWN_INPUT_TYPES = {
    "automation_request",
    "task_plan",
    "optimization",
    "question",
    "other",
}


class AIAnalyzer:
    SYSTEM_PROMPT = (
        "You classify FlowPilot workflow-related user requests. "
        "Return a JSON object with three keys: "
        "complexity_level (simple|medium|complex), "
        "input_type (one of: automation_request, task_plan, optimization, question, other), "
        "confidence (0.0 to 1.0). "
        "Respond ONLY with valid JSON, no explanation."
    )

    async def analyze(self, user_input: UserInput) -> AnalysisResult:
        client = get_openai_client()
        if client is None:
            return self._heuristic(user_input)

        try:
            response = await client.chat.completions.create(
                model=OPENAI_MODEL,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_input.raw_text},
                ],
                temperature=0.0,
            )
            raw = response.choices[0].message.content or "{}"
            data = json.loads(raw)
            return AnalysisResult(
                complexity_level=data.get("complexity_level", "medium"),
                input_type=self._normalize_input_type(data.get("input_type", "other")),
                confidence=float(data.get("confidence", 0.5)),
            )
        except Exception:
            return self._heuristic(user_input)

    @staticmethod
    def _normalize_input_type(value: str) -> str:
        value = (value or "").strip().lower()
        return value if value in KNOWN_INPUT_TYPES else "other"

    @staticmethod
    def _heuristic(user_input: UserInput) -> AnalysisResult:
        text = user_input.raw_text.strip()
        word_count = len(text.split())
        lower = text.lower()
        if any(k in lower for k in ("every day", "daily", "every week", "weekly", "webhook")):
            complexity = "simple"
            confidence = 0.85
            input_type = "automation_request"
        elif word_count < 15:
            complexity = "medium"
            confidence = 0.6
            input_type = "automation_request"
        else:
            complexity = "complex"
            confidence = 0.5
            input_type = "other"
        return AnalysisResult(
            complexity_level=complexity,
            input_type=input_type,
            confidence=confidence,
        )
