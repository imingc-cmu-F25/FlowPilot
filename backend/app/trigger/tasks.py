from __future__ import annotations

from datetime import UTC, datetime, timedelta
import logging

from celery import shared_task
from sqlalchemy.orm import Session

from app.db.connector import get_engine
from app.db.session import SessionFactory
from app.trigger.service import TriggerService
from app.trigger.trigger import TriggerType
from app.trigger.triggerConfig import TimeTriggerConfig
from app.workflow.repo import WorkflowRepository
from app.workflow.run import RunStatus
from app.workflow.run_repo import WorkflowRunRepository

logger = logging.getLogger(__name__)


@shared_task(name="trigger.dispatch_time_triggers")
def dispatch_time_triggers() -> int:
    """Scan enabled workflows with time triggers and emit due runs."""
    print("[time_trigger] scan started", flush=True)
    logger.info("[time_trigger] scan started")

    engine = get_engine()
    session: Session = SessionFactory(bind=engine)

    emitted = 0
    try:
        wf_repo = WorkflowRepository(session)
        trigger_service = TriggerService(WorkflowRunRepository(session))

        all_workflows = wf_repo.list_all()
        print(f"[time_trigger] found {len(all_workflows)} total workflows", flush=True)
        logger.info("[time_trigger] found %d total workflows", len(all_workflows))

        for wf in all_workflows:
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

            print(
                f"[time_trigger] workflow={wf.workflow_id} trigger_at={cfg.trigger_at.isoformat()} due={due}",
                flush=True,
            )
            logger.info(
                "[time_trigger] workflow=%s trigger_at=%s due=%s",
                wf.workflow_id,
                cfg.trigger_at.isoformat(),
                due,
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
                    print(f"[time_trigger] workflow={wf.workflow_id} skipped (one-shot already ran)", flush=True)
                    logger.info("[time_trigger] workflow=%s skipped (one-shot already ran)", wf.workflow_id)
                    continue

                # only skip if a run was dispatched very recently.
                if (
                    cfg.recurrence is not None
                    and last_run.triggered_at >= now - timedelta(seconds=60)
                    and last_run.status in {RunStatus.PENDING, RunStatus.RUNNING, RunStatus.SUCCESS}
                ):
                    print(f"[time_trigger] workflow={wf.workflow_id} skipped (dispatched recently)", flush=True)
                    logger.info("[time_trigger] workflow=%s skipped (dispatched recently)", wf.workflow_id)
                    continue

            print(f"[time_trigger] dispatching workflow={wf.workflow_id}", flush=True)
            logger.info("[time_trigger] dispatching workflow=%s", wf.workflow_id)

            trigger_service.emit_workflow_event(
                workflow_id=wf.workflow_id,
                trigger_type="time",
                enqueue=True,
            )
            emitted += 1

        print(f"[time_trigger] scan complete, emitted={emitted}", flush=True)
        logger.info("[time_trigger] scan complete, emitted=%d", emitted)
        session.commit()
        return emitted
    except Exception as exc:
        print(f"[time_trigger] ERROR: {exc}", flush=True)
        logger.exception("[time_trigger] unexpected error: %s", exc)
        session.rollback()
        raise
    finally:
        session.close()