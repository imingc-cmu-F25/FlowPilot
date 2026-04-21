"""RuleBasedStrategy — keyword/regex matching → preset workflow drafts. Zero LLM cost."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.suggestion.base import SuggestionResult, UserInput
from app.suggestion.strategies.base import SuggestionStrategy


def _resolve_zone(tz_name: str | None) -> ZoneInfo:
    """Best-effort IANA timezone lookup; falls back to UTC silently.

    The frontend should always send a valid zone, but a malformed value
    must not crash the suggestion pipeline — UTC is the safe default
    matching the prior pre-timezone behaviour.
    """
    if not tz_name:
        return ZoneInfo("UTC")
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _extract_hour(text: str) -> int:
    """Pull an "at HH am/pm" hour out of the prompt.

    Bare digits anywhere in the text (email handles like alice2@acme.com,
    or '30' inside 'after 30 seconds') used to be claimed as the hour,
    which silently shifted the schedule. Now we require either an
    am/pm suffix or an explicit "at" anchor.
    """
    lower = text.lower()
    # First preference: explicit `at HH(:MM)? (am|pm)?`.
    m = re.search(r"\bat\s+(\d{1,2})(?::\d{2})?\s*(am|pm)?\b", lower)
    # Fallback: any `HH am/pm` standalone.
    if not m:
        m = re.search(r"\b(\d{1,2})\s*(am|pm)\b", lower)
    if not m:
        return 9
    hour = int(m.group(1))
    suffix = m.group(2)
    if suffix == "pm" and hour < 12:
        hour += 12
    if suffix == "am" and hour == 12:
        hour = 0
    return max(0, min(23, hour))


def _extract_email(text: str) -> str:
    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    return m.group(0) if m else ""


def _extract_url(text: str) -> str:
    m = re.search(r"https?://\S+", text)
    return m.group(0) if m else ""


def _extract_minutes(text: str) -> int | None:
    m = re.search(r"(?:after|in)\s+(\d+)\s*(?:min|minute)", text.lower())
    return int(m.group(1)) if m else None


def _extract_delay_seconds(text: str) -> int | None:
    """Match 'after N seconds' / 'in N sec'. Distinct from minutes so we
    can fire on a sub-minute trigger without round-up."""
    m = re.search(r"(?:after|in)\s+(\d+)\s*(?:sec|second)s?\b", text.lower())
    return int(m.group(1)) if m else None


def _extract_interval(text: str) -> tuple[int, str]:
    m = re.search(r"(?:every|each)\s+(\d+)\s+(minute|hour|day|week)", text.lower())
    if m:
        return int(m.group(1)), m.group(2)
    return 1, "hour"


def _extract_subject(text: str) -> str:
    m = re.search(r'(?:subject|title)\s*[:=]?\s*"([^"]+)"', text, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"(?:subject|title)\s*[:=]?\s*'([^']+)'", text, re.IGNORECASE)
    if m:
        return m.group(1)
    return ""


def _extract_body(text: str) -> str:
    m = re.search(r'(?:body|content|message|saying)\s*[:=]?\s*"([^"]+)"', text, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"(?:body|content|message|saying)\s*[:=]?\s*'([^']+)'", text, re.IGNORECASE)
    if m:
        return m.group(1)
    return ""


def _extract_calendar_title(text: str) -> str:
    """Pull a calendar event title filter out of phrases like 'titled "1:1"'."""
    m = re.search(r'(?:titled|named|called)\s*[:=]?\s*"([^"]+)"', text, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"(?:titled|named|called)\s*[:=]?\s*'([^']+)'", text, re.IGNORECASE)
    if m:
        return m.group(1)
    return ""


def _next_iso_at_hour(hour: int, tz_name: str | None = None) -> str:
    """ISO datetime for the next HH:00 in the user's local timezone,
    serialised as an absolute (UTC-converted) instant."""
    zone = _resolve_zone(tz_name)
    now_local = datetime.now(zone)
    target_local = now_local.replace(hour=hour, minute=0, second=0, microsecond=0)
    if target_local <= now_local:
        target_local += timedelta(days=1)
    return target_local.astimezone(UTC).isoformat()


def _iso_at_hour_on_date(
    hour: int, *, days_offset: int, tz_name: str | None = None
) -> str:
    """ISO datetime at HH:00 in the user's local timezone, `days_offset`
    days from today, serialised as a UTC instant."""
    zone = _resolve_zone(tz_name)
    target_local = (datetime.now(zone) + timedelta(days=days_offset)).replace(
        hour=hour, minute=0, second=0, microsecond=0
    )
    return target_local.astimezone(UTC).isoformat()


def _iso_after_minutes(minutes: int) -> str:
    return (datetime.now(UTC) + timedelta(minutes=minutes)).isoformat()


def _iso_after_seconds(seconds: int) -> str:
    return (datetime.now(UTC) + timedelta(seconds=seconds)).isoformat()


# ---------------------------------------------------------------------------
# Draft builders
# ---------------------------------------------------------------------------

def _build_one_time_email_at_hour_draft(text: str, *, tz_name: str | None = None) -> dict:
    """'send email to X at 9AM tomorrow' — one-time time trigger."""
    hour = _extract_hour(text)
    lower = text.lower()
    zone = _resolve_zone(tz_name)
    days_offset = 1 if "tomorrow" in lower else 0
    # If the user said "today" but the hour has already passed in their
    # local timezone, schedule tomorrow instead — otherwise the trigger
    # fires in the past and would be skipped by the scheduler.
    if days_offset == 0:
        if hour <= datetime.now(zone).hour:
            days_offset = 1
    to = _extract_email(text)
    subject = _extract_subject(text) or "Scheduled email"
    body = _extract_body(text) or f"This is your scheduled {hour}:00 email."
    when = "tomorrow" if days_offset == 1 else "today"
    return {
        "name": f"Send Email at {hour}:00 ({when})",
        "description": (
            f"Sends a one-time email at {hour}:00 {tz_name or 'UTC'} {when}."
        ),
        "trigger": {
            "type": "time",
            "trigger_at": _iso_at_hour_on_date(
                hour, days_offset=days_offset, tz_name=tz_name
            ),
            "timezone": tz_name or "UTC",
            "recurrence": None,
        },
        "steps": [
            {
                "action_type": "send_email",
                "name": "Send Scheduled Email",
                "step_order": 0,
                "to_template": to,
                "subject_template": subject,
                "body_template": body,
            }
        ],
    }


def _build_delayed_email_draft(text: str, *, tz_name: str | None = None) -> dict:
    """'send email after N minutes' — relative delay, timezone irrelevant."""
    minutes = _extract_minutes(text) or 5
    to = _extract_email(text)
    subject = _extract_subject(text) or "Scheduled Notification"
    body = (
        _extract_body(text)
        or f"This is your scheduled email, sent"
        f" {minutes} minutes after creation."
    )
    return {
        "name": f"Send Email After {minutes} Minutes",
        "description": f"Sends an email {minutes} minutes from now.",
        "trigger": {
            "type": "time",
            "trigger_at": _iso_after_minutes(minutes),
            "timezone": "UTC",
            "recurrence": None,
        },
        "steps": [
            {
                "action_type": "send_email",
                "name": "Send Delayed Email",
                "step_order": 0,
                "to_template": to,
                "subject_template": subject,
                "body_template": body,
            }
        ],
    }


def _build_delayed_email_seconds_draft(text: str, *, tz_name: str | None = None) -> dict:
    """'send email after N seconds' — sub-minute delayed email."""
    seconds = _extract_delay_seconds(text) or 30
    to = _extract_email(text)
    subject = _extract_subject(text) or "Scheduled Notification"
    body = (
        _extract_body(text)
        or f"This is your scheduled email, sent"
        f" {seconds} seconds after creation."
    )
    return {
        "name": f"Send Email After {seconds} Seconds",
        "description": f"Sends an email {seconds} seconds from now.",
        "trigger": {
            "type": "time",
            "trigger_at": _iso_after_seconds(seconds),
            "timezone": "UTC",
            "recurrence": None,
        },
        "steps": [
            {
                "action_type": "send_email",
                "name": "Send Delayed Email",
                "step_order": 0,
                "to_template": to,
                "subject_template": subject,
                "body_template": body,
            }
        ],
    }


def _build_daily_email_draft(text: str, *, tz_name: str | None = None) -> dict:
    hour = _extract_hour(text)
    to = _extract_email(text)
    subject = _extract_subject(text) or "Daily Update"
    body = _extract_body(text) or "Here is your daily update summary."
    tz_label = tz_name or "UTC"
    return {
        "name": "Daily Email",
        "description": f"Sends a daily email at {hour}:00 {tz_label}.",
        "trigger": {
            "type": "time",
            "trigger_at": _next_iso_at_hour(hour, tz_name=tz_name),
            "timezone": tz_label,
            "recurrence": {
                "frequency": "daily",
                "interval": 1,
                "days_of_week": [],
                "cron_expression": "",
            },
        },
        "steps": [
            {
                "action_type": "send_email",
                "name": "Send Daily Email",
                "step_order": 0,
                "to_template": to,
                "subject_template": subject,
                "body_template": body,
            }
        ],
    }


def _build_weekly_email_draft(text: str, *, tz_name: str | None = None) -> dict:
    hour = _extract_hour(text)
    to = _extract_email(text)
    subject = _extract_subject(text) or "Weekly Summary"
    body = _extract_body(text) or "Here is your weekly summary report."
    tz_label = tz_name or "UTC"
    return {
        "name": "Weekly Email",
        "description": f"Sends a weekly email at {hour}:00 {tz_label} every Monday.",
        "trigger": {
            "type": "time",
            "trigger_at": _next_iso_at_hour(hour, tz_name=tz_name),
            "timezone": tz_label,
            "recurrence": {
                "frequency": "weekly",
                "interval": 1,
                "days_of_week": [1],
                "cron_expression": "",
            },
        },
        "steps": [
            {
                "action_type": "send_email",
                "name": "Send Weekly Email",
                "step_order": 0,
                "to_template": to,
                "subject_template": subject,
                "body_template": body,
            }
        ],
    }


def _build_webhook_to_email_draft(text: str, *, tz_name: str | None = None) -> dict:
    to = _extract_email(text)
    subject = _extract_subject(text) or "Incoming Webhook Notification"
    body = _extract_body(text) or "Webhook payload received:\n\n{{previous_output}}"
    return {
        "name": "Webhook to Email",
        "description": "Forwards incoming webhook payloads via email.",
        "trigger": {
            "type": "webhook",
            "path": "/hooks/incoming",
            "method": "POST",
            "secret_ref": "",
            "event_filter": "",
        },
        "steps": [
            {
                "action_type": "send_email",
                "name": "Forward to Email",
                "step_order": 0,
                "to_template": to,
                "subject_template": subject,
                "body_template": body,
            }
        ],
    }


def _build_webhook_to_api_draft(text: str, *, tz_name: str | None = None) -> dict:
    url = _extract_url(text)
    return {
        "name": "Webhook to API Call",
        "description": "Calls an external API when a webhook is received.",
        "trigger": {
            "type": "webhook",
            "path": "/hooks/incoming",
            "method": "POST",
            "secret_ref": "",
            "event_filter": "",
        },
        "steps": [
            {
                "action_type": "http_request",
                "name": "Call API",
                "step_order": 0,
                "method": "POST",
                "url_template": url,
                "headers": {"Content-Type": "application/json"},
            }
        ],
    }


def _build_interval_trigger_draft(text: str, *, tz_name: str | None = None) -> dict:
    interval, unit = _extract_interval(text)
    freq_map = {"minute": "minutely", "hour": "hourly", "day": "daily", "week": "weekly"}
    frequency = freq_map.get(unit, "hourly")
    url = _extract_url(text)
    return {
        "name": f"Every {interval} {unit}(s)",
        "description": f"Runs an HTTP request every {interval} {unit}(s).",
        "trigger": {
            "type": "time",
            "trigger_at": _next_iso_at_hour(datetime.now(UTC).hour),
            "timezone": "UTC",
            "recurrence": {
                "frequency": frequency,
                "interval": interval,
                "days_of_week": [],
                "cron_expression": "",
            },
        },
        "steps": [
            {
                "action_type": "http_request",
                "name": "HTTP Request",
                "step_order": 0,
                "method": "GET",
                "url_template": url,
                "headers": {},
            }
        ],
    }


def _build_health_check_draft(text: str, *, tz_name: str | None = None) -> dict:
    url = _extract_url(text)
    to = _extract_email(text)
    subject = _extract_subject(text) or "Health Check Result"
    body = _extract_body(text) or "Health check result:\n\n{{previous_output}}"
    interval, unit = (
        _extract_interval(text)
        if re.search(r"every|each", text.lower())
        else (1, "hour")
    )
    freq_map = {"minute": "minutely", "hour": "hourly", "day": "daily", "week": "weekly"}
    frequency = freq_map.get(unit, "hourly")
    return {
        "name": "Health Check & Alert",
        "description": (
            f"Checks {url or 'endpoint'} every"
            f" {interval} {unit}(s) and sends"
            f" an alert email."
        ),
        "trigger": {
            "type": "time",
            "trigger_at": (datetime.now(UTC) + timedelta(minutes=1)).isoformat(),
            "timezone": "UTC",
            "recurrence": {
                "frequency": frequency,
                "interval": interval,
                "days_of_week": [],
                "cron_expression": "",
            },
        },
        "steps": [
            {
                "action_type": "http_request",
                "name": "Check Health",
                "step_order": 0,
                "method": "GET",
                "url_template": url,
                "headers": {},
            },
            {
                "action_type": "send_email",
                "name": "Send Alert",
                "step_order": 1,
                "to_template": to,
                "subject_template": subject,
                "body_template": body,
            },
        ],
    }


def _build_http_call_draft(text: str, *, tz_name: str | None = None) -> dict:
    url = _extract_url(text)
    return {
        "name": "HTTP API Call",
        "description": "Makes an HTTP request to an external API.",
        "trigger": {
            "type": "webhook",
            "path": "/hooks/trigger",
            "method": "POST",
            "secret_ref": "",
            "event_filter": "",
        },
        "steps": [
            {
                "action_type": "http_request",
                "name": "Call API",
                "step_order": 0,
                "method": "GET",
                "url_template": url,
                "headers": {},
            }
        ],
    }


def _build_fetch_and_email_draft(text: str, *, tz_name: str | None = None) -> dict:
    url = _extract_url(text)
    to = _extract_email(text)
    subject = _extract_subject(text) or "Data Report"
    body = _extract_body(text) or "Here is the fetched data:\n\n{{previous_output}}"
    return {
        "name": "Fetch Data & Email Report",
        "description": "Fetches data from an API and emails the results.",
        "trigger": {
            "type": "time",
            "trigger_at": _next_iso_at_hour(_extract_hour(text), tz_name=tz_name),
            "timezone": tz_name or "UTC",
            "recurrence": None,
        },
        "steps": [
            {
                "action_type": "http_request",
                "name": "Fetch Data",
                "step_order": 0,
                "method": "GET",
                "url_template": url,
                "headers": {},
            },
            {
                "action_type": "send_email",
                "name": "Email Results",
                "step_order": 1,
                "to_template": to,
                "subject_template": subject,
                "body_template": body,
            },
        ],
    }


def _build_daily_schedule_email_draft(text: str, *, tz_name: str | None = None) -> dict:
    """'every morning email me today's schedule / calendar / agenda'."""
    hour = _extract_hour(text) or 8
    to = _extract_email(text)
    subject = _extract_subject(text) or "Your schedule for today"
    body = (
        _extract_body(text)
        or "Here are your upcoming calendar events:\n\n{{previous_output}}"
    )
    tz_label = tz_name or "UTC"
    return {
        "name": "Daily Schedule Email",
        "description": (
            f"Each day at {hour}:00 {tz_label}, fetch upcoming calendar "
            f"events and email them."
        ),
        "trigger": {
            "type": "time",
            "trigger_at": _next_iso_at_hour(hour, tz_name=tz_name),
            "timezone": tz_label,
            "recurrence": {
                "frequency": "daily",
                "interval": 1,
                "days_of_week": [],
                "cron_expression": "",
            },
        },
        "steps": [
            {
                "action_type": "calendar_list_upcoming",
                "name": "List Upcoming Events",
                "step_order": 0,
                "calendar_id": "primary",
                "max_results": 10,
                "title_contains": "",
                "window_hours": 24,
            },
            {
                "action_type": "send_email",
                "name": "Email Schedule",
                "step_order": 1,
                "to_template": to,
                "subject_template": subject,
                "body_template": body,
            },
        ],
    }


