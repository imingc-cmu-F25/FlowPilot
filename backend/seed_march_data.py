"""
Seed script: inject March 2026 workflow + execution data for report testing.

Run from the backend directory (local):
    uv run python seed_march_data.py

Run inside Docker (backend container):
    python seed_march_data.py
    # The script auto-detects the Docker postgres hostname via POSTGRES_HOST.

Optional explicit override:
    DATABASE_URL=postgresql+psycopg://flowpilot:flowpilot@postgres:5432/flowpilot \
        python seed_march_data.py
"""

import os
import random
import uuid
from datetime import UTC, datetime, timedelta

import app.db.schema  # noqa: F401 — registers all ORM classes
from app.db.schema.user import UserORM
from app.db.schema.workflow import WorkflowORM
from app.db.schema.workflow_run import WorkflowRunORM
from app.db.schema.workflow_step import WorkflowStepORM
from app.db.schema.workflow_step_run import WorkflowStepRunORM
from app.db.schema.workflow_trigger import WorkflowTriggerORM
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# DB connection — honours app env vars so it works both locally and in Docker
# ---------------------------------------------------------------------------
_host = os.environ.get("POSTGRES_HOST", "localhost")
_port = os.environ.get("POSTGRES_PORT", "5432")
_db   = os.environ.get("POSTGRES_DB", "flowpilot")
_user = os.environ.get("POSTGRES_USER", "flowpilot")
_pass = os.environ.get("POSTGRES_PASSWORD", "flowpilot")
_default_url = f"postgresql+psycopg://{_user}:{_pass}@{_host}:{_port}/{_db}"

DATABASE_URL = os.environ.get("DATABASE_URL", _default_url)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
MARCH_START = datetime(2026, 3, 1, tzinfo=UTC)
MARCH_END = datetime(2026, 3, 30, 23, 59, 59, tzinfo=UTC)
SEED_USER = "natalie"


def rand_march_dt(hour_min: int = 0, hour_max: int = 23) -> datetime:
    day = random.randint(1, 30)
    hour = random.randint(hour_min, hour_max)
    minute = random.randint(0, 59)
    return datetime(2026, 3, day, hour, minute, tzinfo=UTC)


def step_duration() -> timedelta:
    return timedelta(seconds=random.randint(1, 120))


