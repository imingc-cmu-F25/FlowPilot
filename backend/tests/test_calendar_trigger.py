"""Tests for the calendar_event trigger dispatch loop.

The dispatcher lives in ``app.trigger.tasks.dispatch_calendar_event_triggers``
and fires one workflow run per tick when at least one matching cached
event is newer than the last dispatch for that workflow.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from app.trigger.tasks import dispatch_calendar_event_triggers
from app.trigger.trigger import TriggerType
from app.trigger.triggerConfig import CalendarEventTriggerConfig


class FakeSession:
    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


class FakeEventsRepo:
    def __init__(self, _session, rows_by_call):
        self._rows = rows_by_call  # callable returning list[SimpleNamespace]

    def find_since(self, *, user_name, since, title_contains=None, calendar_id=None, limit=100):
        return list(self._rows(user_name=user_name, since=since, limit=limit))


class FakeRunRepo:
    def __init__(self, _session):
        self.latest_by_workflow = {}
        self.latest_triggered_at_by_type = {}

    def list_for_workflow(self, workflow_id, limit=1):
        r = self.latest_by_workflow.get(workflow_id)
        return [r] if r else []

    def latest_triggered_at_for_type(self, workflow_id, trigger_type):
        return self.latest_triggered_at_by_type.get((workflow_id, trigger_type))


class FakeTriggerService:
    def __init__(self, run_repo=None):
        self.emitted = []

    def emit_workflow_event(self, workflow_id, trigger_type, enqueue=True, max_retries=0):
        self.emitted.append((workflow_id, trigger_type))


def _wire_dispatcher(monkeypatch, *, workflows, event_rows, run_repo):
    fake_session = FakeSession()
    fake_trigger_service = FakeTriggerService()

    class _WfRepo:
        def __init__(self, _s):
            pass

        def list_all(self):
            return workflows

    monkeypatch.setattr("app.trigger.tasks.new_session", lambda: fake_session)
    monkeypatch.setattr("app.trigger.tasks.WorkflowRepository", _WfRepo)
    monkeypatch.setattr("app.trigger.tasks.WorkflowRunRepository", lambda _s: run_repo)
    monkeypatch.setattr(
        "app.trigger.tasks.CachedCalendarEventRepository",
        lambda s: FakeEventsRepo(s, event_rows),
    )
    monkeypatch.setattr(
        "app.trigger.tasks.TriggerService",
        lambda run_repo=None: fake_trigger_service,
    )
    return fake_trigger_service


def _wf(**overrides) -> SimpleNamespace:
    defaults = {
        "workflow_id": uuid4(),
        "owner_name": "owner",
        "enabled": True,
        "trigger": CalendarEventTriggerConfig(
            calendar_id="primary", title_contains="", dedup_seconds=60
        ),
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _rows_one(**_):
    return [SimpleNamespace(provider_event_id="e1")]


def _rows_none(**_):
    return []


def test_emits_when_new_event_since_last_dispatch(monkeypatch):
    wf = _wf()
    run_repo = FakeRunRepo(None)
    svc = _wire_dispatcher(
        monkeypatch, workflows=[wf], event_rows=_rows_one, run_repo=run_repo
    )

    emitted = dispatch_calendar_event_triggers()
    assert emitted == 1
    assert svc.emitted == [(wf.workflow_id, "calendar_event")]


def test_skips_when_no_new_events(monkeypatch):
    wf = _wf()
    run_repo = FakeRunRepo(None)
    svc = _wire_dispatcher(
        monkeypatch, workflows=[wf], event_rows=_rows_none, run_repo=run_repo
    )

    emitted = dispatch_calendar_event_triggers()
    assert emitted == 0
    assert svc.emitted == []


def test_skips_when_recent_run_within_dedup(monkeypatch):
    wf = _wf()
    run_repo = FakeRunRepo(None)
    run_repo.latest_by_workflow[wf.workflow_id] = SimpleNamespace(
        trigger_type="calendar_event",
        status="success",
        triggered_at=datetime.now(UTC),
    )
    svc = _wire_dispatcher(
        monkeypatch, workflows=[wf], event_rows=_rows_one, run_repo=run_repo
    )

    emitted = dispatch_calendar_event_triggers()
    assert emitted == 0
    assert svc.emitted == []


def test_ignores_disabled_workflow(monkeypatch):
    wf = _wf(enabled=False)
    run_repo = FakeRunRepo(None)
    svc = _wire_dispatcher(
        monkeypatch, workflows=[wf], event_rows=_rows_one, run_repo=run_repo
    )

    assert dispatch_calendar_event_triggers() == 0
    assert svc.emitted == []


def test_ignores_non_calendar_trigger(monkeypatch):
    wf = _wf(trigger=SimpleNamespace(type=TriggerType.TIME))
    run_repo = FakeRunRepo(None)
    svc = _wire_dispatcher(
        monkeypatch, workflows=[wf], event_rows=_rows_one, run_repo=run_repo
    )

    assert dispatch_calendar_event_triggers() == 0
    assert svc.emitted == []


def test_bootstrap_window_scans_last_five_minutes_when_no_prior_runs(monkeypatch):
    """First time a workflow runs, `since` must be close to now (not epoch)."""
    wf = _wf()
    seen = {}

    def rows(user_name, since, limit):
        seen["since"] = since
        return [SimpleNamespace(provider_event_id="x")]

    run_repo = FakeRunRepo(None)
    _wire_dispatcher(monkeypatch, workflows=[wf], event_rows=rows, run_repo=run_repo)

    dispatch_calendar_event_triggers()
    assert seen["since"] is not None
    # Must be within the last ~5 minutes (+ a generous tick margin).
    assert datetime.now(UTC) - seen["since"] < timedelta(minutes=6)