def _build_calendar_event_to_email_draft(text: str, *, tz_name: str | None = None) -> dict:
    """'when a calendar event (titled X) shows up, email me / notify ...'."""
    to = _extract_email(text)
    title_contains = _extract_calendar_title(text)
    subject = (
        _extract_subject(text)
        or (
            f"New calendar event: {title_contains}"
            if title_contains
            else "New calendar event"
        )
    )
    body = (
        _extract_body(text)
        or "A new event was added to your calendar:\n\n{{previous_output}}"
    )
    return {
        "name": "Calendar Event → Email",
        "description": (
            "Emails a notification whenever a new event appears "
            "in the user's Google Calendar."
            + (f" Filtered to events titled '{title_contains}'." if title_contains else "")
        ),
        "trigger": {
            "type": "calendar_event",
            "calendar_id": "primary",
            "title_contains": title_contains,
            "dedup_seconds": 60,
        },
        "steps": [
            {
                "action_type": "send_email",
                "name": "Send Notification",
                "step_order": 0,
                "to_template": to,
                "subject_template": subject,
                "body_template": body,
            }
        ],
    }


class RuleBasedStrategy(SuggestionStrategy):
    """Matches hard-coded regex patterns against raw_text. Returns preset drafts."""

    RULES: list[tuple[str, callable]] = [
        # one-time scheduled email: "send email at 9am tomorrow" / "today
        # at 9am email me ...". Must come BEFORE the daily-email rules so
        # "tomorrow" doesn't get mis-classified as "every day".
        (
            r"(send|email).*\bat\s+\d{1,2}\s*(am|pm)\b.*\b(tomorrow|today)\b",
            _build_one_time_email_at_hour_draft,
        ),
        (
            r"\b(tomorrow|today)\b.*\bat\s+\d{1,2}\s*(am|pm)\b.*(send|email)",
            _build_one_time_email_at_hour_draft,
        ),
        (
            r"(send|email).*\b(tomorrow|today)\b.*\b\d{1,2}\s*(am|pm)\b",
            _build_one_time_email_at_hour_draft,
        ),
        # delayed email (seconds): "send email after 30 seconds". Must come
        # BEFORE the minute-based rule because the minute regex doesn't
        # match "sec(ond)s" — but guarding explicitly makes ordering safe
        # if the minute pattern is ever broadened.
        (
            r"(send|email).*(after|in)\s+\d+\s*(sec|second)s?\b",
            _build_delayed_email_seconds_draft,
        ),
        (
            r"(after|in)\s+\d+\s*(sec|second)s?\b.*(send|email)",
            _build_delayed_email_seconds_draft,
        ),
        # delayed email: "send email after 5 minutes"
        (r"(send|email).*(after|in)\s+\d+\s*(min|minute)", _build_delayed_email_draft),
        (r"(after|in)\s+\d+\s*(min|minute).*(send|email)", _build_delayed_email_draft),
        # Calendar patterns come BEFORE the generic daily-email rule so
        # "every morning email me my schedule" is not mis-matched to a
        # plain daily email with no calendar step.
        # calendar_event trigger → action: "when a meeting titled X shows up..."
        (
            r"(when|on|if).*(calendar|meeting|event|appointment).*"
            r"(email|send|notify|alert|call|hook|webhook|post|http)",
            _build_calendar_event_to_email_draft,
        ),
        (
            r"(new|add|added|created).*(calendar|meeting|event).*(email|notify|alert)",
            _build_calendar_event_to_email_draft,
        ),
        # daily calendar digest: "every morning email me my schedule"
        (
            r"(every|each)\s+(morning|day|evening|afternoon).*"
            r"(schedule|calendar|agenda|meeting|event|appointment)",
            _build_daily_schedule_email_draft,
        ),
        (
            r"(daily|every day).*(schedule|calendar|agenda|upcoming)",
            _build_daily_schedule_email_draft,
        ),
        (
            r"(schedule|calendar|agenda|upcoming).*(daily|every day|each morning)",
            _build_daily_schedule_email_draft,
        ),
        # health check + alert: "check health ... email"
        (
            r"(check|monitor|ping).*(health|status|uptime).*(email|alert|notify)",
            _build_health_check_draft,
        ),
        (r"(health|status).*(check|monitor).*(email|alert|notify)", _build_health_check_draft),
        # fetch data and email
        (
            r"(fetch|get|pull).*(data|report|result).*(email|send|mail)",
            _build_fetch_and_email_draft,
        ),
        (r"(call|request).*(api|url).*(email|send|forward)", _build_fetch_and_email_draft),
        # daily email
        (r"(every day|daily).*(email|send)", _build_daily_email_draft),
        (r"(email|send).*(every day|daily)", _build_daily_email_draft),
        # weekly email
        (r"(every week|weekly).*(email|send)", _build_weekly_email_draft),
        (r"(email|send).*(every week|weekly)", _build_weekly_email_draft),
        # webhook → email
        (r"webhook.*(forward|send|email)", _build_webhook_to_email_draft),
        (r"(when|on).*(webhook|hook).*(email|send|notify)", _build_webhook_to_email_draft),
        # webhook → API
        (r"webhook.*(call|api|request|trigger)", _build_webhook_to_api_draft),
        (r"(when|on).*(webhook|hook).*(call|api|deploy)", _build_webhook_to_api_draft),
        # interval-based
        (r"(every|each)\s+\d+\s+(minute|hour|day|week)", _build_interval_trigger_draft),
        # one-time email "at HH am/pm" with NO day anchor — comes AFTER
        # daily/weekly rules so "send daily email at 9am" doesn't get
        # mis-classified as one-time. The builder auto-picks today vs
        # tomorrow based on whether the hour has already passed in the
        # user's timezone, so "at 11PM" said in the morning fires today
        # while the same prompt at midnight rolls to tomorrow.
        (
            r"(send|email).*\bat\s+\d{1,2}\s*(am|pm)\b",
            _build_one_time_email_at_hour_draft,
        ),
        (
            r"\bat\s+\d{1,2}\s*(am|pm)\b.*(send|email)",
            _build_one_time_email_at_hour_draft,
        ),
        # generic HTTP call
        (r"(call|request|fetch|hit).*(api|url|endpoint)", _build_http_call_draft),
    ]

    @staticmethod
    def _strip_quoted(text: str) -> str:
        """Remove quoted strings so regex matching only considers the intent."""
        text = re.sub(r'"[^"]*"', "", text)
        text = re.sub(r"'[^']*'", "", text)
        return text

    async def generate_suggestion(self, user_input: UserInput) -> SuggestionResult:
        text = user_input.raw_text
        match_text = self._strip_quoted(text)
        for pattern, builder in self.RULES:
            if re.search(pattern, match_text, re.IGNORECASE):
                draft = builder(text, tz_name=user_input.timezone)
                return SuggestionResult(
                    content=(
                        f"Matched a known pattern. Created a draft workflow "
                        f"named '{draft['name']}'."
                    ),
                    workflow_draft=draft,
                    strategy_used="rule_based",
                )
        return SuggestionResult(
            content="No matching rule found for this input.",
            workflow_draft=None,
            strategy_used="rule_based",
        )
