from __future__ import annotations

from datetime import UTC, datetime, timedelta

from celery import shared_task
from sqlalchemy.orm import Session

from app.db.connector import get_engine
from app.db.session import SessionFactory
from app.trigger.service import TriggerService
from app.trigger.trigger import TriggerType
from app.trigger.triggerConfig import TimeTriggerConfig
from app.workflow.repo import WorkflowRepository
from app.workflow.run_repo import WorkflowRunRepository
from app.workflow.run import RunStatus

@shared_task(name="trigger.dispatch_time_triggers")
def dispatch_time_triggers() -> int:
    """Scan enabled workflows with time triggers and emit due runs."""
    engine = get_engine()
    session: Session = SessionFactory(bind=engine)()

    emitted = 0
    try:
        wf_repo = WorkflowRepository(session)
        trigger_service = TriggerService(WorkflowRunRepository(session))

        for wf in wf_repo.list_all():
            if not wf.enabled:
                continue
            if wf.trigger.type != TriggerType.TIME:
                continue

            cfg = wf.trigger
            if not isinstance(cfg, TimeTriggerConfig):
                continue

            # Reuse trigger config semantics for "is due now".
            now = datetime.now(UTC)
            due = (
                now >= cfg.trigger_at
                if cfg.recurrence is None
                else cfg.recurrence.is_due(cfg.trigger_at, now)
            )
            if not due:
                continue

            # skip forever after first dispatch
            recent_runs = WorkflowRunRepository(session).list_for_workflow(wf.workflow_id, limit=1)
            last_run = recent_runs[0] if recent_runs else None

            if last_run and last_run.trigger_type == "time":
                if cfg.recurrence is None and last_run.status in {
                    RunStatus.PENDING,
                    RunStatus.RUNNING,
                    RunStatus.SUCCESS,
                }:
                    continue

                # only skip if a run was dispatched very recently.
                if (
                    cfg.recurrence is not None
                    and last_run.triggered_at >= now - timedelta(seconds=60)
                    and last_run.status in {RunStatus.PENDING, RunStatus.RUNNING, RunStatus.SUCCESS}
                ):
                    continue

            trigger_service.emit_workflow_event(
                workflow_id=wf.workflow_id,
                trigger_type="time",
                enqueue=True,
            )
            emitted += 1

        session.commit()
        return emitted
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()