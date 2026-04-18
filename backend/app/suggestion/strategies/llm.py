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
                "name": {"type": "string", "description": "Short descriptive workflow name"},
                "description": {
                    "type": "string",
                    "description": (
                        "One-sentence description of"
                        " what the workflow does"
                    ),
                },
                "trigger": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["time", "webhook", "custom"],
                            "description": (
                                "time=scheduled/delayed,"
                                " webhook=HTTP event-driven,"
                                " custom=condition-based"
                            ),
                        },
                        # time trigger fields
                        "trigger_at": {
                            "type": "string",
                            "description": (
                                "ISO-8601 UTC datetime when"
                                " workflow fires (required"
                                " for type=time). Example:"
                                " 2026-04-18T20:00:00+00:00"
                            ),
                        },
                        "timezone": {
                            "type": "string",
                            "description": "IANA timezone name, e.g. UTC, America/New_York",
                        },
                        "recurrence": {
                            "type": "object",
                            "description": (
                                "Optional recurring schedule."
                                " Omit or set null for"
                                " one-time triggers."
                            ),
                            "properties": {
                                "frequency": {
                                    "type": "string",
                                    "enum": ["minutely", "hourly", "daily", "weekly", "custom"],
                                },
                                "interval": {
                                    "type": "integer",
                                    "description": (
                                        "Repeat every N units"
                                        " (e.g. interval=2 with"
                                        " daily = every 2 days)"
                                    ),
                                },
                                "days_of_week": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": (
                                        "For weekly: 0=Mon,"
                                        " 1=Tue, ..., 6=Sun."
                                        " Example: [0,4] ="
                                        " Monday and Friday"
                                    ),
                                },
                                "cron_expression": {
                                    "type": "string",
                                    "description": (
                                "For frequency=custom: cron"
                                " expression, e.g."
                                " '0 9 * * 1-5' ="
                                " 9am weekdays"
                            ),
                                },
                            },
                        },
                        # webhook trigger fields
                        "path": {
                            "type": "string",
                            "description": (
                                "URL path for webhook"
                                " (required for"
                                " type=webhook),"
                                " must start with /"
                            ),
                        },
                        "method": {
                            "type": "string",
                            "description": "HTTP method for webhook: GET, POST, PUT, PATCH, DELETE",
                        },
                        "secret_ref": {
                            "type": "string",
                            "description": (
                                "Secret reference for"
                                " webhook HMAC verification"
                            ),
                        },
                        "event_filter": {
                            "type": "string",
                            "description": (
                                "Match against"
                                " X-Event-Type header"
                            ),
                        },
                        # custom trigger fields
                        "condition": {
                            "type": "string",
                            "description": (
                                "Condition expression for"
                                " custom trigger (required"
                                " for type=custom)"
                            ),
                        },
                        "source": {
                            "type": "string",
                            "description": "Context source for custom trigger evaluation",
                        },
                    },
                    "required": ["type"],
                },
                "steps": {
                    "type": "array",
                    "description": (
                        "Ordered list of action steps."
                        " Steps execute sequentially"
                        " and can reference prior step"
                        " outputs via"
                        " {{previous_output}}."
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "action_type": {
                                "type": "string",
                                "enum": ["send_email", "http_request", "calendar_create_event"],
                                "description": "Type of action to perform",
                            },
                            "name": {
                                "type": "string",
                                "description": (
                                    "Short descriptive"
                                    " step name"
                                ),
                            },
                            "step_order": {
                                "type": "integer",
                                "description": (
                                    "Execution order,"
                                    " 0-based"
                                ),
                            },
                            # send_email fields
                            "to_template": {
                                "type": "string",
                                "description": (
                                    "Email recipient address"
                                    " (for send_email)."
                                    " Supports {{variable}}"
                                    " placeholders."
                                ),
                            },
                            "subject_template": {
                                "type": "string",
                                "description": (
                                    "Email subject line"
                                    " (for send_email)."
                                    " Supports {{variable}}"
                                    " placeholders."
                                ),
                            },
                            "body_template": {
                                "type": "string",
                                "description": (
                                    "Email body content"
                                    " (for send_email). Use"
                                    " {{previous_output}} to"
                                    " include data from"
                                    " prior steps."
                                ),
                            },
                            # http_request fields
                            "method": {
                                "type": "string",
                                "description": (
                                    "HTTP method for"
                                    " http_request: GET,"
                                    " POST, PUT, PATCH,"
                                    " DELETE"
                                ),
                            },
                            "url_template": {
                                "type": "string",
                                "description": (
                                    "Target URL (for"
                                    " http_request). Supports"
                                    " {{variable}}"
                                    " placeholders."
                                ),
                            },
                            "headers": {
                                "type": "object",
                                "description": "HTTP headers as key-value pairs (for http_request)",
                            },
                            # calendar_create_event fields
                            "calendar_id": {
                                "type": "string",
                                "description": "Calendar identifier (for calendar_create_event)",
                            },
                            "title_template": {
                                "type": "string",
                                "description": (
                                    "Event title (for"
                                    " calendar_create_event)."
                                    " Supports {{variable}}"
                                    " placeholders."
                                ),
                            },
                            "start_mapping": {
                                "type": "string",
                                "description": (
                                    "JSONPath to start"
                                    " datetime from prior"
                                    " step output (for"
                                    " calendar_create_event)"
                                ),
                            },
                            "end_mapping": {
                                "type": "string",
                                "description": (
                                    "JSONPath to end"
                                    " datetime from prior"
                                    " step output (for"
                                    " calendar_create_event)"
                                ),
                            },
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
        "You are FlowPilot's intelligent workflow builder. "
        "The current UTC time is {current_utc}.\n\n"
        "Your job: convert the user's natural-language request into a COMPLETE, READY-TO-USE "
        "workflow definition by calling the build_workflow function.\n\n"
        "## Platform capabilities\n"
        "**Triggers** (how a workflow starts):\n"
        "- `time` — run at a specific datetime, optionally recurring "
        "(minutely, hourly, daily, weekly, or custom cron).\n"
        "- `webhook` — run when an HTTP request hits a specific path.\n"
        "- `custom` — run when a condition expression evaluates to true.\n\n"
        "**Actions** (what a workflow does, steps execute sequentially):\n"
        "- `send_email` — send an email with configurable recipient, subject, and body.\n"
        "- `http_request` — call any HTTP API/URL with configurable method, headers, and URL.\n"
        "- `calendar_create_event` — create a calendar event with title, start/end times.\n\n"
        "**Chaining**: steps run in order. Later steps can reference earlier step outputs "
        "using `{{{{previous_output}}}}` in any template field.\n\n"
        "## Rules\n"
        "1. ALWAYS fill in every field with concrete, meaningful "
        "values derived from the user's request. "
        "NEVER use generic placeholders like 'recipient@example.com', 'Message body.', or 'https://example.com'.\n"
        "2. Give the workflow a short, descriptive name summarizing what it does.\n"
        "3. Write a clear one-sentence description.\n"
        "4. For TIME triggers:\n"
        "   - Compute `trigger_at` as an exact ISO-8601 UTC datetime. "
        "Examples: 'after 5 minutes' → current time + 5 min; 'tomorrow 9am' → next 09:00 UTC; "
        "'every Monday' → next Monday 09:00 UTC.\n"
        "   - Set `recurrence` when the user wants it repeated. Pick the right frequency "
        "and interval. For 'every weekday' use custom cron '0 9 * * 1-5'.\n"
        "   - Omit `recurrence` (or set null) for one-time tasks.\n"
        "5. For WEBHOOK triggers:\n"
        "   - Set a meaningful `path` starting with / (e.g. /hooks/github-push).\n"
        "   - Set `method` (default POST). Use `event_filter` if the user specifies event types.\n"
        "6. For CUSTOM triggers:\n"
        "   - Set a `condition` expression and optional `source`.\n"
        "7. For SEND_EMAIL steps:\n"
        "   - Extract the recipient from the request. If unclear, use a descriptive placeholder "
        "the user can easily fill in (e.g. 'your-team@company.com').\n"
        "   - Write subject and body that match the user's purpose. Be specific and helpful.\n"
        "8. For HTTP_REQUEST steps:\n"
        "   - Use the URL from the request if provided. Set appropriate method and headers.\n"
        "   - For API calls that return data, chain with a "
        "subsequent step that uses {{{{previous_output}}}}.\n"
        "9. For CALENDAR_CREATE_EVENT steps:\n"
        "   - Set calendar_id, title_template, start_mapping, and end_mapping.\n"
        "10. Combine multiple steps for complex requests. Examples:\n"
        "    - 'Check API health and alert me' → http_request + send_email\n"
        "    - 'Fetch weather and email report' → "
        "http_request + send_email with {{{{previous_output}}}}\n"
        "    - 'When webhook fires, call API and create "
        "calendar event' → http_request + calendar_create_event\n"
        "11. Think about what the user actually wants to "
        "achieve and build the best workflow for it."
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
                    {"role": "system", "content": self.SYSTEM_PROMPT.format(
                        current_utc=datetime.now(UTC).isoformat(),
                    )},
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
        trigger.setdefault("path", "/hooks/incoming")
        trigger.setdefault("method", "POST")
        trigger.setdefault("secret_ref", "")
        trigger.setdefault("event_filter", "")
    elif t_type == "custom":
        trigger.setdefault("condition", "true")
        trigger.setdefault("source", "event_payload")
        trigger.setdefault("description", "")
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
            step.setdefault("to_template", "")
            step.setdefault("subject_template", "")
            step.setdefault("body_template", "")
        elif action_type == "http_request":
            step.setdefault("method", "GET")
            step.setdefault("url_template", "")
            step.setdefault("headers", {})
        elif action_type == "calendar_create_event":
            step.setdefault("calendar_id", "")
            step.setdefault("title_template", "")
            step.setdefault("start_mapping", "")
            step.setdefault("end_mapping", "")
        fixed_steps.append(step)
    draft["steps"] = fixed_steps
    return draft


def _default_future_iso() -> str:
    return (datetime.now(UTC) + timedelta(hours=1)).isoformat()