# ---------------------------------------------------------------------------
# Workflow definitions (variety of types for a realistic report)
# ---------------------------------------------------------------------------
WORKFLOWS = [
    {
        "name": "Daily Slack Digest",
        "description": "Fetch top tickets and post a daily Slack digest.",
        "status": "active",
        "enabled": True,
        "trigger_type": "time",
        "trigger_config": {
            "type": "time",
            "trigger_at": "2026-03-01T09:00:00+00:00",
            "timezone": "UTC",
            "recurrence": {"frequency": "daily", "interval": 1},
        },
        "steps": [
            {
                "action_type": "http_request",
                "name": "Fetch open tickets",
                "step_order": 1,
                "config": {
                    "action_type": "http_request",
                    "step_order": 1,
                    "name": "Fetch open tickets",
                    "url_template": "https://api.example.com/tickets?status=open",
                    "method": "GET",
                    "headers": {"Authorization": "Bearer {{env.TICKETS_TOKEN}}"},
                },
            },
            {
                "action_type": "send_email",
                "name": "Email digest",
                "step_order": 2,
                "config": {
                    "action_type": "send_email",
                    "step_order": 2,
                    "name": "Email digest",
                    "to_template": "team@example.com",
                    "subject_template": "Daily Digest - {{trigger.date}}",
                    "body_template": "Open tickets:\n{{steps.0.output.tickets}}",
                },
            },
        ],
        "run_pattern": [("success", 25), ("failed", 3)],
    },
    {
        "name": "Invoice PDF Generator",
        "description": "Generates and emails PDF invoices on webhook trigger.",
        "status": "active",
        "enabled": True,
        "trigger_type": "webhook",
        "trigger_config": {
            "type": "webhook",
            "path": "/hooks/invoice",
            "method": "POST",
            "secret_ref": "INVOICE_WEBHOOK_SECRET",
            "event_filter": "",
            "header_filters": {},
        },
        "steps": [
            {
                "action_type": "http_request",
                "name": "Generate PDF",
                "step_order": 1,
                "config": {
                    "action_type": "http_request",
                    "step_order": 1,
                    "name": "Generate PDF",
                    "url_template": "https://pdf.example.com/generate",
                    "method": "POST",
                    "headers": {"Content-Type": "application/json"},
                },
            },
            {
                "action_type": "send_email",
                "name": "Send invoice email",
                "step_order": 2,
                "config": {
                    "action_type": "send_email",
                    "step_order": 2,
                    "name": "Send invoice email",
                    "to_template": "{{trigger.body.customer_email}}",
                    "subject_template": "Your Invoice #{{trigger.body.invoice_id}}",
                    "body_template": "Please find your invoice attached.",
                },
            },
        ],
        "run_pattern": [("success", 18), ("failed", 5)],
    },
    {
        "name": "Weekly Report Aggregator",
        "description": "Aggregates metrics every Monday and creates a calendar event.",
        "status": "active",
        "enabled": True,
        "trigger_type": "time",
        "trigger_config": {
            "type": "time",
            "trigger_at": "2026-03-02T08:00:00+00:00",
            "timezone": "UTC",
            "recurrence": {"frequency": "weekly", "interval": 1},
        },
        "steps": [
            {
                "action_type": "http_request",
                "name": "Pull weekly metrics",
                "step_order": 1,
                "config": {
                    "action_type": "http_request",
                    "step_order": 1,
                    "name": "Pull weekly metrics",
                    "url_template": "https://analytics.example.com/weekly",
                    "method": "GET",
                    "headers": {},
                },
            },
            {
                "action_type": "calendar_create_event",
                "name": "Schedule review meeting",
                "step_order": 2,
                "config": {
                    "action_type": "calendar_create_event",
                    "step_order": 2,
                    "name": "Schedule review meeting",
                    "calendar_id": "primary",
                    "title_template": "Weekly Review - {{trigger.date}}",
                    "start_mapping": "$.trigger.date",
                    "end_mapping": "$.trigger.date",
                },
            },
        ],
        "run_pattern": [("success", 4), ("failed", 0)],
    },
    {
        "name": "Customer Onboarding Notifier",
        "description": "Sends a welcome email when a new customer registers.",
        "status": "active",
        "enabled": True,
        "trigger_type": "webhook",
        "trigger_config": {
            "type": "webhook",
            "path": "/hooks/customer/signup",
            "method": "POST",
            "secret_ref": "SIGNUP_SECRET",
            "event_filter": "customer.created",
            "header_filters": {},
        },
        "steps": [
            {
                "action_type": "send_email",
                "name": "Welcome email",
                "step_order": 1,
                "config": {
                    "action_type": "send_email",
                    "step_order": 1,
                    "name": "Welcome email",
                    "to_template": "{{trigger.body.email}}",
                    "subject_template": "Welcome to FlowPilot, {{trigger.body.name}}!",
                    "body_template": "Hi {{trigger.body.name}},\n\nWelcome aboard!",
                },
            },
        ],
        "run_pattern": [("success", 31), ("failed", 2)],
    },
    {
        "name": "Nightly DB Backup Alert",
        "description": "Verifies nightly backup completed and alerts on failure.",
        "status": "active",
        "enabled": True,
        "trigger_type": "time",
        "trigger_config": {
            "type": "time",
            "trigger_at": "2026-03-01T02:00:00+00:00",
            "timezone": "UTC",
            "recurrence": {"frequency": "daily", "interval": 1},
        },
        "steps": [
            {
                "action_type": "http_request",
                "name": "Check backup status",
                "step_order": 1,
                "config": {
                    "action_type": "http_request",
                    "step_order": 1,
                    "name": "Check backup status",
                    "url_template": "https://backup.example.com/status/latest",
                    "method": "GET",
                    "headers": {"X-Api-Key": "{{env.BACKUP_API_KEY}}"},
                },
            },
            {
                "action_type": "send_email",
                "name": "Alert on failure",
                "step_order": 2,
                "config": {
                    "action_type": "send_email",
                    "step_order": 2,
                    "name": "Alert on failure",
                    "to_template": "ops@example.com",
                    "subject_template": "Backup Status: {{steps.0.output.status}}",
                    "body_template": "Backup result: {{steps.0.output.message}}",
                },
            },
        ],
        "run_pattern": [("success", 27), ("failed", 1)],
    },
    {
        "name": "Abandoned Draft Cleaner",
        "description": "Deletes draft workflows older than 90 days via HTTP.",
        "status": "paused",
        "enabled": False,
        "trigger_type": "time",
        "trigger_config": {
            "type": "time",
            "trigger_at": "2026-03-01T03:30:00+00:00",
            "timezone": "UTC",
            "recurrence": {"frequency": "weekly", "interval": 2},
        },
        "steps": [
            {
                "action_type": "http_request",
                "name": "Delete old drafts",
                "step_order": 1,
                "config": {
                    "action_type": "http_request",
                    "step_order": 1,
                    "name": "Delete old drafts",
                    "url_template": "https://api.example.com/workflows/drafts/cleanup",
                    "method": "DELETE",
                    "headers": {},
                },
            },
        ],
        "run_pattern": [("success", 2), ("failed", 1)],
    },
    {
        "name": "Lead Enrichment Pipeline",
        "description": "Enriches new leads with firmographic data from an external API.",
        "status": "active",
        "enabled": True,
        "trigger_type": "webhook",
        "trigger_config": {
            "type": "webhook",
            "path": "/hooks/leads/new",
            "method": "POST",
            "secret_ref": "LEADS_WEBHOOK_SECRET",
            "event_filter": "lead.created",
            "header_filters": {"X-Source": "crm"},
        },
        "steps": [
            {
                "action_type": "http_request",
                "name": "Enrich lead",
                "step_order": 1,
                "config": {
                    "action_type": "http_request",
                    "step_order": 1,
                    "name": "Enrich lead",
                    "url_template": "https://enrich.example.com/company?domain={{trigger.body.domain}}",
                    "method": "GET",
                    "headers": {},
                },
            },
            {
                "action_type": "http_request",
                "name": "Update CRM record",
                "step_order": 2,
                "config": {
                    "action_type": "http_request",
                    "step_order": 2,
                    "name": "Update CRM record",
                    "url_template": "https://crm.example.com/leads/{{trigger.body.lead_id}}",
                    "method": "PATCH",
                    "headers": {"Content-Type": "application/json"},
                },
            },
        ],
        "run_pattern": [("success", 40), ("failed", 6)],
    },
    {
        "name": "SLA Breach Monitor",
        "description": "Checks for SLA breaches every 4 hours and pages on-call.",
        "status": "active",
        "enabled": True,
        "trigger_type": "time",
        "trigger_config": {
            "type": "time",
            "trigger_at": "2026-03-01T00:00:00+00:00",
            "timezone": "UTC",
            "recurrence": {"frequency": "hourly", "interval": 4},
        },
        "steps": [
            {
                "action_type": "http_request",
                "name": "Query SLA status",
                "step_order": 1,
                "config": {
                    "action_type": "http_request",
                    "step_order": 1,
                    "name": "Query SLA status",
                    "url_template": "https://monitoring.example.com/sla/breaches",
                    "method": "GET",
                    "headers": {},
                },
            },
            {
                "action_type": "send_email",
                "name": "Page on-call",
                "step_order": 2,
                "config": {
                    "action_type": "send_email",
                    "step_order": 2,
                    "name": "Page on-call",
                    "to_template": "oncall@example.com",
                    "subject_template": "SLA BREACH DETECTED - {{trigger.timestamp}}",
                    "body_template": "Breached tickets: {{steps.0.output.breaches}}",
                },
            },
        ],
        "run_pattern": [("success", 170), ("failed", 10)],
    },
]

