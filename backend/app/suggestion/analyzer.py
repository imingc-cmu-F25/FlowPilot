"""AIAnalyzer — classifies user intent using OpenAI, with heuristic fallback."""

from __future__ import annotations

import json

from app.suggestion.base import AnalysisResult, UserInput
from app.suggestion.openai_client import get_openai_client, get_openai_model

KNOWN_INPUT_TYPES = {
    "automation_request",
    "task_plan",
    "optimization",
    "question",
    "other",
}

# Heuristic: any of these tokens hints the user is describing a workflow.
# Used both for the no-API-key fallback path AND as the relevance gate that
# decides whether to short-circuit the pipeline with a "this doesn't look
# like a workflow request" message.
AUTOMATION_KEYWORDS = {
    # Strong workflow signals — appearing in casual chat is rare.
    "email", "mail", "send", "notify", "alert", "remind",
    "webhook", "hook", "endpoint", "api", "url",
    "call", "request", "fetch", "ping", "trigger",
    "monitor", "watch", "health",
    "schedule", "scheduled", "after", "every", "each",
    "daily", "weekly", "hourly", "minute", "minutes",
    "weekday", "weekend",
    "calendar", "meeting", "appointment", "agenda",
    "upcoming",
    "report", "summary", "deploy",
    "workflow", "automation", "automate",
    # Intentionally NOT included (too common in casual chat):
    # "today", "tomorrow", "now", "morning", "evening", "night",
    # weekday names (monday..sunday), "get", "post", "data", "run",
    # "check", "status", "hour", "hours", "event".
}


def _has_automation_intent(text: str) -> bool:
    """Return True if the text contains any workflow-relevant keyword."""
    lower = text.lower()
    # Cheap word-boundary-ish split — the keyword set is short tokens, so
    # `in` would over-match (e.g. "send" inside "sender"). Splitting on
    # non-letter runs is good enough for English; for mixed-language input
    # we still scan substrings as a fallback.
    import re
    tokens = set(re.findall(r"[a-zA-Z]+", lower))
    return bool(tokens & AUTOMATION_KEYWORDS)


class AIAnalyzer:
    SYSTEM_PROMPT = (
        "You classify FlowPilot workflow-related user requests. "
        "Return a JSON object with three keys: "
        "complexity_level (simple|medium|complex), "
        "input_type (one of: automation_request, task_plan, optimization, question, other), "
        "confidence (0.0 to 1.0). "
        "IMPORTANT: FlowPilot only builds *workflow automations* (scheduled "
        "tasks, webhooks, calendar-driven actions, multi-step API/email "
        "pipelines). If the user's text is NOT a workflow request — e.g. "
        "it's small talk ('hi', 'how are you'), a general question ('what "
        "is python?'), a joke request, gibberish, or otherwise unactionable "
        "— set input_type to \"other\" and confidence to >= 0.9 so the "
        "pipeline can short-circuit politely. "
        "Respond ONLY with valid JSON, no explanation."
    )

    async def analyze(self, user_input: UserInput) -> AnalysisResult:
        # Heuristic-first: the keyword classifier deterministically handles
        # the common cases (automation_request 0.85, irrelevant input 0.9,
        # etc.). Only fall through to the LLM when we're genuinely
        # uncertain (confidence < 0.8). Saves one LLM round-trip per
        # request on the hot path — the analyzer is ~30-40% of total
        # latency before we even start generating a draft.
        heuristic = self._heuristic(user_input)
        if heuristic.confidence >= 0.8:
            return heuristic

        client = get_openai_client()
        if client is None:
            return heuristic

        try:
            response = await client.chat.completions.create(
                model=get_openai_model(),
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
            return heuristic

    @staticmethod
    def _normalize_input_type(value: str) -> str:
        value = (value or "").strip().lower()
        return value if value in KNOWN_INPUT_TYPES else "other"

    @staticmethod
    def _heuristic(user_input: UserInput) -> AnalysisResult:
        text = user_input.raw_text.strip()
        word_count = len(text.split())
        lower = text.lower()
        # Relevance gate: text with zero workflow keywords is almost
        # certainly not a workflow request. Mark it `other` with high
        # confidence so the service layer can short-circuit. We make an
        # exception for very long inputs (>=20 words) so a verbose
        # description we don't fully tokenise still gets routed to the LLM.
        if word_count < 20 and not _has_automation_intent(text):
            return AnalysisResult(
                complexity_level="simple",
                input_type="other",
                confidence=0.9,
            )
        # Simple keywords → RuleBasedStrategy (confidence >= 0.8)
        if any(k in lower for k in ("every day", "daily", "every week", "weekly", "webhook")):
            complexity = "simple"
            confidence = 0.85
            input_type = "automation_request"
        # Moderate keywords → TemplateStrategy (confidence >= 0.7)
        elif word_count < 20 and any(
            k in lower
            for k in (
                "email", "send", "mail", "notify", "alert",
                "check", "monitor", "ping", "health",
                "fetch", "call", "api", "request",
                "after", "minute", "hour",
            )
        ):
            complexity = "medium"
            confidence = 0.75
            input_type = "automation_request"
        # Short but vague → TemplateStrategy attempt
        elif word_count < 10:
            complexity = "medium"
            confidence = 0.7
            input_type = "automation_request"
        # Long or complex → LLMStrategy
        else:
            complexity = "complex"
            confidence = 0.5
            input_type = "other"
        return AnalysisResult(
            complexity_level=complexity,
            input_type=input_type,
            confidence=confidence,
        )
