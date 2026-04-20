from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from celery import shared_task
from sqlalchemy.orm import Session

from app.connectors.repo import CachedCalendarEventRepository
from app.db.session import new_session
from app.trigger.customTrigger import CustomTrigger
from app.trigger.service import TriggerService
from app.trigger.trigger import TriggerType
from app.trigger.triggerConfig import (
    CalendarEventTriggerConfig,
    CustomTriggerConfig,
    TimeTriggerConfig,
)
from app.workflow.repo import WorkflowRepository
from app.workflow.run import RunStatus
from app.workflow.run_repo import WorkflowRunRepository

# How long we suppress re-firing a custom trigger after it last emitted a run.
_CUSTOM_TRIGGER_DEDUP_WINDOW = timedelta(seconds=60)

# Window we use the *first* time a calendar-event trigger fires for a
# given workflow. Without this, the very first tick would look at "every
# event ever cached" and fire immediately — which is almost never what
# the user meant when they enabled the workflow.
_CALENDAR_TRIGGER_BOOTSTRAP_WINDOW = timedelta(minutes=5)


@shared_task(name="trigger.dispatch_time_triggers")
def dispatch_time_triggers() -> int:
    """Scan enabled workflows with time triggers and emit due runs."""
    session: Session = new_session()

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

            run_repo = WorkflowRunRepository(session)

            if cfg.recurrence is None:
                # One-time: fire exactly once *for this trigger_at*. Scoping
                # the existence check to runs at/after the configured
                # trigger_at has two nice properties:
                #   1. Back-to-back beat ticks don't re-fire after the first
                #      dispatch (the prior time run has triggered_at >= now
                #      >= trigger_at).
                #   2. If the user edits trigger_at forward to a new future
                #      moment, the old time run no longer satisfies the
                #      `since` filter, so the scheduler will fire once more
                #      when the new moment arrives — which is exactly what
                #      "I rescheduled it" should mean.
                # A plain trigger_type filter (no `since`) would instead
                # freeze the workflow after its first dispatch forever, which
                # is the bug we hit when users rescheduled from the builder.
                if run_repo.exists_with_trigger_type(
                    wf.workflow_id, "time", since=cfg.trigger_at
                ):
                    continue
            else:
                # Recurring: suppress dispatch for 60 s after *any* run of this
                # workflow — otherwise a user's manual click at 08:59:30 would
                # be followed by an auto time-run at 09:00:00 they didn't want.
                recent_runs = run_repo.list_for_workflow(wf.workflow_id, limit=1)
                last_run = recent_runs[0] if recent_runs else None
                if (
                    last_run is not None
                    and last_run.triggered_at >= now - timedelta(seconds=60)
                    and last_run.status in {
                        RunStatus.PENDING,
                        RunStatus.RUNNING,
                        RunStatus.SUCCESS,
                    }
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


@shared_task(name="trigger.dispatch_custom_triggers")
def dispatch_custom_triggers() -> int:
    """Scan enabled workflows with custom triggers and emit runs when their
    condition evaluates truthy.

    Custom triggers are deliberately minimal (see CustomTrigger.evaluate): this
    task re-evaluates each active custom trigger every minute and suppresses
    repeated emission within a short dedup window so a constantly-true
    condition doesn't produce one run per second.
    """
    session: Session = new_session()

    emitted = 0
    try:
        wf_repo = WorkflowRepository(session)
        run_repo = WorkflowRunRepository(session)
        trigger_service = TriggerService(run_repo)
        evaluator = CustomTrigger()

        now = datetime.now(UTC)

        for wf in wf_repo.list_all():
            if not wf.enabled:
                continue
            if wf.trigger.type != TriggerType.CUSTOM:
                continue
            cfg = wf.trigger
            if not isinstance(cfg, CustomTriggerConfig):
                continue

            try:
                # evaluate() is declared async; drive it synchronously here.
                fired = asyncio.run(evaluator.evaluate({"config": cfg}))
            except Exception:
                # Evaluation errors must not kill the whole dispatch loop.
                continue
            if not fired:
                continue

            # Dedup against *any* recent run, not just custom ones. A manual
            # click seconds before the next evaluation should still suppress
            # the auto-fire — the user already ran it and doesn't expect a
            # duplicate.
            recent_runs = run_repo.list_for_workflow(wf.workflow_id, limit=1)
            last_run = recent_runs[0] if recent_runs else None
            if (
                last_run is not None
                and last_run.triggered_at >= now - _CUSTOM_TRIGGER_DEDUP_WINDOW
                and last_run.status in {RunStatus.PENDING, RunStatus.RUNNING, RunStatus.SUCCESS}
            ):
                continue

            trigger_service.emit_workflow_event(
                workflow_id=wf.workflow_id,
                trigger_type="custom",
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


@shared_task(name="trigger.dispatch_calendar_event_triggers")
def dispatch_calendar_event_triggers() -> int:
    """Fire workflows whose ``calendar_event`` trigger sees new cached events.

    "New" here means the row's ``first_seen_at`` is after the workflow's
    last calendar_event run. We deliberately do NOT look at ``synced_at``
    because the sync task rewrites every cached row every 10 minutes —
    using it as the "new event" signal would re-fire the workflow on
    every existing event forever.

    Exactly one run per tick is emitted no matter how many events are
    new. Workflows that want the event data read it through the
    ``CalendarListUpcoming`` action; this keeps the dispatch loop
    predictable and avoids run storms when a user adds many events at
    once.
    """
    session: Session = new_session()
    emitted = 0
    try:
        wf_repo = WorkflowRepository(session)
        run_repo = WorkflowRunRepository(session)
        trigger_service = TriggerService(run_repo)
        events_repo = CachedCalendarEventRepository(session)

        now = datetime.now(UTC)

        for wf in wf_repo.list_all():
            if not wf.enabled:
                continue
            if wf.trigger.type != TriggerType.CALENDAR_EVENT:
                continue
            cfg = wf.trigger
            if not isinstance(cfg, CalendarEventTriggerConfig):
                continue

            last = run_repo.latest_triggered_at_for_type(
                wf.workflow_id, "calendar_event"
            )
            if last is None:
                since = now - _CALENDAR_TRIGGER_BOOTSTRAP_WINDOW
            else:
                # Slide the window *back* by dedup_seconds so a
                # just-finished dispatch doesn't race a still-arriving
                # sync write.
                since = last - timedelta(seconds=cfg.dedup_seconds)

            new_rows = events_repo.find_since(
                user_name=wf.owner_name,
                since=since,
                title_contains=cfg.title_contains or None,
                calendar_id=cfg.calendar_id or None,
                limit=1,
            )
            if not new_rows:
                continue

            # Suppress if the most recent run of this workflow (any type)
            # is inside dedup_seconds — mirrors the custom-trigger guard.
            recent_runs = run_repo.list_for_workflow(wf.workflow_id, limit=1)
            last_run = recent_runs[0] if recent_runs else None
            if (
                last_run is not None
                and last_run.triggered_at
                >= now - timedelta(seconds=max(cfg.dedup_seconds, 1))
                and last_run.status
                in {RunStatus.PENDING, RunStatus.RUNNING, RunStatus.SUCCESS}
            ):
                continue

            trigger_service.emit_workflow_event(
                workflow_id=wf.workflow_id,
                trigger_type="calendar_event",
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