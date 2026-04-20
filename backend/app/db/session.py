from collections.abc import Generator

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session, sessionmaker

import app.db.schema  # noqa: F401  — registers all ORM classes with Base.metadata
from app.db.base import Base
from app.db.connector import get_engine

SessionFactory = sessionmaker(autoflush=False, autocommit=False, expire_on_commit=False)


def new_session() -> Session:
    """Return a fresh SQLAlchemy Session bound to the configured engine.

    Celery tasks (and anything else running outside a FastAPI request) should
    prefer this helper over calling SessionFactory directly — it's the single
    place that decides how sessions get created, and it also prevents the
    recurrent `SessionFactory(bind=engine)()` typo where an extra pair of
    parentheses silently turned into a runtime TypeError.
    """
    return SessionFactory(bind=get_engine())


def _ensure_users_emails_column() -> None:
    engine = get_engine()
    insp = inspect(engine)
    if not insp.has_table("users"):
        return
    cols = {c["name"] for c in insp.get_columns("users")}
    if "emails" in cols:
        return
    ddl = "ALTER TABLE users ADD COLUMN emails JSON"
    if engine.dialect.name == "sqlite":
        ddl = "ALTER TABLE users ADD COLUMN emails TEXT"
    with engine.begin() as conn:
        conn.execute(text(ddl))


def _migrate_workflow_owner_column() -> None:
    """
    One-time migration: replace workflows.owner_id (UUID) with owner_name
    (String). Existing rows get owner_name = 'unknown' because the old UUID
    value cannot be mapped to a username. The FK constraint is added only on
    fresh tables via the ORM; here we use a plain NOT NULL string column to
    avoid FK violations on stale data.
    """
    engine = get_engine()
    insp = inspect(engine)
    if not insp.has_table("workflows"):
        return
    cols = {c["name"] for c in insp.get_columns("workflows")}
    if "owner_name" in cols:
        return  # already migrated
    if "owner_id" not in cols:
        return  # fresh schema — create_all handles it
    with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            # Add plain string column (no FK — old rows have UUID owner_ids)
            conn.execute(text(
                "ALTER TABLE workflows ADD COLUMN owner_name VARCHAR(255)"
            ))
            conn.execute(text("UPDATE workflows SET owner_name = 'unknown'"))
            conn.execute(text(
                "ALTER TABLE workflows ALTER COLUMN owner_name SET NOT NULL"
            ))
            conn.execute(text("ALTER TABLE workflows DROP COLUMN owner_id"))
        elif engine.dialect.name == "sqlite":
            conn.execute(
                text(
                    "ALTER TABLE workflows ADD COLUMN owner_name TEXT "
                    "NOT NULL DEFAULT 'unknown'"
                )
            )
            # SQLite can't drop columns before 3.35; owner_id becomes dead weight


def _ensure_workflow_runs_retry_columns() -> None:
    """Add retry_count / max_retries to workflow_runs if missing (additive migration)."""
    engine = get_engine()
    insp = inspect(engine)
    if not insp.has_table("workflow_runs"):
        return
    cols = {c["name"] for c in insp.get_columns("workflow_runs")}
    if "retry_count" in cols and "max_retries" in cols:
        return
    with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            if "retry_count" not in cols:
                conn.execute(
                    text(
                        "ALTER TABLE workflow_runs ADD COLUMN retry_count "
                        "INTEGER NOT NULL DEFAULT 0"
                    )
                )
            if "max_retries" not in cols:
                conn.execute(
                    text(
                        "ALTER TABLE workflow_runs ADD COLUMN max_retries "
                        "INTEGER NOT NULL DEFAULT 0"
                    )
                )
        elif engine.dialect.name == "sqlite":
            if "retry_count" not in cols:
                conn.execute(
                    text(
                        "ALTER TABLE workflow_runs ADD COLUMN retry_count "
                        "INTEGER NOT NULL DEFAULT 0"
                    )
                )
            if "max_retries" not in cols:
                conn.execute(
                    text(
                        "ALTER TABLE workflow_runs ADD COLUMN max_retries "
                        "INTEGER NOT NULL DEFAULT 0"
                    )
                )


