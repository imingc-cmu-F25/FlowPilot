from collections.abc import Generator

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session, sessionmaker

import app.db.schema  # noqa: F401  — registers all ORM classes with Base.metadata
from app.db.base import Base
from app.db.connector import get_engine

SessionFactory = sessionmaker(autoflush=False, autocommit=False, expire_on_commit=False)


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
