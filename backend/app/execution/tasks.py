"""Celery tasks for workflow execution."""

from __future__ import annotations

from uuid import UUID

from celery import shared_task
from sqlalchemy.orm import Session

from app.db.connector import get_engine
from app.db.session import SessionFactory
from app.execution.contracts import CELERY_TASK_EXECUTE_RUN
from app.execution.engine import ExecutionEngine


@shared_task(name=CELERY_TASK_EXECUTE_RUN)
def execute_workflow_run(run_id: str) -> None:
    """
    Execute a workflow run by id.
    Requires an existing workflow_runs row (typically status=pending).
    """
    rid = UUID(run_id)
    engine = get_engine()
    session: Session = SessionFactory(bind=engine)()
    try:
        ExecutionEngine(session).execute(rid)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@shared_task(name="execution.ping")
def ping() -> str:
    return "pong"