# Step-level error messages for failed step runs
STEP_ERRORS = [
    "ConnectionError: upstream service timed out after 30s",
    "HTTP 503: Service Unavailable",
    "HTTP 401: Unauthorized — check API key",
    "JSONDecodeError: unexpected token at position 0",
    "SMTP error 550: Recipient address rejected",
    "HTTP 429: Too Many Requests — rate limit exceeded",
]

STEP_OUTPUTS = [
    {"status": "ok", "count": 42},
    {"status": "success", "message": "Processed 17 records"},
    {"pdf_url": "https://cdn.example.com/invoices/inv_2026_03.pdf"},
    {"event_id": "gcal_evt_abc123"},
    {"tickets": ["T-001", "T-002", "T-003"]},
    {"breaches": [], "checked_at": "2026-03-15T10:00:00Z"},
]


# ---------------------------------------------------------------------------
# Main seeding logic
# ---------------------------------------------------------------------------

def ensure_user(session) -> str:
    existing = session.get(UserORM, SEED_USER)
    if existing:
        print(f"  User '{SEED_USER}' already exists, reusing.")
        return SEED_USER
    user = UserORM(
        name=SEED_USER,
        # bcrypt hash of "password123" — placeholder, not used for login
        password_hash="$2b$12$KIX.placeholder.hash.for.seed.data.only",
        emails=["seed@example.com"],
    )
    session.add(user)
    print(f"  Created user: {SEED_USER}")
    return SEED_USER


