"""Celery tasks for workflow execution."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from celery import shared_task
from sqlalchemy.orm import Session

from app.db.schema import WorkflowRunORM
from app.db.session import new_session
from app.execution.contracts import CELERY_TASK_EXECUTE_RUN
from app.execution.engine import ExecutionEngine
from app.workflow.run import RunStatus
from app.workflow.run_repo import WorkflowRunRepository

# How long a run can sit in RUNNING before the reaper decides the worker died.
# In practice workflow execution should be well under this; anything longer is
# almost certainly a crashed worker rather than an in-flight step.
_STALE_RUN_AFTER = timedelta(minutes=10)


@shared_task(
    name=CELERY_TASK_EXECUTE_RUN,
    bind=True,
    # Retry the *Celery task* (not the in-process step retry loop) when an
    # unexpected exception escapes the engine — e.g. a transient DB error,
    # Redis blip, or OOM retry. Business-level step failures are still handled
    # inside ExecutionEngine via the State pattern and do NOT bubble up here.
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=3,
)
def execute_workflow_run(self, run_id: str) -> None:
    """
    Execute a workflow run by id.
    Requires an existing workflow_runs row (typically status=pending).

    Thanks to ExecutionEngine.try_claim_running, re-running this task for the
    same run id is safe: an already-claimed run short-circuits without running
    its actions again.
    """
    rid = UUID(run_id)
    session: Session = new_session()
    try:
        # Guard against the API committing the new run row slightly after
        # send_task fires. If we get here before the producer commit is
        # visible, ask Celery to retry this task with its usual backoff so
        # the run doesn't get stuck in PENDING.
        if session.get(WorkflowRunORM, rid) is None:
            raise self.retry(
                exc=RuntimeError(f"workflow_run {run_id} not yet visible"),
                countdown=1,
                max_retries=5,
            )
        ExecutionEngine(session).execute(rid)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@shared_task(name="execution.reap_stale_runs")
def reap_stale_runs() -> int:
    """Find RUNNING workflow runs older than _STALE_RUN_AFTER and fail them.

    This exists because a worker that crashes mid-execution (SIGKILL, pod
    eviction, OOM) leaves its claim in the RUNNING state forever. Running this
    periodically from beat is our last-resort recovery so those runs don't
    hang and block dashboards or reports.
    """
    session: Session = new_session()
    reaped = 0
    try:
        cutoff = datetime.now(UTC) - _STALE_RUN_AFTER
        stale_rows = (
            session.query(WorkflowRunORM)
            .filter(
                WorkflowRunORM.status == RunStatus.RUNNING.value,
                WorkflowRunORM.started_at <= cutoff,
            )
            .all()
        )
        repo = WorkflowRunRepository(session)
        for row in stale_rows:
            repo.mark_failed(
                row.id,
                "Run reaped by scheduler: worker likely crashed before completion.",
            )
            reaped += 1
        session.commit()
        return reaped
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@shared_task(name="execution.ping")
def ping() -> str:
    return "pong"
