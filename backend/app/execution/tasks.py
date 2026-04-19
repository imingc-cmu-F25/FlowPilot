"""Celery tasks for workflow execution."""

from __future__ import annotations

import logging
from uuid import UUID

from celery import shared_task
from sqlalchemy.orm import Session

from app.db.connector import get_engine
from app.db.session import SessionFactory
from app.execution.contracts import CELERY_TASK_EXECUTE_RUN
from app.execution.engine import ExecutionEngine

logger = logging.getLogger(__name__)


@shared_task(name=CELERY_TASK_EXECUTE_RUN)
def execute_workflow_run(run_id: str) -> None:
    """
    Execute a workflow run by id.
    Requires an existing workflow_runs row (typically status=pending).
    """
    print(f"[execution] execute_workflow_run started run_id={run_id}", flush=True)
    logger.info("[execution] execute_workflow_run started run_id=%s", run_id)

    rid = UUID(run_id)
    engine = get_engine()
    session: Session = SessionFactory(bind=engine)
    try:
        ExecutionEngine(session).execute(rid)
        session.commit()
        print(f"[execution] execute_workflow_run completed run_id={run_id}", flush=True)
        logger.info("[execution] execute_workflow_run completed run_id=%s", run_id)
    except Exception as exc:
        print(f"[execution] ERROR run_id={run_id}: {exc}", flush=True)
        logger.exception("[execution] execute_workflow_run failed run_id=%s: %s", run_id, exc)
        session.rollback()
        raise
    finally:
        session.close()


@shared_task(name="execution.ping")
def ping() -> str:
    return "pong"
