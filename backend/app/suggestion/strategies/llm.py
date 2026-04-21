"""LLMStrategy — uses OpenAI function calling to generate arbitrary workflow drafts."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from app.suggestion.base import SuggestionResult, UserInput
from app.suggestion.openai_client import get_openai_client, get_openai_model
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
                            "enum": ["time", "webhook", "custom", "calendar_event"],
                            "description": (
                                "time=scheduled/delayed,"
                                " webhook=HTTP event-driven,"
                                " custom=condition-based,"
                                " calendar_event=fires when a new event"
                                " appears in the user's Google Calendar"
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
                            # Explicit nullable so strict validators
                            # (Groq) don't reject a one-time trigger.
                            # OpenAI tolerates null on `type:"object"`,
                            # Groq enforces JSON-schema-strict.
                            "type": ["object", "null"],
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
                        # calendar_event trigger fields
                        "calendar_id": {
                            "type": "string",
                            "description": (
                                "Google Calendar id to watch"
                                " (for type=calendar_event)."
                                " Use 'primary' for the user's"
                                " main calendar."
                            ),
                        },
                        "title_contains": {
                            "type": "string",
                            "description": (
                                "Optional substring filter on"
                                " event title (for"
                                " type=calendar_event). Empty"
                                " string means no filter."
                            ),
                        },
                        "dedup_seconds": {
                            "type": "integer",
                            "description": (
                                "Debounce window in seconds"
                                " (for type=calendar_event,"
                                " default 60). Ignore"
                                " first-seen events within"
                                " this window of the prior"
                                " dispatch."
                            ),
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
                                "enum": [
                                    "send_email",
                                    "http_request",
                                    "calendar_create_event",
                                    "calendar_list_upcoming",
                                ],
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
                            # calendar_list_upcoming fields
                            # (calendar_id is reused from above)
                            "max_results": {
                                "type": "integer",
                                "description": (
                                    "Max events to return"
                                    " (for calendar_list_upcoming,"
                                    " 1-100, default 10)."
                                ),
                            },
                            "title_contains": {
                                "type": "string",
                                "description": (
                                    "Optional substring filter"
                                    " on event title (for"
                                    " calendar_list_upcoming)."
                                ),
                            },
                            "window_hours": {
                                "type": "integer",
                                "description": (
                                    "Lookahead window in hours"
                                    " (for calendar_list_upcoming)."
                                    " 0 = no time bound, just"
                                    " rely on max_results."
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
        "The current UTC time is {current_utc}. "
        "The user's local timezone is {user_timezone}. "
        "When the user says a bare time like '9 AM' or '11 PM' WITHOUT "
        "mentioning UTC, interpret it as that wall-clock time IN THE USER'S "
        "TIMEZONE, then convert to the equivalent UTC instant for "
        "trigger_at. Example: user is in America/Los_Angeles and says "
        "'9 AM tomorrow' → trigger_at is tomorrow's 09:00 PT, which is "
        "16:00 UTC (PDT) or 17:00 UTC (PST). Set trigger.timezone to the "
        "user's IANA zone, not 'UTC'.\n\n"
        "Your job: convert the user's natural-language request into a COMPLETE, READY-TO-USE "
        "workflow definition by calling the build_workflow function.\n\n"
        "## Hard requirement\n"
        "You MUST call the `build_workflow` function. NEVER reply with plain "
        "text. If a field is genuinely uncertain, make the best reasonable "
        "guess and put a one-sentence note in the workflow `description` "
        "field explaining what you assumed. The user will see the draft in "
        "a builder UI and can correct anything before saving.\n\n"
        "## Platform capabilities\n"
        "**Triggers** (how a workflow starts):\n"
        "- `time` — run at a specific datetime, optionally recurring "
        "(minutely, hourly, daily, weekly, or custom cron).\n"
        "- `webhook` — run when an HTTP request hits a specific path.\n"
        "- `custom` — run when a condition expression evaluates to true.\n"
        "- `calendar_event` — run when a new event appears in the user's "
        "Google Calendar (optionally filtered by title substring).\n\n"
        "**Actions** (what a workflow does, steps execute sequentially):\n"
        "- `send_email` — send an email with configurable recipient, subject, and body.\n"
        "- `http_request` — call any HTTP API/URL with configurable method, headers, and URL.\n"
        "- `calendar_create_event` — create a calendar event with title, start/end times.\n"
        "- `calendar_list_upcoming` — fetch the next N upcoming events from a "
        "calendar; downstream steps can reference the result via "
        "`{{{{previous_output}}}}`.\n\n"
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
        "   - Set `recurrence` when the user EXPLICITLY uses a repetition word "
        "(every, each, daily, weekly, monthly, hourly, recurring). Pick the "
        "right frequency and interval. For 'every weekday' use custom cron "
        "'0 9 * * 1-5'.\n"
        "   - For one-time triggers set `recurrence: null`. `recurrence: "
        "null` is VALID — NEVER describe it as an error or 'missing field', "
        "and NEVER tell the user to 'provide a recurrence object'.\n"
        "   - Phrases that UNAMBIGUOUSLY mean one-time (set recurrence=null "
        "and call the function immediately, do NOT ask for clarification): "
        "'tomorrow', 'today', 'next Monday/Tuesday/...', any explicit date, "
        "'in N minutes/seconds/hours', 'after N minutes/seconds/hours'.\n"
        "   - The ONLY ambiguous case is a bare time-of-day with no date "
        "anchor and no repetition verb (e.g. 'at 9am' alone). Even then, "
        "DEFAULT to one-time tomorrow at that time and add a note in "
        "`description` like 'Assumed one-time tomorrow; change to recurring "
        "if you wanted that.' Do NOT refuse to call the function.\n"
        "5. For WEBHOOK triggers:\n"
        "   - Set a meaningful `path` starting with / (e.g. /hooks/github-push).\n"
        "   - Set `method` (default POST). Use `event_filter` if the user specifies event types.\n"
        "6. For CUSTOM triggers:\n"
        "   - Set a `condition` expression and optional `source`.\n"
        "6b. For CALENDAR_EVENT triggers:\n"
        "   - Set `calendar_id` (default 'primary'). Use `title_contains` "
        "to filter to events whose title contains a phrase (e.g. 'standup', "
        "'1:1'). Leave `dedup_seconds` unset unless the user wants a "
        "different debounce window from the 60s default.\n"
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
        "9b. For CALENDAR_LIST_UPCOMING steps:\n"
        "   - Set `calendar_id` (default 'primary') and `max_results` "
        "(1-100, default 10). Use `window_hours` to bound the lookahead "
        "(e.g. 24 = next day, 168 = next week, 0 = no time bound). Use "
        "`title_contains` if the user only cares about a subset of events. "
        "Pair this with a downstream send_email/http_request step that "
        "consumes `{{{{previous_output}}}}`.\n"
        "10. Combine multiple steps for complex requests. Examples:\n"
        "    - 'Check API health and alert me' → http_request + send_email\n"
        "    - 'Fetch weather and email report' → "
        "http_request + send_email with {{{{previous_output}}}}\n"
        "    - 'When webhook fires, call API and create "
        "calendar event' → http_request + calendar_create_event\n"
        "    - 'Every morning email me my schedule for today' → time trigger "
        "(daily 8am) + calendar_list_upcoming (window_hours=24) + send_email "
        "with {{{{previous_output}}}}\n"
        "    - 'When a meeting titled 1:1 is added to my calendar, post to "
        "this webhook' → calendar_event trigger (title_contains='1:1') + "
        "http_request\n"
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
                model=get_openai_model(),
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT.format(
                        current_utc=datetime.now(UTC).isoformat(),
                        user_timezone=user_input.timezone or "UTC",
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
                # When the provider (e.g. Groq on Llama) ignores our
                # tool_choice directive and emits a plain chat reply,
                # `message.content` often scolds the user with bogus
                # "fix the recurrence error" instructions. Surfacing that
                # verbatim is worse than useless — it blames the user for
                # something that's actually a model-side refusal. Return a
                # neutral message instead so the UI falls back cleanly.
                return SuggestionResult(
                    content=(
                        "I couldn't build a structured workflow from that input. "
                        "Try rephrasing with a clearer intent — e.g. 'send an "
                        "email to X after 30 seconds' or 'every Monday 9am call "
                        "https://example.com/api'."
                    ),
                    workflow_draft=None,
                    strategy_used="llm",
                )
            raw_args = message.tool_calls[0].function.arguments
            draft = json.loads(raw_args)
            try:
                draft = _validate_and_fix(draft)
            except DraftFillError as exc:
                # The model returned a structurally incomplete draft (e.g.
                # recurring time trigger with no trigger_at). Don't silently
                # invent values — surface the gap so the user can fix the
                # phrasing, otherwise the workflow fires at a random time.
                return SuggestionResult(
                    content=str(exc),
                    workflow_draft=None,
                    strategy_used="llm",
                )
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


class DraftFillError(ValueError):
    """Raised when the LLM-emitted draft is missing fields we refuse to
    invent (e.g. trigger_at on a recurring time trigger)."""


def _validate_and_fix(draft: dict) -> dict:
    """Ensure required fields exist and have sensible defaults."""
    draft.setdefault("name", "AI-Generated Workflow")
    draft.setdefault("description", "Generated by LLMStrategy")

    trigger = draft.get("trigger") or {}
    t_type = trigger.get("type", "time")
    if t_type == "time":
        # One-time triggers can fall back to "1h from now" — that's only a
        # convenience and the user will see the time in the builder before
        # confirming. But a *recurring* trigger silently anchored to a
        # random future minute means the workflow fires at the wrong time
        # forever. Better to refuse and ask the user to clarify.
        recurrence = trigger.get("recurrence")
        if "trigger_at" not in trigger or trigger["trigger_at"] in (None, ""):
            if recurrence:
                raise DraftFillError(
                    "I couldn't tell when the recurring schedule should "
                    "start. Add a clear time, e.g. 'every Monday at 9am' "
                    "or 'daily at 7:30am UTC'."
                )
            trigger["trigger_at"] = _default_future_iso()
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
        trigger.setdefault("timezone", "UTC")
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
