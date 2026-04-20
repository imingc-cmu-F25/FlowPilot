import json
import logging
import re
from datetime import datetime
from urllib.parse import parse_qs
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.action.actionRegistry import ActionRegistry
from app.core.auth import (
    enforce_owner_match,
    enforce_run_access,
    enforce_workflow_access,
    get_current_user_optional,
)
from app.core.config import settings
from app.db.session import get_db
from app.execution.contracts import enqueue_execute_run
from app.execution.step_run_repo import WorkflowStepRunRepository
from app.reporting.repo import ReportRepository
from app.reporting.service import make_reporting_service
from app.suggestion.base import UserInput
from app.suggestion.repo import SuggestionRepository
from app.suggestion.service import SuggestionService
from app.trigger.customTrigger import AVAILABLE_VARIABLES, dry_run_condition
from app.trigger.service import TriggerService
from app.trigger.triggerConfig import WebhookTriggerConfig
from app.trigger.triggerRegistry import TriggerRegistry
from app.trigger.webhook_auth import verify_webhook_auth
from app.user.repo import UserRepository
from app.workflow.repo import WorkflowRepository
from app.workflow.run import RunStatus, WorkflowRun
from app.workflow.run_repo import WorkflowRunRepository
from app.workflow.service import (
    CreateWorkflowCommand,
    UpdateWorkflowCommand,
    WorkflowService,
    make_workflow_service,
)
from app.workflow.validator import validate_workflow
from app.workflow.workflow import WorkflowDefinition, WorkflowStatus

logger = logging.getLogger(__name__)

api_router = APIRouter()


def _guard_webhook_path_unique(
    db: Session,
    wf: WorkflowDefinition,
    *,
    exclude_workflow_id: UUID | None,
) -> None:
    """Reject the save if another enabled webhook workflow already owns
    the same (path, method). Disabled workflows are ignored — they
    don't route HTTP traffic so they can't shadow anyone.

    Raises HTTPException(409) with a structured body the builder UI
    can display inline next to the ``path`` input. The check is a
    no-op for non-webhook triggers and for workflows saved as
    disabled — a collision only matters at the moment two workflows
    would both fire for the same URL.
    """
    if not wf.enabled:
        return
    trigger = wf.trigger
    if not isinstance(trigger, WebhookTriggerConfig):
        return
    conflict = WorkflowRepository(db).find_enabled_webhook_conflict(
        path=trigger.path,
        method=trigger.method,
        exclude_workflow_id=exclude_workflow_id,
    )
    if conflict is None:
        return
    raise HTTPException(
        status_code=409,
        detail={
            "message": (
                f"Another enabled workflow already listens on "
                f"{trigger.method.upper()} {trigger.path}. Pick a different path or "
                f"disable the other workflow first."
            ),
            "errors": [
                {
                    "field": "trigger.path",
                    "message": "Path already in use by another enabled webhook workflow",
                }
            ],
            "conflicting_workflow_id": str(conflict),
        },
    )


def _format_validation_errors(exc: ValidationError) -> dict:
    errors = []
    for err in exc.errors():
        loc = ".".join(str(part) for part in err.get("loc", []))
        errors.append({"field": loc, "message": err.get("msg", "Invalid value")})
    return {"message": "Validation failed", "errors": errors}


def _format_value_error(exc: ValueError) -> dict:
    return {"message": str(exc)}


def _format_integrity_error(exc: IntegrityError) -> dict:
    message = "Database constraint violated"
    errors = []
    details = str(exc.orig) if exc.orig else str(exc)
    if "workflows_owner_name_fkey" in details:
        message = "Owner not found"
        errors.append({"field": "owner_name", "message": "User does not exist"})
    return {"message": message, "errors": errors}