def seed_workflow(session, wf_def: dict, owner: str) -> uuid.UUID:
    wf_id = uuid.uuid4()
    now = MARCH_START

    wf = WorkflowORM(
        id=wf_id,
        owner_name=owner,
        name=wf_def["name"],
        description=wf_def["description"],
        status=wf_def["status"],
        enabled=wf_def["enabled"],
        created_at=now,
        updated_at=now,
    )
    session.add(wf)

    trigger = WorkflowTriggerORM(
        trigger_id=uuid.uuid4(),
        workflow_id=wf_id,
        type=wf_def["trigger_type"],
        config=wf_def["trigger_config"],
    )
    session.add(trigger)

    for step_def in wf_def["steps"]:
        step = WorkflowStepORM(
            step_id=uuid.uuid4(),
            workflow_id=wf_id,
            action_type=step_def["action_type"],
            name=step_def["name"],
            step_order=step_def["step_order"],
            config=step_def["config"],
        )
        session.add(step)

    print(f"  Workflow '{wf_def['name']}' ({wf_id})")
    return wf_id


def seed_runs(session, wf_id: uuid.UUID, wf_def: dict):
    trigger_type = wf_def["trigger_type"]
    steps = wf_def["steps"]
    total_runs = 0

    for run_status, count in wf_def["run_pattern"]:
        for _ in range(count):
            triggered_at = rand_march_dt()
            started_at = triggered_at + timedelta(seconds=random.randint(0, 5))
            duration = timedelta(seconds=random.randint(2, 180))
            finished_at = started_at + duration

            run_id = uuid.uuid4()
            run = WorkflowRunORM(
                id=run_id,
                workflow_id=wf_id,
                status=run_status,
                trigger_type=trigger_type,
                triggered_at=triggered_at,
                started_at=started_at,
                finished_at=finished_at,
                error=random.choice(STEP_ERRORS) if run_status == "failed" else None,
                output=random.choice(STEP_OUTPUTS) if run_status == "success" else None,
                retry_count=random.randint(0, 2) if run_status == "failed" else 0,
                max_retries=3,
            )
            session.add(run)

            # Step runs
            for step_def in steps:
                # Last step may fail for a failed run
                is_last_step = step_def["step_order"] == len(steps)
                if run_status == "failed" and is_last_step:
                    step_status = "failed"
                    step_error = random.choice(STEP_ERRORS)
                    step_output = None
                else:
                    step_status = "success"
                    step_error = None
                    step_output = random.choice(STEP_OUTPUTS)

                step_started = started_at + timedelta(
                    seconds=(step_def["step_order"] - 1) * 30
                )
                step_finished = step_started + step_duration()

                step_run = WorkflowStepRunORM(
                    id=uuid.uuid4(),
                    run_id=run_id,
                    step_order=step_def["step_order"],
                    step_name=step_def["name"],
                    action_type=step_def["action_type"],
                    status=step_status,
                    started_at=step_started,
                    finished_at=step_finished,
                    inputs={"resolved": True, "step": step_def["step_order"]},
                    output=step_output,
                    error=step_error,
                )
                session.add(step_run)

            total_runs += 1

    return total_runs


def cleanup_previous_seed(session) -> None:
    """Delete workflows previously inserted by this seed script (by owner)."""
    wf_ids = session.execute(
        select(WorkflowORM.id).where(WorkflowORM.owner_name == SEED_USER)
    ).scalars().all()
    if not wf_ids:
        return
    # CASCADE deletes triggers, steps, runs, and step_runs automatically
    session.execute(delete(WorkflowORM).where(WorkflowORM.owner_name == SEED_USER))
    print(f"  Removed {len(wf_ids)} previously seeded workflow(s).")


def main():
    random.seed(42)  # reproducible

    print("=== FlowPilot March 2026 Data Seed ===\n")
    with Session() as session:
        print("[0/3] Cleaning up any previous seed data...")
        cleanup_previous_seed(session)
        session.flush()

        print("\n[1/3] Ensuring test user...")
        owner = ensure_user(session)
        session.flush()

        print("\n[2/3] Creating workflows...")
        wf_ids = []
        for wf_def in WORKFLOWS:
            wf_id = seed_workflow(session, wf_def, owner)
            wf_ids.append((wf_id, wf_def))
        session.flush()

        print("\n[3/3] Seeding workflow runs & step runs (March 1–30, 2026)...")
        total_runs = 0
        for wf_id, wf_def in wf_ids:
            n = seed_runs(session, wf_id, wf_def)
            total_runs += n
            success_count = sum(c for s, c in wf_def["run_pattern"] if s == "success")
            fail_count = sum(c for s, c in wf_def["run_pattern"] if s == "failed")
            print(
                f"    '{wf_def['name']}': {n} runs "
                f"({success_count} success, {fail_count} failed)"
            )

        session.commit()

    print(f"\nDone. Seeded {len(WORKFLOWS)} workflows and {total_runs} runs.")
    print(f"Owner: '{SEED_USER}' | Period: 2026-03-01 → 2026-03-30")


if __name__ == "__main__":
    main()
