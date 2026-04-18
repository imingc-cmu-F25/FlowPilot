"""TemplateStrategy — matches a template and fills parameters extracted from raw_text."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from app.suggestion.base import AnalysisResult, SuggestionResult, UserInput
from app.suggestion.strategies.base import SuggestionStrategy


def _extract_email(text: str) -> str:
    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    return m.group(0) if m else ""


def _extract_url(text: str) -> str:
    m = re.search(r"https?://\S+", text)
    return m.group(0) if m else ""


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


def _extract_hour(text: str) -> int | None:
    m = re.search(r"(\d{1,2})\s*(am|pm)?", text.lower())
    if not m:
        return None
    hour = int(m.group(1))
    suffix = m.group(2)
    if suffix == "pm" and hour < 12:
        hour += 12
    if suffix == "am" and hour == 12:
        hour = 0
    return max(0, min(23, hour))


def _extract_minutes(text: str) -> int | None:
    m = re.search(r"(?:after|in)\s+(\d+)\s*(?:min|minute)", text.lower())
    return int(m.group(1)) if m else None


def _next_iso_at_hour(hour: int) -> str:
    now = datetime.now(UTC)
    target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target.isoformat()


def _iso_after_minutes(minutes: int) -> str:
    return (datetime.now(UTC) + timedelta(minutes=minutes)).isoformat()


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

class _DailyEmailReportTemplate:
    id = "daily_email_report"

    def extract_params(self, text: str) -> dict:
        return {
            "hour": _extract_hour(text) or 9,
            "to": _extract_email(text),
            "subject": _extract_subject(text) or "Daily Report",
            "body": _extract_body(text) or "Here is your daily report.",
        }

    def fill(self, params: dict) -> dict:
        return {
            "name": "Daily Email Report",
            "description": f"Sends a daily report email at {params['hour']}:00 UTC.",
            "trigger": {
                "type": "time",
                "trigger_at": _next_iso_at_hour(params["hour"]),
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
                    "name": "Send Daily Report",
                    "step_order": 0,
                    "to_template": params["to"],
                    "subject_template": params["subject"],
                    "body_template": params["body"],
                }
            ],
        }


class _WeeklySummaryTemplate:
    id = "weekly_summary"

    def extract_params(self, text: str) -> dict:
        return {
            "hour": _extract_hour(text) or 9,
            "to": _extract_email(text),
            "subject": _extract_subject(text) or "Weekly Summary",
            "body": _extract_body(text) or "Here is your weekly summary.",
        }

    def fill(self, params: dict) -> dict:
        return {
            "name": "Weekly Summary",
            "description": f"Sends a weekly summary email at {params['hour']}:00 UTC every Monday.",
            "trigger": {
                "type": "time",
                "trigger_at": _next_iso_at_hour(params["hour"]),
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
                    "name": "Send Weekly Summary",
                    "step_order": 0,
                    "to_template": params["to"],
                    "subject_template": params["subject"],
                    "body_template": params["body"],
                }
            ],
        }


class _WebhookToEmailTemplate:
    id = "webhook_to_email"

    def extract_params(self, text: str) -> dict:
        return {
            "to": _extract_email(text),
            "subject": _extract_subject(text) or "Incoming Webhook Notification",
            "body": _extract_body(text) or "Webhook payload received:\n\n{{previous_output}}",
        }

    def fill(self, params: dict) -> dict:
        return {
            "name": "Webhook → Email",
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
                    "to_template": params["to"],
                    "subject_template": params["subject"],
                    "body_template": params["body"],
                }
            ],
        }


class _WebhookToApiTemplate:
    id = "webhook_to_api"

    def extract_params(self, text: str) -> dict:
        return {"url": _extract_url(text)}

    def fill(self, params: dict) -> dict:
        return {
            "name": "Webhook → API Call",
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
                    "url_template": params["url"],
                    "headers": {"Content-Type": "application/json"},
                }
            ],
        }


class _ScheduledHttpPingTemplate:
    id = "scheduled_http_ping"

    def extract_params(self, text: str) -> dict:
        return {
            "url": _extract_url(text),
            "hour": _extract_hour(text) or 9,
        }

    def fill(self, params: dict) -> dict:
        return {
            "name": "Scheduled HTTP Ping",
            "description": (
                f"Pings {params['url'] or 'endpoint'}"
                f" every hour starting at"
                f" {params['hour']}:00 UTC."
            ),
            "trigger": {
                "type": "time",
                "trigger_at": _next_iso_at_hour(params["hour"]),
                "timezone": "UTC",
                "recurrence": {
                    "frequency": "hourly",
                    "interval": 1,
                    "days_of_week": [],
                    "cron_expression": "",
                },
            },
            "steps": [
                {
                    "action_type": "http_request",
                    "name": "Ping Endpoint",
                    "step_order": 0,
                    "method": "GET",
                    "url_template": params["url"],
                    "headers": {},
                }
            ],
        }


class _HealthCheckAlertTemplate:
    id = "health_check_alert"

    def extract_params(self, text: str) -> dict:
        return {
            "url": _extract_url(text),
            "to": _extract_email(text),
            "hour": _extract_hour(text) or 9,
            "subject": _extract_subject(text) or "Health Check Result",
            "body": _extract_body(text) or "Health check result:\n\n{{previous_output}}",
        }

    def fill(self, params: dict) -> dict:
        return {
            "name": "Health Check & Alert",
            "description": f"Checks {params['url'] or 'endpoint'} hourly and emails the result.",
            "trigger": {
                "type": "time",
                "trigger_at": _next_iso_at_hour(params["hour"]),
                "timezone": "UTC",
                "recurrence": {
                    "frequency": "hourly",
                    "interval": 1,
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
                    "url_template": params["url"],
                    "headers": {},
                },
                {
                    "action_type": "send_email",
                    "name": "Send Alert",
                    "step_order": 1,
                    "to_template": params["to"],
                    "subject_template": params["subject"],
                    "body_template": params["body"],
                },
            ],
        }


class _FetchAndEmailTemplate:
    id = "fetch_and_email"

    def extract_params(self, text: str) -> dict:
        return {
            "url": _extract_url(text),
            "to": _extract_email(text),
            "hour": _extract_hour(text) or 9,
            "subject": _extract_subject(text) or "Data Report",
            "body": _extract_body(text) or "Here is the fetched data:\n\n{{previous_output}}",
        }

    def fill(self, params: dict) -> dict:
        return {
            "name": "Fetch Data & Email Report",
            "description": "Fetches data from an API and emails the results.",
            "trigger": {
                "type": "time",
                "trigger_at": _next_iso_at_hour(params["hour"]),
                "timezone": "UTC",
                "recurrence": None,
            },
            "steps": [
                {
                    "action_type": "http_request",
                    "name": "Fetch Data",
                    "step_order": 0,
                    "method": "GET",
                    "url_template": params["url"],
                    "headers": {},
                },
                {
                    "action_type": "send_email",
                    "name": "Email Results",
                    "step_order": 1,
                    "to_template": params["to"],
                    "subject_template": params["subject"],
                    "body_template": params["body"],
                },
            ],
        }


class _DelayedEmailTemplate:
    id = "delayed_email"

    def extract_params(self, text: str) -> dict:
        minutes = _extract_minutes(text) or 5
        return {
            "minutes": minutes,
            "to": _extract_email(text),
            "subject": _extract_subject(text) or "Scheduled Notification",
            "body": (
                _extract_body(text)
                or f"This is your scheduled email,"
                f" sent {minutes} minutes"
                f" after creation."
            ),
        }

    def fill(self, params: dict) -> dict:
        minutes = params["minutes"]
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
                    "to_template": params["to"],
                    "subject_template": params["subject"],
                    "body_template": params["body"],
                }
            ],
        }


class TemplateStrategy(SuggestionStrategy):
    """Matches input_type to a template, extracts params, fills skeleton."""

    TEMPLATES = {
        "delayed_email": _DelayedEmailTemplate(),
        "daily_email_report": _DailyEmailReportTemplate(),
        "weekly_summary": _WeeklySummaryTemplate(),
        "webhook_to_email": _WebhookToEmailTemplate(),
        "webhook_to_api": _WebhookToApiTemplate(),
        "scheduled_http_ping": _ScheduledHttpPingTemplate(),
        "health_check_alert": _HealthCheckAlertTemplate(),
        "fetch_and_email": _FetchAndEmailTemplate(),
    }

    def __init__(self, analysis: AnalysisResult | None = None) -> None:
        self._analysis = analysis

    def set_analysis(self, analysis: AnalysisResult) -> None:
        self._analysis = analysis

    @staticmethod
    def _strip_quoted(text: str) -> str:
        """Remove quoted strings so keyword matching only considers the intent."""
        text = re.sub(r'"[^"]*"', "", text)
        text = re.sub(r"'[^']*'", "", text)
        return text

    def _pick_template(self, user_input: UserInput):
        text = self._strip_quoted(user_input.raw_text).lower()

        # delayed email
        if re.search(r"(after|in)\s+\d+\s*(min|minute)", text) and any(
            k in text for k in ("email", "send", "mail")
        ):
            return self.TEMPLATES["delayed_email"]

        # health check + alert (multi-step)
        if any(k in text for k in ("check", "monitor", "health", "ping", "status")) and any(
            k in text for k in ("email", "alert", "notify")
        ):
            return self.TEMPLATES["health_check_alert"]

        # fetch data and email (multi-step)
        if any(k in text for k in ("fetch", "get", "pull")) and any(
            k in text for k in ("email", "send", "mail", "report")
        ):
            return self.TEMPLATES["fetch_and_email"]

        # webhook → API
        if any(k in text for k in ("webhook", "hook")) and any(
            k in text for k in ("call", "api", "request", "deploy", "trigger")
        ):
            return self.TEMPLATES["webhook_to_api"]

        # webhook → email
        if any(k in text for k in ("webhook", "hook")) and any(
            k in text for k in ("email", "send", "forward", "notify")
        ):
            return self.TEMPLATES["webhook_to_email"]

        # weekly
        if "weekly" in text or "every week" in text:
            return self.TEMPLATES["weekly_summary"]

        # scheduled HTTP ping
        if ("ping" in text or "health" in text) and ("http" in text or "://" in text):
            return self.TEMPLATES["scheduled_http_ping"]

        # daily
        if "daily" in text or "every day" in text:
            return self.TEMPLATES["daily_email_report"]

        return None

    async def generate_suggestion(self, user_input: UserInput) -> SuggestionResult:
        template = self._pick_template(user_input)
        if template is None:
            return SuggestionResult(
                content="No matching template found for this input.",
                workflow_draft=None,
                strategy_used="template",
            )
        params = template.extract_params(user_input.raw_text)
        draft = template.fill(params)
        return SuggestionResult(
            content=f"Used template '{template.id}' with your parameters.",
            workflow_draft=draft,
            strategy_used="template",
        )