# System
@api_router.get("/healthz", tags=["system"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


# Workflow 
@api_router.get("/workflows")
def list_workflows(
    db: Session = Depends(get_db),
    current_user: str | None = Depends(get_current_user_optional),
):
    repo = WorkflowRepository(db)
    if current_user is None:
        return []
    workflows = repo.list_all()
    workflows = [wf for wf in workflows if wf.owner_name == current_user]
    return workflows


@api_router.post("/workflows", status_code=201)
def create_workflow(
    cmd: CreateWorkflowCommand,
    db: Session = Depends(get_db),
    svc: WorkflowService = Depends(make_workflow_service),
    current_user: str | None = Depends(get_current_user_optional),
):
    try:
        if current_user is not None:
            cmd = cmd.model_copy(update={"owner_name": current_user})
        if UserRepository(db).get_by_name(cmd.owner_name) is None:
            raise HTTPException(
                422,
                detail={
                    "message": "Owner not found",
                    "errors": [
                        {"field": "owner_name", "message": "User does not exist"}
                    ],
                },
            )
        wf = svc.create_workflow(cmd)
        _guard_webhook_path_unique(db, wf, exclude_workflow_id=None)
        return WorkflowRepository(db).save(wf)

    except HTTPException:
        raise
    except (ValidationError, ValueError) as exc:
        if isinstance(exc, ValidationError):
            raise HTTPException(422, detail=_format_validation_errors(exc))
        raise HTTPException(422, detail=_format_value_error(exc))
    
    except IntegrityError as exc:
        raise HTTPException(422, detail=_format_integrity_error(exc))
    
    except Exception as exc:
        logger.exception("Unhandled error creating workflow")
        raise HTTPException(
            500, detail={"message": f"Unexpected server error: {type(exc).__name__}: {exc}"}
        )


@api_router.get("/workflows/{wf_id}")
def get_workflow(
    wf_id: UUID,
    db: Session = Depends(get_db),
    current_user: str | None = Depends(get_current_user_optional),
):
    return enforce_workflow_access(db, wf_id, current_user)


@api_router.put("/workflows/{wf_id}")
def update_workflow(
    wf_id: UUID,
    cmd: UpdateWorkflowCommand,
    db: Session = Depends(get_db),
    svc: WorkflowService = Depends(make_workflow_service),
    current_user: str | None = Depends(get_current_user_optional),
):
    existing = enforce_workflow_access(db, wf_id, current_user)
    repo = WorkflowRepository(db)

    try:
        updated = svc.update_workflow(existing, cmd)
        _guard_webhook_path_unique(db, updated, exclude_workflow_id=wf_id)
        return repo.save(updated)

    except HTTPException:
        raise
    except (ValidationError, ValueError) as exc:
        if isinstance(exc, ValidationError):
            raise HTTPException(422, detail=_format_validation_errors(exc))
        raise HTTPException(422, detail=_format_value_error(exc))
    
    except IntegrityError as exc:
        raise HTTPException(422, detail=_format_integrity_error(exc))
    
    except Exception as exc:
        logger.exception("Unhandled error updating workflow %s", wf_id)
        raise HTTPException(
            500, detail={"message": f"Unexpected server error: {type(exc).__name__}: {exc}"}
        )


@api_router.delete("/workflows/{wf_id}", status_code=204)
def delete_workflow(
    wf_id: UUID,
    db: Session = Depends(get_db),
    current_user: str | None = Depends(get_current_user_optional),
):
    # Idempotent delete: if the workflow doesn't exist OR doesn't belong to
    # the caller, silently succeed (204) — do not leak existence.
    wf = WorkflowRepository(db).get(wf_id)
    if wf is None:
        return
    if current_user is not None and wf.owner_name != current_user:
        return
    WorkflowRepository(db).delete(wf_id)


# Validation & Activation 
@api_router.post("/workflows/{wf_id}/validate")
def validate(
    wf_id: UUID,
    db: Session = Depends(get_db),
    current_user: str | None = Depends(get_current_user_optional),
):
    wf = enforce_workflow_access(db, wf_id, current_user)
    errors = validate_workflow(wf)
    return {"valid": len(errors) == 0, "errors": errors}


@api_router.post("/workflows/{wf_id}/activate")
def activate_workflow(
    wf_id: UUID,
    db: Session = Depends(get_db),
    current_user: str | None = Depends(get_current_user_optional),
):
    wf = enforce_workflow_access(db, wf_id, current_user)

    errors = validate_workflow(wf)
    if errors:
        raise HTTPException(422, detail={"message": "Workflow is invalid", "errors": errors})

    activated = wf.model_copy(update={"status": WorkflowStatus.ACTIVE, "enabled": True})
    return WorkflowRepository(db).save(activated)


# Workflow Runs
@api_router.get("/workflows/{wf_id}/runs")
def list_runs(
    wf_id: UUID,
    db: Session = Depends(get_db),
    current_user: str | None = Depends(get_current_user_optional),
):
    enforce_workflow_access(db, wf_id, current_user)
    return WorkflowRunRepository(db).list_for_workflow(wf_id)


@api_router.get("/workflows/{wf_id}/runs/{run_id}")
def get_run(
    wf_id: UUID,
    run_id: UUID,
    db: Session = Depends(get_db),
    current_user: str | None = Depends(get_current_user_optional),
):
    return enforce_run_access(db, wf_id, run_id, current_user)


@api_router.get("/workflows/{wf_id}/runs/{run_id}/steps", tags=["workflow-runs"])
def list_step_runs(
    wf_id: UUID,
    run_id: UUID,
    db: Session = Depends(get_db),
    current_user: str | None = Depends(get_current_user_optional),
):
    enforce_run_access(db, wf_id, run_id, current_user)
    return WorkflowStepRunRepository(db).list_for_run(run_id)


class CreateWorkflowRunBody(BaseModel):
    """Manual / dev trigger — creates a pending run and optionally enqueues execution."""

    trigger_type: str = Field(default="manual", description="Stored on workflow_runs.trigger_type")
    # None -> inherit the workflow's configured max_retries. Explicit 0/N
    # from the body still takes precedence so ad-hoc runs can bypass or
    # raise the budget for a single execution without editing the workflow.
    max_retries: int | None = Field(default=None, ge=0, le=10)
    enqueue: bool = Field(
        default=True,
        description="If true, dispatch Celery task execution.execute_workflow_run",
    )


@api_router.post("/workflows/{wf_id}/runs", status_code=201, tags=["workflow-runs"])
def create_workflow_run(
    wf_id: UUID,
    body: CreateWorkflowRunBody,
    db: Session = Depends(get_db),
    current_user: str | None = Depends(get_current_user_optional),
):
    """Create a workflow run row (pending) and optionally enqueue the execution engine."""
    enforce_workflow_access(db, wf_id, current_user)
    wf = WorkflowRepository(db).get(wf_id)
    # enforce_workflow_access already rejects missing workflows, but mypy
    # (and any future refactor that widens that helper) shouldn't have to
    # re-prove that invariant here.
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    effective_retries = body.max_retries if body.max_retries is not None else wf.max_retries
    run = WorkflowRun(
        workflow_id=wf_id,
        status=RunStatus.PENDING,
        trigger_type=body.trigger_type,
        max_retries=effective_retries,
    )
    created = WorkflowRunRepository(db).create(run)
    if body.enqueue:
        # Commit *before* enqueueing so the Celery worker can see this row.
        # Without this, a fast worker can pick up the task while the API's
        # transaction is still open, try_claim_running sees no PENDING row,
        # and the engine silently exits leaving status="pending" forever.
        db.commit()
        enqueue_execute_run(created.run_id)
    return {"run_id": str(created.run_id), "status": created.status.value, "enqueued": body.enqueue}

# Webhook
# Cap on body size we're willing to persist onto workflow_runs.trigger_context.
# Anything beyond this gets its ``body_text`` truncated; the parsed
# ``body`` dict is still attempted because most legitimate webhooks
# (Slack slash commands, GitHub pushes under typical limits) sit well
# below this. Keeps rogue callers from smuggling MB-scale blobs into
# the DB through the webhook ingress.
_WEBHOOK_MAX_BODY_BYTES = 64 * 1024

# Headers we never echo into workflow_runs.trigger_context — they
# either carry credentials we don't want sitting in the logs table
# or aren't useful as template inputs.
_REDACTED_HEADERS = frozenset({"authorization", "cookie", "proxy-authorization"})


# ---------------------------------------------------------------------------
# Free-form text → structured fields
# ---------------------------------------------------------------------------
#
# Slack slash commands drop the whole argument list into a single ``text``
# field (e.g. ``/block focus 30min`` → ``text="focus 30min"``). Users want
# "the event length is however long they typed", so we extract a duration
# once at ingress and surface it as ``previous_output.parsed.*``. Keeping
# the regex tiny (m/min/minute, h/hr/hour, d/day) means the grammar is
# easy to audit and we don't accidentally grow a natural-language parser.
_TEXT_DURATION_RE = re.compile(
    r"(\d+)\s*(minutes?|mins?|m|hours?|hrs?|h|days?|d)\b",
    re.IGNORECASE,
)

_UNIT_NORMALIZE = {
    "m": "m", "min": "m", "mins": "m", "minute": "m", "minutes": "m",
    "h": "h", "hr": "h", "hrs": "h", "hour": "h", "hours": "h",
    "d": "d", "day": "d", "days": "d",
}

# When the Slack ``text`` field has no duration we still want the workflow
# to produce a sensibly-scoped event so a misconfigured slash command
# doesn't silently crash the Calendar step. 30 minutes matches the
# default ``defaultCalendarAction`` shape (``start+30m``) so behaviour is
# consistent whether the user customises the end field or not.
_DEFAULT_DURATION_MINUTES = 30


def _parse_text_duration(text: str) -> dict:
    """Extract the first ``<N><unit>`` duration out of free-form text.

    Returns a dict with stable keys regardless of whether a duration was
    found, so downstream templates can reference
    ``previous_output.parsed.duration`` unconditionally:

    * ``duration``         — token form accepted by the calendar
      relative-time resolver (``"30m"``, ``"2h"``, ``"1d"``). Falls back
      to ``"30m"`` if no match, so ``start+{{previous_output.parsed.duration}}``
      always resolves to a valid end time in the demo.
    * ``duration_minutes`` — integer minutes for human-readable templates
      (emails, logs). Falls back to ``30``.
    * ``subject``          — original text with the duration fragment
      stripped and whitespace collapsed. Empty if the original was empty.
    * ``has_duration``     — whether a match was found. Useful for
      builder hints / tests that want to tell "defaulted" apart from
      "explicitly 30m".
    """
    base = text or ""
    match = _TEXT_DURATION_RE.search(base)
    if match is None:
        return {
            "duration": f"{_DEFAULT_DURATION_MINUTES}m",
            "duration_minutes": _DEFAULT_DURATION_MINUTES,
            "subject": base.strip(),
            "has_duration": False,
        }

    amount = int(match.group(1))
    unit = _UNIT_NORMALIZE[match.group(2).lower()]
    minutes_per_unit = {"m": 1, "h": 60, "d": 60 * 24}[unit]
    stripped = (base[: match.start()] + base[match.end():]).strip()
    stripped = re.sub(r"\s+", " ", stripped)
    return {
        "duration": f"{amount}{unit}",
        "duration_minutes": amount * minutes_per_unit,
        "subject": stripped,
        "has_duration": True,
    }


def _parse_webhook_body(raw_body: bytes, content_type: str) -> dict | list | str | None:
    """Best-effort parse of the webhook payload into a template-friendly shape.

    - application/json          → parsed JSON
    - application/x-www-form-urlencoded → flat dict (single values unwrapped)
    - anything else             → return None; callers rely on body_text instead

    A decode failure returns None rather than raising so that a
    mis-declared Content-Type doesn't take down the whole ingress.
    """
    if not raw_body:
        return None

    ct = content_type.lower()
    if "application/json" in ct:
        try:
            return json.loads(raw_body.decode("utf-8", errors="replace"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    if "application/x-www-form-urlencoded" in ct:
        try:
            decoded = raw_body.decode("utf-8", errors="replace")
        except UnicodeDecodeError:
            return None
        pairs = parse_qs(decoded, keep_blank_values=True)
        # Slack slash commands only ever have scalar values, but
        # generic form posts can have repeated keys (e.g. checkbox[]).
        # Keep lists where they appear so no data is silently dropped.
        return {k: (v[0] if len(v) == 1 else v) for k, v in pairs.items()}

    return None


def _build_trigger_context(
    *,
    normalized_path: str,
    method: str,
    headers: dict[str, str],
    query: dict[str, str],
    raw_body: bytes,
    content_type: str,
) -> dict:
    """Assemble the dict stashed on workflow_runs.trigger_context.

    The engine seeds the first step's ``previous_output`` with this,
    so template keys like {{previous_output.body.text}} and
    {{previous_output.headers.x-github-event}} resolve from here.
    """
    parsed_body = _parse_webhook_body(raw_body, content_type)
    body_text = raw_body[:_WEBHOOK_MAX_BODY_BYTES].decode("utf-8", errors="replace")

    # Only derive ``parsed`` when the payload exposes a ``text`` field
    # (Slack slash commands, and anything that adopts the same shape).
    # For arbitrary JSON webhooks the keys here would be meaningless, so
    # we omit them rather than ship misleading defaults.
    parsed: dict = {}
    if isinstance(parsed_body, dict) and isinstance(parsed_body.get("text"), str):
        parsed = _parse_text_duration(parsed_body["text"])

    return {
        "source": "webhook",
        "path": normalized_path,
        "method": method,
        "content_type": content_type,
        "headers": {k: v for k, v in headers.items() if k not in _REDACTED_HEADERS},
        "query": query,
        "body": parsed_body if parsed_body is not None else {},
        "body_text": body_text,
        "parsed": parsed,
    }


def _passes_event_filter(cfg: WebhookTriggerConfig, headers: dict[str, str]) -> bool:
    """``event_filter`` is matched against X-Event-Type. Empty means accept any."""
    wanted = (cfg.event_filter or "").strip()
    if not wanted:
        return True
    return headers.get("x-event-type", "") == wanted


def _passes_header_filters(cfg: WebhookTriggerConfig, headers: dict[str, str]) -> bool:
    """All configured header key/value pairs must match (case-insensitive key)."""
    for key, expected in (cfg.header_filters or {}).items():
        if headers.get(key.lower(), "") != expected:
            return False
    return True


def _slack_request(headers: dict[str, str]) -> bool:
    """Heuristic: Slack tags every outbound request with x-slack-signature."""
    return "x-slack-signature" in headers


@api_router.api_route(
    "/hooks/{hook_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    tags=["triggers"],
)
async def ingest_webhook(
    hook_path: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Webhook ingress.

    Per request:
    1. read body (bounded) + normalise headers / query
    2. find enabled workflows with a matching (path, method) trigger
    3. for each match, verify secret_ref and apply event/header filters
    4. emit one run per surviving workflow, seeding its trigger_context
       with the captured payload so step 1 templates can use it
    5. respond with a caller-friendly shape (Slack gets an ephemeral
       reply; everyone else gets a JSON summary)
    """
    normalized_path = "/hooks/" + hook_path.lstrip("/")
    method = request.method.upper()

    # Read once — FastAPI caches the body on the request object, but
    # we still want the exact bytes for HMAC verification.
    raw_body = await request.body()
    if len(raw_body) > _WEBHOOK_MAX_BODY_BYTES:
        # Truncate for storage but keep full bytes for signature
        # verification, otherwise a padded request would fail HMAC.
        stored_body = raw_body[:_WEBHOOK_MAX_BODY_BYTES]
    else:
        stored_body = raw_body

    headers = {k.lower(): v for k, v in request.headers.items()}
    query = dict(request.query_params)
    content_type = headers.get("content-type", "")

    trigger_context = _build_trigger_context(
        normalized_path=normalized_path,
        method=method,
        headers=headers,
        query=query,
        raw_body=stored_body,
        content_type=content_type,
    )

    wf_repo = WorkflowRepository(db)
    matched = wf_repo.list_enabled_for_webhook(normalized_path, method)

    trigger_service = TriggerService(run_repo=WorkflowRunRepository(db))
    emitted = 0
    skipped_auth = 0
    skipped_filter = 0

    for wf in matched:
        cfg = wf.trigger
        if not isinstance(cfg, WebhookTriggerConfig):
            continue

        auth = verify_webhook_auth(
            secret_ref=cfg.secret_ref,
            raw_body=raw_body,
            headers=headers,
        )
        if not auth.ok:
            logger.info(
                "webhook auth rejected workflow=%s path=%s reason=%s",
                wf.workflow_id,
                normalized_path,
                auth.reason,
            )
            skipped_auth += 1
            continue

        if not _passes_event_filter(cfg, headers):
            skipped_filter += 1
            continue
        if not _passes_header_filters(cfg, headers):
            skipped_filter += 1
            continue

        trigger_service.emit_workflow_event(
            workflow_id=wf.workflow_id,
            trigger_type="webhook",
            enqueue=True,
            max_retries=wf.max_retries,
            trigger_context=trigger_context,
        )
        emitted += 1

    # Every match rejected solely on auth → surface that clearly so
    # misconfigured Slack / HMAC secrets are noisy instead of silent.
    if matched and emitted == 0 and skipped_auth > 0 and skipped_filter == 0:
        raise HTTPException(status_code=401, detail="webhook signature verification failed")

    if _slack_request(headers):
        # Slack slash commands display the response body to the user
        # if ``response_type`` is set. Using ``ephemeral`` means only
        # the caller sees it — the channel stays clean.
        if emitted > 0:
            text = f"FlowPilot: started {emitted} workflow(s) ✓"
        elif skipped_filter > 0:
            text = (
                "FlowPilot: request received but no matching workflow accepted it "
                "(check event/header filters)."
            )
        else:
            text = "FlowPilot: no workflow is listening on this path/method."
        return JSONResponse({"response_type": "ephemeral", "text": text})

    return {
        "path": normalized_path,
        "method": method,
        "matched_workflows": len(matched),
        "emitted_runs": emitted,
        "skipped_auth": skipped_auth,
        "skipped_filter": skipped_filter,
    }


# Registry
@api_router.get("/registry/actions")
def list_actions():
    return ActionRegistry.list_schemas()


@api_router.get("/registry/triggers")
def list_triggers():
    return TriggerRegistry.list_schemas()


class CustomTriggerDryRunBody(BaseModel):
    """Input for POST /triggers/custom/evaluate (builder live preview)."""

    condition: str = Field(..., max_length=500)
    source: str = Field(default="event_payload", max_length=100)
    timezone: str = Field(default="UTC", max_length=100)


@api_router.post("/triggers/custom/evaluate", tags=["triggers"])
def evaluate_custom_trigger(body: CustomTriggerDryRunBody):
    """Evaluate a custom-trigger condition **right now** and return the verdict.

    Used by the workflow builder to show a live "would this fire?" preview
    and to surface syntax / whitelist errors inline instead of the user
    having to save the workflow and watch the dispatch loop silently
    refuse to fire. The dispatch loop itself swallows evaluation errors
    (by design); this endpoint is the escape hatch that exposes them.
    """
    report = dry_run_condition(body.condition, body.source, body.timezone)
    return {
        **report,
        # Attach the catalogue so the builder can re-render the hint
        # block without a second request. Cheap (9 entries) and keeps
        # the list canonical on the backend.
        "available_variables": [
            {"name": n, "description": d} for n, d in AVAILABLE_VARIABLES
        ],
    }


# Reports
class GenerateReportBody(BaseModel):
    owner_name: str
    period_start: datetime
    period_end: datetime


@api_router.get("/reports", tags=["reports"])
def list_reports(
    owner_name: str,
    db: Session = Depends(get_db),
    current_user: str | None = Depends(get_current_user_optional),
):
    enforce_owner_match(owner_name, current_user)
    if UserRepository(db).get_by_name(owner_name) is None:
        raise HTTPException(404, detail="Owner not found")
    return ReportRepository(db).list_for_owner(owner_name)


@api_router.get("/reports/{report_id}", tags=["reports"])
def get_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: str | None = Depends(get_current_user_optional),
):
    report = ReportRepository(db).get(report_id)
    if report is None:
        raise HTTPException(404, detail="Report not found")
    if current_user is not None and report.owner_name != current_user:
        raise HTTPException(404, detail="Report not found")
    return report


@api_router.delete("/reports/{report_id}", status_code=204, tags=["reports"])
def delete_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: str | None = Depends(get_current_user_optional),
):
    repo = ReportRepository(db)
    report = repo.get(report_id)
    if report is None:
        raise HTTPException(404, detail="Report not found")
    if current_user is not None and report.owner_name != current_user:
        raise HTTPException(404, detail="Report not found")
    repo.delete(report_id)
    db.commit()
    return None


@api_router.post("/reports/generate", status_code=201, tags=["reports"])
def generate_report(
    body: GenerateReportBody,
    db: Session = Depends(get_db),
    current_user: str | None = Depends(get_current_user_optional),
):
    """Synchronous manual trigger for the reporting pipeline.

    Runs the pipeline in-process (no Celery) for dev/testing. The async,
    beat-driven path enqueues reporting.generate_monthly_report via Celery.
    """
    enforce_owner_match(body.owner_name, current_user)
    if UserRepository(db).get_by_name(body.owner_name) is None:
        raise HTTPException(404, detail="Owner not found")
    if body.period_end <= body.period_start:
        raise HTTPException(
            422,
            detail={"message": "period_end must be after period_start"},
        )
    service = make_reporting_service(db)
    report = service.generate_monthly_report(
        owner_name=body.owner_name,
        period_start=body.period_start,
        period_end=body.period_end,
    )
    return report


# AI Suggestions
class CreateSuggestionBody(BaseModel):
    raw_text: str = Field(min_length=1)
    user_name: str | None = None


def _serialize_suggestion(orm) -> dict:
    return {
        "id": str(orm.id),
        "user_name": orm.user_name,
        "raw_text": orm.raw_text,
        "strategy_used": orm.strategy_used,
        "analysis": orm.analysis,
        "content": orm.content,
        "workflow_draft": orm.workflow_draft,
        "created_at": orm.created_at.isoformat() if orm.created_at else None,
        "accepted_workflow_id": (
            str(orm.accepted_workflow_id) if orm.accepted_workflow_id else None
        ),
    }


@api_router.post("/suggestions", status_code=201, tags=["suggestions"])
async def create_suggestion(
    body: CreateSuggestionBody,
    db: Session = Depends(get_db),
    current_user: str | None = Depends(get_current_user_optional),
):
    effective_user = current_user if current_user is not None else body.user_name
    if current_user is not None and body.user_name and body.user_name != current_user:
        raise HTTPException(403, detail="Cannot create suggestion for another user")
    service = SuggestionService(db)
    user_input = UserInput(raw_text=body.raw_text, user_name=effective_user)
    try:
        orm = await service.suggest(user_input)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, detail={"message": f"Suggestion failed: {exc!s}"})
    return _serialize_suggestion(orm)


@api_router.get("/suggestions", tags=["suggestions"])
def list_suggestions(
    user_name: str,
    db: Session = Depends(get_db),
    current_user: str | None = Depends(get_current_user_optional),
):
    enforce_owner_match(user_name, current_user)
    repo = SuggestionRepository(db)
    return [_serialize_suggestion(s) for s in repo.list_for_user(user_name)]


@api_router.get("/suggestions/{suggestion_id}", tags=["suggestions"])
def get_suggestion(
    suggestion_id: UUID,
    db: Session = Depends(get_db),
    current_user: str | None = Depends(get_current_user_optional),
):
    repo = SuggestionRepository(db)
    orm = repo.get(suggestion_id)
    if orm is None:
        raise HTTPException(404, detail="Suggestion not found")
    if current_user is not None and orm.user_name and orm.user_name != current_user:
        raise HTTPException(404, detail="Suggestion not found")
    return _serialize_suggestion(orm)


@api_router.post("/suggestions/{suggestion_id}/accept", tags=["suggestions"])
def accept_suggestion(
    suggestion_id: UUID,
    db: Session = Depends(get_db),
    current_user: str | None = Depends(get_current_user_optional),
):
    repo = SuggestionRepository(db)
    orm = repo.get(suggestion_id)
    if orm is None:
        raise HTTPException(404, detail="Suggestion not found")
    if current_user is not None and orm.user_name and orm.user_name != current_user:
        raise HTTPException(404, detail="Suggestion not found")
    if not orm.workflow_draft:
        raise HTTPException(422, detail="Suggestion has no workflow draft to accept")
    return {
        "suggestion_id": str(orm.id),
        "workflow_draft": orm.workflow_draft,
        "hint": (
            "POST the draft to /api/workflows to create it, then call "
            "/suggestions/{id}/accept/link to record the accepted workflow id."
        ),
    }
