"""SuggestionService — orchestrates Analyzer → Selector → Strategy → Rephraser → Repo."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.schema import SuggestionORM
from app.suggestion.analyzer import AIAnalyzer
from app.suggestion.base import (
    AnalysisResult,
    PendingQuestion,
    SuggestionResult,
    UserInput,
)
from app.suggestion.context import SuggestionContext
from app.suggestion.rephraser import AIRephraser
from app.suggestion.repo import SuggestionRepository
from app.suggestion.selector import StrategySelector

# Sentinel paths that strategies emit when they don't have a real value
# from the user. Treated as "missing" by the question detector.
_WEBHOOK_PATH_SENTINELS = {"", "/hooks/incoming", "/hooks/trigger"}

# Substrings that mean "this URL is a placeholder, not a real endpoint".
# Triggered for http_request.url_template; we'd rather re-ask the user
# than let the workflow fire and get a 404 / connection error at runtime.
_PLACEHOLDER_URL_FRAGMENTS = (
    "example.com",
    "example.org",
    "example.net",
    "your-",
    "yourdomain",
    "yoursite",
    "fillme",
    "placeholder",
    "xxx",
    "txxx",
    "bxxx",
    "{token}",
    "<your",
    "<token",
    "<url",
)
# Slack-specific gotcha: app.slack.com/client/... is the channel viewer
# URL, not an incoming webhook. Users routinely paste it expecting it to
# work. The real webhook lives on hooks.slack.com.
_SLACK_NON_WEBHOOK_URLS = (
    "app.slack.com/client/",
    "slack.com/archives/",
)


_SLACK_TOKEN_PREFIXES = (
    "xoxa-", "xoxb-", "xoxc-", "xoxe-", "xoxp-", "xoxr-", "xoxs-", "xapp-",
)


def _diagnose_url_template(url: str) -> str | None:
    """If `url` is obviously not a real endpoint, return a hint string the
    UI can show alongside the question. Returns None when the URL looks
    plausibly real."""
    lower = url.lower()
    # Token confusion is very common with Slack — users grab the token
    # off the OAuth page and paste it where the webhook URL should go.
    # Treating it as a URL leaks the token to logs and triggers httpx's
    # "missing http(s)://" error at run time.
    if lower.startswith(_SLACK_TOKEN_PREFIXES):
        return (
            "That looks like a Slack token (xox*-...), not a URL. "
            "Tokens belong in Slack API auth headers, not in url_template. "
            "What you want here is an Incoming Webhook URL like "
            "https://hooks.slack.com/services/T.../B.../..."
        )
    # Anything that isn't a fully-qualified URL won't even reach the
    # remote server — better to ask now than to fail mid-run.
    if not (lower.startswith("http://") or lower.startswith("https://")):
        return (
            "URL must start with http:// or https://. "
            "If this is a Slack endpoint, paste the full Incoming "
            "Webhook URL (https://hooks.slack.com/services/T.../B.../...)."
        )
    if any(frag in lower for frag in _SLACK_NON_WEBHOOK_URLS):
        return (
            "That looks like a Slack channel viewer URL, not an "
            "Incoming Webhook. Generate one in https://api.slack.com/apps "
            "→ your app → Incoming Webhooks; it should look like "
            "https://hooks.slack.com/services/T.../B.../..."
        )
    if any(frag in lower for frag in _PLACEHOLDER_URL_FRAGMENTS):
        return "That URL looks like a placeholder. Paste a real endpoint."
    return None

_TOO_SHORT_MESSAGE = (
    "Your request is too short for me to understand what to automate. "
    "Try describing it as a full sentence, e.g. "
    "'send an email to team@acme.com every Monday at 9am', "
    "'notify me in Slack after 30 seconds', "
    "or 'when a webhook hits /hooks/github-push, call my deploy API'."
)

# Triggered when the analyzer is confident the input isn't a workflow
# request at all (small talk, jokes, general questions, etc.). The
# threshold mirrors the prompt's "confidence >= 0.9" instruction; the
# heuristic fallback is also tuned to emit exactly that pattern.
_NOT_A_WORKFLOW_MESSAGE = (
    "I help build *workflow automations* — things like scheduled emails, "
    "webhook handlers, or calendar-driven tasks. Your message doesn't "
    "look like an automation request. Try something like: "
    "'every Monday at 9am email me last week's metrics', "
    "'when a webhook hits /hooks/github-push, call my deploy API', "
    "or 'each morning email me my schedule for today'."
)
_OFF_TOPIC_CONFIDENCE_THRESHOLD = 0.8


def detect_pending_questions(draft: dict | None) -> list[PendingQuestion]:
    """Scan a draft and return clarifying questions for empty / sentinel
    fields the user must fill before the workflow can be created.

    Centralised here (rather than per-strategy) so all three strategies
    share the same gaps detection. Field paths are dotted, mirroring the
    flat draft shape strategies emit, e.g. `trigger.path` or
    `steps.0.to_template`.
    """
    if not draft:
        return []
    questions: list[PendingQuestion] = []

    trigger = draft.get("trigger") or {}
    if trigger.get("type") == "webhook":
        path = (trigger.get("path") or "").strip()
        if path in _WEBHOOK_PATH_SENTINELS:
            questions.append(
                PendingQuestion(
                    field="trigger.path",
                    question=(
                        "What URL path should this webhook listen on? "
                        "It must start with /hooks/."
                    ),
                    example="/hooks/github-push",
                    suggested_value=path or "/hooks/",
                )
            )

    for i, step in enumerate(draft.get("steps") or []):
        action_type = step.get("action_type")
        if action_type == "send_email":
            if not (step.get("to_template") or "").strip():
                questions.append(
                    PendingQuestion(
                        field=f"steps.{i}.to_template",
                        question="Who should receive this email?",
                        example="ops@acme.com",
                    )
                )
        elif action_type == "http_request":
            url = (step.get("url_template") or "").strip()
            if not url:
                questions.append(
                    PendingQuestion(
                        field=f"steps.{i}.url_template",
                        question="Which URL should this HTTP request hit?",
                        example="https://hooks.slack.com/services/T.../B.../...",
                    )
                )
            else:
                hint = _diagnose_url_template(url)
                if hint is not None:
                    questions.append(
                        PendingQuestion(
                            field=f"steps.{i}.url_template",
                            question=hint,
                            example="https://hooks.slack.com/services/T.../B.../...",
                            suggested_value="",
                        )
                    )

    return questions


def _looks_too_short(text: str) -> bool:
    """Return True when raw_text is too short / malformed to interpret.

    We intentionally gate this *before* the analyzer → strategy pipeline so
    the user gets an actionable hint rather than a stale template match or
    a confused LLM response. Generous thresholds — valid short prompts like
    'send email to a@b.com daily' have to still pass.
    """
    stripped = text.strip()
    if len(stripped) < 5:
        return True
    if not any(c.isalpha() for c in stripped):
        return True
    # Need at least one 3+ character word. Catches inputs like "a b c d e"
    # or "?? ?? ??" that superficially pass the length check.
    words = [w for w in stripped.split() if any(c.isalpha() for c in w)]
    if not any(len(w) >= 3 for w in words):
        return True
    return False


class SuggestionService:
    def __init__(
        self,
        db: Session,
        analyzer: AIAnalyzer | None = None,
        selector: StrategySelector | None = None,
        context: SuggestionContext | None = None,
        rephraser: AIRephraser | None = None,
    ) -> None:
        self._analyzer = analyzer or AIAnalyzer()
        self._selector = selector or StrategySelector()
        self._context = context or SuggestionContext()
        self._rephraser = rephraser or AIRephraser()
        self._repo = SuggestionRepository(db)

    async def suggest(self, user_input: UserInput) -> SuggestionORM:
        # Short-circuit garbage / single-word inputs before spending any
        # LLM quota. A "guard" strategy_used value marks the row so UI/ops
        # can filter these out of usage analytics.
        if _looks_too_short(user_input.raw_text):
            analysis = AnalysisResult(
                complexity_level="simple",
                input_type="too_short",
                confidence=1.0,
            )
            result = SuggestionResult(
                content=_TOO_SHORT_MESSAGE,
                workflow_draft=None,
                strategy_used="guard",
            )
            return self._repo.save(user_input, analysis, result)

        analysis = await self._analyzer.analyze(user_input)

        # Second guard: the analyzer (LLM or heuristic) flagged this as
        # not-a-workflow with high confidence. Skip the strategy pipeline
        # and reply with a friendly nudge instead of letting the LLM
        # build a nonsense draft for "tell me a joke".
        if (
            analysis.input_type == "other"
            and analysis.confidence >= _OFF_TOPIC_CONFIDENCE_THRESHOLD
        ):
            result = SuggestionResult(
                content=_NOT_A_WORKFLOW_MESSAGE,
                workflow_draft=None,
                strategy_used="guard",
            )
            return self._repo.save(user_input, analysis, result)

        strategy = self._selector.select_strategy(analysis)
        self._context.set_strategy(strategy)
        result = await self._context.execute(user_input)

        # Fallback: if non-LLM strategy returns no draft, re-route to LLM.
        if result.workflow_draft is None and result.strategy_used != "llm":
            self._context.set_strategy(self._selector.llm_fallback)
            result = await self._context.execute(user_input)

        # Rephraser only adds value to free-form LLM-generated content
        # describing an actual draft. Skipping it for canned strings
        # (rule_based / template / guard) saves an LLM round-trip; more
        # importantly, skipping it when there's no draft prevents the
        # rephraser from "polishing" our sanitized fallback message back
        # into model gibberish (the no-tool-call branch hits this).
        if (
            result.strategy_used == "llm"
            and result.content
            and result.workflow_draft is not None
        ):
            result = await self._rephraser.rephrase(result)

        # Tag any sentinel / blank fields so the UI can prompt the user
        # for them before they accept the draft.
        questions = detect_pending_questions(result.workflow_draft)
        if questions:
            result = result.model_copy(update={"pending_questions": questions})
        return self._repo.save(user_input, analysis, result)

    @property
    def repo(self) -> SuggestionRepository:
        return self._repo