def _ensure_workflow_runs_trigger_context_column() -> None:
    """Add workflow_runs.trigger_context (nullable JSON) if missing.

    The webhook ingest path stashes the incoming body / headers / query
    here so the execution engine can seed the first step's
    ``previous_output`` with it. Older rows pre-date the column and
    stay NULL, which simply means "no captured payload" — backwards
    compatible with every non-webhook trigger.
    """
    engine = get_engine()
    insp = inspect(engine)
    if not insp.has_table("workflow_runs"):
        return
    cols = {c["name"] for c in insp.get_columns("workflow_runs")}
    if "trigger_context" in cols:
        return
    # JSON is spelled identically by both dialects we support; pg stores
    # it as JSONB via SQLAlchemy's JSON type, sqlite stores it as TEXT.
    ddl = "ALTER TABLE workflow_runs ADD COLUMN trigger_context JSON"
    with engine.begin() as conn:
        conn.execute(text(ddl))


def _ensure_user_sessions_pkce_column() -> None:
    """Add user_sessions.oauth_code_verifier (nullable) if missing.

    Needed so the Google Calendar OAuth flow can persist the PKCE
    code_verifier between the /authorize and /callback requests.
    """
    engine = get_engine()
    insp = inspect(engine)
    if not insp.has_table("user_sessions"):
        return
    cols = {c["name"] for c in insp.get_columns("user_sessions")}
    if "oauth_code_verifier" in cols:
        return
    ddl = "ALTER TABLE user_sessions ADD COLUMN oauth_code_verifier VARCHAR(256)"
    with engine.begin() as conn:
        conn.execute(text(ddl))


def _ensure_workflows_max_retries_column() -> None:
    """Add workflows.max_retries (default 0) if missing.

    Keeps the per-workflow retry policy backwards-compatible: existing rows
    get max_retries=0 — i.e. the same "fail on first error" behaviour they
    had before the column existed.
    """
    engine = get_engine()
    insp = inspect(engine)
    if not insp.has_table("workflows"):
        return
    cols = {c["name"] for c in insp.get_columns("workflows")}
    if "max_retries" in cols:
        return
    ddl = (
        "ALTER TABLE workflows ADD COLUMN max_retries INTEGER NOT NULL DEFAULT 0"
    )
    with engine.begin() as conn:
        conn.execute(text(ddl))


def _ensure_cached_events_first_seen_column() -> None:
    """Add cached_calendar_events.first_seen_at (nullable) if missing.

    The calendar_event trigger uses this column to detect genuinely new
    events instead of ``synced_at``, which the sync task rewrites on
    every 10-minute tick and therefore causes the trigger to re-fire on
    every cached event forever. Old rows get NULL; repo.upsert backfills
    them on the next write and the trigger treats NULL as "older than
    any bootstrap window", i.e. silently ignored.
    """
    engine = get_engine()
    insp = inspect(engine)
    if not insp.has_table("cached_calendar_events"):
        return
    cols = {c["name"] for c in insp.get_columns("cached_calendar_events")}
    if "first_seen_at" in cols:
        return
    if engine.dialect.name == "postgresql":
        ddl = (
            "ALTER TABLE cached_calendar_events "
            "ADD COLUMN first_seen_at TIMESTAMP WITH TIME ZONE"
        )
    else:
        ddl = "ALTER TABLE cached_calendar_events ADD COLUMN first_seen_at DATETIME"
    with engine.begin() as conn:
        conn.execute(text(ddl))


def _drop_legacy_payload_column() -> None:
    """
    One-time migration: remove the old workflows.payload blob column that was
    replaced by the normalized workflow_triggers / workflow_steps tables.
    SQLite does not support DROP COLUMN before 3.35, so we skip it there.
    """
    engine = get_engine()
    if engine.dialect.name == "sqlite":
        return
    insp = inspect(engine)
    if not insp.has_table("workflows"):
        return
    cols = {c["name"] for c in insp.get_columns("workflows")}
    if "payload" not in cols:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE workflows DROP COLUMN payload"))


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())
    _ensure_users_emails_column()
    _migrate_workflow_owner_column()
    _ensure_workflow_runs_retry_columns()
    _ensure_workflow_runs_trigger_context_column()
    _ensure_workflows_max_retries_column()
    _ensure_user_sessions_pkce_column()
    _ensure_cached_events_first_seen_column()
    _drop_legacy_payload_column()


def get_db() -> Generator[Session, None, None]:
    db = SessionFactory(bind=get_engine())
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
