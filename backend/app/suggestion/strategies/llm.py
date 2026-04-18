"""LLMStrategy — uses OpenAI function calling to generate arbitrary workflow drafts."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from app.suggestion.base import SuggestionResult, UserInput
from app.suggestion.openai_client import OPENAI_MODEL, get_openai_client
from app.suggestion.strategies.base import SuggestionStrategy

_WORKFLOW_SCHEMA = {
    "type": "function",
    "function": {
        "name": "build_workflow",
        "description": "Build a FlowPilot workflow definition matching the user's request.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "trigger": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["time", "webhook"]},
                        "trigger_at": {
                            "type": "string",
                            "description": "ISO-8601 datetime, required for type=time",
                        },
                        "timezone": {"type": "string"},
                        "recurrence": {
                            "type": "object",
                            "properties": {
                                "frequency": {
                                    "type": "string",
                                    "enum": [
                                        "minutely",
                                        "hourly",
                                        "daily",
                                        "weekly",
                                        "custom",
                                    ],
                                },
                                "interval": {"type": "integer"},
                                "days_of_week": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                },
                                "cron_expression": {"type": "string"},
                            },
                        },
                        "path": {
                            "type": "string",
                            "description": "required for type=webhook",
                        },
                        "method": {"type": "string"},
                        "secret_ref": {"type": "string"},
                        "event_filter": {"type": "string"},
                    },
                    "required": ["type"],
                },
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action_type": {
                                "type": "string",
                                "enum": ["send_email", "http_request"],
                            },
                            "name": {"type": "string"},
                            "step_order": {"type": "integer"},
                            "to_template": {"type": "string"},
                            "subject_template": {"type": "string"},
                            "body_template": {"type": "string"},
                            "url_template": {"type": "string"},
                            "headers": {"type": "object"},
                        },
                        "required": ["action_type", "name", "step_order"],
                    },
                },
            },
            "required": ["name", "trigger", "steps"],
        },
    },
}


class LLMStrategy(SuggestionStrategy):
    """Calls OpenAI function calling to generate a structured workflow draft."""

    SYSTEM_PROMPT = (
        "You are a FlowPilot workflow assistant. "
        "Given a user's natural-language request, generate a workflow definition "
        "by calling the build_workflow function. "
        "Use 'time' triggers for scheduled work, 'webhook' for event-driven. "
        "Use 'send_email' or 'http_request' actions only. "
        "Keep step names short and descriptive."
    )

    async def generate_suggestion(self, user_input: UserInput) -> SuggestionResult:
        client = get_openai_client()
        if client is None:
            return SuggestionResult(
                content=(
                    "LLM suggestions are unavailable — OPENAI_API_KEY is not set. "
                    "Please configure it to enable this strategy."
                ),
                workflow_draft=None,
                strategy_used="llm",
            )

        try:
            response = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_input.raw_text},
                ],
                tools=[_WORKFLOW_SCHEMA],
                tool_choice={
                    "type": "function",
                    "function": {"name": "build_workflow"},
                },
                temperature=0.3,
            )
            message = response.choices[0].message
            if not message.tool_calls:
                return SuggestionResult(
                    content=(message.content or "Could not generate a structured workflow."),
                    workflow_draft=None,
                    strategy_used="llm",
                )
            raw_args = message.tool_calls[0].function.arguments
            draft = json.loads(raw_args)
            draft = _validate_and_fix(draft)
            return SuggestionResult(
                content="Generated a custom workflow based on your request.",
                workflow_draft=draft,
                strategy_used="llm",
            )
        except Exception as exc:
            return SuggestionResult(
                content=f"LLM call failed: {exc!s}",
                workflow_draft=None,
                strategy_used="llm",
            )


def _validate_and_fix(draft: dict) -> dict:
    """Ensure required fields exist and have sensible defaults."""
    draft.setdefault("name", "AI-Generated Workflow")
    draft.setdefault("description", "Generated by LLMStrategy")

    trigger = draft.get("trigger") or {}
    t_type = trigger.get("type", "time")
    if t_type == "time":
        trigger.setdefault("trigger_at", _default_future_iso())
        trigger.setdefault("timezone", "UTC")
        trigger.setdefault("recurrence", None)
    elif t_type == "webhook":
        trigger.setdefault("path", "/trigger")
        trigger.setdefault("method", "POST")
        trigger.setdefault("secret_ref", "")
        trigger.setdefault("event_filter", "")
    trigger["type"] = t_type
    draft["trigger"] = trigger

    steps = draft.get("steps") or []
    fixed_steps = []
    for i, step in enumerate(steps):
        step.setdefault("name", f"Step {i + 1}")
        step.setdefault("step_order", i)
        action_type = step.get("action_type", "send_email")
        step["action_type"] = action_type
        if action_type == "send_email":
            step.setdefault("to_template", "recipient@example.com")
            step.setdefault("subject_template", "Notification")
            step.setdefault("body_template", "Message body.")
        elif action_type == "http_request":
            step.setdefault("method", "GET")
            step.setdefault("url_template", "https://example.com")
            step.setdefault("headers", {})
        fixed_steps.append(step)
    draft["steps"] = fixed_steps
    return draft


def _default_future_iso() -> str:
    return (datetime.now(UTC) + timedelta(hours=1)).isoformat()
