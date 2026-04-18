"""RuleBasedStrategy — keyword/regex matching → preset workflow drafts. Zero LLM cost."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from app.suggestion.base import SuggestionResult, UserInput
from app.suggestion.strategies.base import SuggestionStrategy


def _extract_hour(text: str) -> int:
    m = re.search(r"(\d{1,2})\s*(am|pm)?", text.lower())
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


def _next_iso_at_hour(hour: int) -> str:
    now = datetime.now(UTC)
    target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target.isoformat()


def _iso_after_minutes(minutes: int) -> str:
    return (datetime.now(UTC) + timedelta(minutes=minutes)).isoformat()


# ---------------------------------------------------------------------------
# Draft builders
# ---------------------------------------------------------------------------

def _build_delayed_email_draft(text: str) -> dict:
    """'send email after N minutes'"""
    minutes = _extract_minutes(text) or 5
    to = _extract_email(text)
    subject = _extract_subject(text) or "Scheduled Notification"
    body = _extract_body(text) or f"This is your scheduled email, sent {minutes} minutes after creation."
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


def _build_daily_email_draft(text: str) -> dict:
    hour = _extract_hour(text)
    to = _extract_email(text)
    subject = _extract_subject(text) or "Daily Update"
    body = _extract_body(text) or "Here is your daily update summary."
    return {
        "name": "Daily Email",
        "description": f"Sends a daily email at {hour}:00 UTC.",
        "trigger": {
            "type": "time",
            "trigger_at": _next_iso_at_hour(hour),
            "timezone": "UTC",
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


def _build_weekly_email_draft(text: str) -> dict:
    hour = _extract_hour(text)
    to = _extract_email(text)
    subject = _extract_subject(text) or "Weekly Summary"
    body = _extract_body(text) or "Here is your weekly summary report."
    return {
        "name": "Weekly Email",
        "description": f"Sends a weekly email at {hour}:00 UTC every Monday.",
        "trigger": {
            "type": "time",
            "trigger_at": _next_iso_at_hour(hour),
            "timezone": "UTC",
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


def _build_webhook_to_email_draft(text: str) -> dict:
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


def _build_webhook_to_api_draft(text: str) -> dict:
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


def _build_interval_trigger_draft(text: str) -> dict:
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


def _build_health_check_draft(text: str) -> dict:
    url = _extract_url(text)
    to = _extract_email(text)
    subject = _extract_subject(text) or "Health Check Result"
    body = _extract_body(text) or "Health check result:\n\n{{previous_output}}"
    interval, unit = _extract_interval(text) if re.search(r"every|each", text.lower()) else (1, "hour")
    freq_map = {"minute": "minutely", "hour": "hourly", "day": "daily", "week": "weekly"}
    frequency = freq_map.get(unit, "hourly")
    return {
        "name": "Health Check & Alert",
        "description": f"Checks {url or 'endpoint'} every {interval} {unit}(s) and sends an alert email.",
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


def _build_http_call_draft(text: str) -> dict:
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


def _build_fetch_and_email_draft(text: str) -> dict:
    url = _extract_url(text)
    to = _extract_email(text)
    subject = _extract_subject(text) or "Data Report"
    body = _extract_body(text) or "Here is the fetched data:\n\n{{previous_output}}"
    return {
        "name": "Fetch Data & Email Report",
        "description": "Fetches data from an API and emails the results.",
        "trigger": {
            "type": "time",
            "trigger_at": _next_iso_at_hour(_extract_hour(text)),
            "timezone": "UTC",
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


class RuleBasedStrategy(SuggestionStrategy):
    """Matches hard-coded regex patterns against raw_text. Returns preset drafts."""

    RULES: list[tuple[str, callable]] = [
        # delayed email: "send email after 5 minutes"
        (r"(send|email).*(after|in)\s+\d+\s*(min|minute)", _build_delayed_email_draft),
        (r"(after|in)\s+\d+\s*(min|minute).*(send|email)", _build_delayed_email_draft),
        # health check + alert: "check health ... email"
        (r"(check|monitor|ping).*(health|status|uptime).*(email|alert|notify)", _build_health_check_draft),
        (r"(health|status).*(check|monitor).*(email|alert|notify)", _build_health_check_draft),
        # fetch data and email
        (r"(fetch|get|pull).*(data|report|result).*(email|send|mail)", _build_fetch_and_email_draft),
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
                draft = builder(text)
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
