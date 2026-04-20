from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from app.trigger.tasks import dispatch_custom_triggers, dispatch_time_triggers
from app.trigger.trigger import TriggerType
from app.trigger.triggerConfig import CustomTriggerConfig, TimeTriggerConfig
from app.workflow.run import RunStatus


class FakeSession:
    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


class FakeWorkflowRepo:
    def __init__(self, _session):
        now = datetime.now(UTC)
        self._workflows = [
            # due time trigger
            SimpleNamespace(
                workflow_id=uuid4(),
                enabled=True,
                max_retries=0,
                trigger=TimeTriggerConfig(trigger_at=now - timedelta(minutes=1)),
            ),
            # not due time trigger
            SimpleNamespace(
                workflow_id=uuid4(),
                enabled=True,
                max_retries=0,
                trigger=TimeTriggerConfig(trigger_at=now + timedelta(minutes=10)),
            ),
            # disabled workflow
            SimpleNamespace(
                workflow_id=uuid4(),
                enabled=False,
                max_retries=0,
                trigger=TimeTriggerConfig(trigger_at=now - timedelta(minutes=1)),
            ),
            # non-time trigger
            SimpleNamespace(
                workflow_id=uuid4(),
                enabled=True,
                max_retries=0,
                trigger=SimpleNamespace(type=TriggerType.WEBHOOK),
            ),
        ]

    def list_all(self):
        return self._workflows


class FakeRunRepo:
    def __init__(self, _session):
        self.latest_by_workflow = {}
        # Map of wf_id -> list of (trigger_type, triggered_at). The one-time
        # time-trigger dedup path needs to know *when* prior runs happened so
        # that a workflow rescheduled to a new trigger_at can fire again.
        self.runs_by_workflow: dict = {}

    def list_for_workflow(self, workflow_id, limit=1):
        run = self.latest_by_workflow.get(workflow_id)
        return [run] if run else []

    def exists_with_trigger_type(self, workflow_id, trigger_type, since=None):
        for tt, triggered_at in self.runs_by_workflow.get(workflow_id, []):
            if tt != trigger_type:
                continue
            if since is None or triggered_at >= since:
                return True
        return False


class FakeTriggerService:
    def __init__(self, run_repo=None):
        self.run_repo = run_repo
        self.emitted = []

    def emit_workflow_event(self, workflow_id, trigger_type, enqueue=True, max_retries=0):
        self.emitted.append((workflow_id, trigger_type, enqueue, max_retries))


def test_dispatch_time_triggers_emits_only_due_workflows(monkeypatch):
    fake_session = FakeSession()
    fake_run_repo = FakeRunRepo(fake_session)
    fake_trigger_service = FakeTriggerService(run_repo=fake_run_repo)

    monkeypatch.setattr("app.trigger.tasks.new_session", lambda: fake_session)
    monkeypatch.setattr("app.trigger.tasks.WorkflowRepository", FakeWorkflowRepo)
    monkeypatch.setattr("app.trigger.tasks.WorkflowRunRepository", lambda s: fake_run_repo)
    monkeypatch.setattr(
        "app.trigger.tasks.TriggerService", 
        lambda run_repo=None: fake_trigger_service,
    )

    emitted = dispatch_time_triggers()

    assert emitted == 1
    assert len(fake_trigger_service.emitted) == 1
    assert fake_trigger_service.emitted[0][1] == "time"


def test_dispatch_time_triggers_skips_if_time_run_already_fired(monkeypatch):
    """One-time time triggers must fire exactly once per trigger_at."""
    fake_session = FakeSession()
    fake_run_repo = FakeRunRepo(fake_session)
    fake_trigger_service = FakeTriggerService(run_repo=fake_run_repo)

    def _wf_repo_factory(session):
        repo = FakeWorkflowRepo(session)
        first_wf = repo.list_all()[0]
        # Simulate a time run that already fired after the configured
        # trigger_at — the dedup path should suppress re-dispatch.
        fake_run_repo.runs_by_workflow[first_wf.workflow_id] = [
            ("time", first_wf.trigger.trigger_at + timedelta(seconds=1)),
        ]
        return repo

    monkeypatch.setattr("app.trigger.tasks.new_session", lambda: fake_session)
    monkeypatch.setattr("app.trigger.tasks.WorkflowRepository", _wf_repo_factory)
    monkeypatch.setattr(
        "app.trigger.tasks.WorkflowRunRepository",
        lambda s: fake_run_repo,
    )
    monkeypatch.setattr(
        "app.trigger.tasks.TriggerService",
        lambda run_repo=None: fake_trigger_service,
    )

    emitted = dispatch_time_triggers()

    assert emitted == 0
    assert fake_trigger_service.emitted == []


def test_dispatch_time_triggers_does_not_refire_after_manual_run(monkeypatch):
    """Regression: a user's manual run must not cause the scheduler to forget
    that it already fired a one-time time trigger for this workflow.

    Before the fix, dispatch_time_triggers only looked at the *latest* run and
    only suppressed if its trigger_type == "time". A subsequent manual / webhook
    run would become "latest" and the scheduler would re-emit another time run."""
    fake_session = FakeSession()
    fake_run_repo = FakeRunRepo(fake_session)
    fake_trigger_service = FakeTriggerService(run_repo=fake_run_repo)

    now = datetime.now(UTC)

    def _wf_repo_factory(session):
        repo = FakeWorkflowRepo(session)
        first_wf = repo.list_all()[0]
        # Prior "time" run already fired for this trigger_at, then the user
        # clicked Run Now which wrote a "manual" run as the newest row.
        fake_run_repo.runs_by_workflow[first_wf.workflow_id] = [
            ("time", first_wf.trigger.trigger_at + timedelta(seconds=1)),
            ("manual", now),
        ]
        fake_run_repo.latest_by_workflow[first_wf.workflow_id] = SimpleNamespace(
            trigger_type="manual",
            status=RunStatus.SUCCESS,
            triggered_at=now,
        )
        return repo

    monkeypatch.setattr("app.trigger.tasks.new_session", lambda: fake_session)
    monkeypatch.setattr("app.trigger.tasks.WorkflowRepository", _wf_repo_factory)
    monkeypatch.setattr(
        "app.trigger.tasks.WorkflowRunRepository",
        lambda s: fake_run_repo,
    )
    monkeypatch.setattr(
        "app.trigger.tasks.TriggerService",
        lambda run_repo=None: fake_trigger_service,
    )

    emitted = dispatch_time_triggers()

    assert emitted == 0
    assert fake_trigger_service.emitted == []


def test_dispatch_time_triggers_refires_after_reschedule(monkeypatch):
    """Regression: editing trigger_at forward to a new future moment must
    allow the scheduler to fire once more when that new moment arrives.

    The old dedup used `exists_with_trigger_type(..., "time")` without a
    `since` filter, which froze the workflow after its first dispatch even
    when the user clearly rescheduled it. Now the dedup is scoped to runs
    at-or-after the configured trigger_at, which this test pins down."""
    fake_session = FakeSession()
    fake_run_repo = FakeRunRepo(fake_session)
    fake_trigger_service = FakeTriggerService(run_repo=fake_run_repo)

    now = datetime.now(UTC)

    def _wf_repo_factory(session):
        repo = FakeWorkflowRepo(session)
        first_wf = repo.list_all()[0]
        # Old time run is 10 minutes before the *current* trigger_at: i.e.
        # the user already ran this workflow once, then rescheduled it to a
        # new (now just-past) time. The scheduler should see the dispatch is
        # due and that no run exists after the new trigger_at → fire again.
        fake_run_repo.runs_by_workflow[first_wf.workflow_id] = [
            ("time", first_wf.trigger.trigger_at - timedelta(minutes=10)),
        ]
        return repo

    monkeypatch.setattr("app.trigger.tasks.new_session", lambda: fake_session)
    monkeypatch.setattr("app.trigger.tasks.WorkflowRepository", _wf_repo_factory)
    monkeypatch.setattr(
        "app.trigger.tasks.WorkflowRunRepository",
        lambda s: fake_run_repo,
    )
    monkeypatch.setattr(
        "app.trigger.tasks.TriggerService",
        lambda run_repo=None: fake_trigger_service,
    )

    emitted = dispatch_time_triggers()

    assert emitted == 1
    assert len(fake_trigger_service.emitted) == 1
    assert fake_trigger_service.emitted[0][1] == "time"
    # Suppress unused variable lint — `now` is deliberately sampled to keep the
    # semantics of "runs are recent vs. trigger_at" obvious to future readers.
    assert now is not None


def test_dispatch_time_triggers_recurring_suppressed_by_recent_manual_run(monkeypatch):
    """Regression: recurring time triggers should dedup against *any* recent run,
    including manual clicks, so a user's Run-Now seconds before the next
    scheduled tick doesn't produce a near-duplicate auto run."""
    fake_session = FakeSession()
    fake_run_repo = FakeRunRepo(fake_session)
    fake_trigger_service = FakeTriggerService(run_repo=fake_run_repo)

    now = datetime.now(UTC)
    from app.trigger.recurrence import RecurrenceFrequency, RecurrenceRule

    class RecurringWorkflowRepo:
        def __init__(self, _session):
            self.wf_id = uuid4()
            self._workflows = [
                SimpleNamespace(
                    workflow_id=self.wf_id,
                    enabled=True,
                    max_retries=0,
                    trigger=TimeTriggerConfig(
                        trigger_at=now - timedelta(minutes=5),
                        recurrence=RecurrenceRule(
                            frequency=RecurrenceFrequency.MINUTELY, interval=1
                        ),
                    ),
                ),
            ]

        def list_all(self):
            return self._workflows

    def _wf_repo_factory(session):
        repo = RecurringWorkflowRepo(session)
        fake_run_repo.latest_by_workflow[repo.wf_id] = SimpleNamespace(
            trigger_type="manual",
            status=RunStatus.SUCCESS,
            triggered_at=now - timedelta(seconds=5),
        )
        return repo

    monkeypatch.setattr("app.trigger.tasks.new_session", lambda: fake_session)
    monkeypatch.setattr("app.trigger.tasks.WorkflowRepository", _wf_repo_factory)
    monkeypatch.setattr(
        "app.trigger.tasks.WorkflowRunRepository",
        lambda s: fake_run_repo,
    )
    monkeypatch.setattr(
        "app.trigger.tasks.TriggerService",
        lambda run_repo=None: fake_trigger_service,
    )

    emitted = dispatch_time_triggers()

    assert emitted == 0
    assert fake_trigger_service.emitted == []


class FakeCustomWorkflowRepo:
    def __init__(self, _session):
        self._workflows = [
            # truthy condition → should fire
            SimpleNamespace(
                workflow_id=uuid4(),
                enabled=True,
                max_retries=0,
                trigger=CustomTriggerConfig(condition="true"),
            ),
            # falsy condition → must not fire
            SimpleNamespace(
                workflow_id=uuid4(),
                enabled=True,
                max_retries=0,
                trigger=CustomTriggerConfig(condition="false"),
            ),
            # disabled
            SimpleNamespace(
                workflow_id=uuid4(),
                enabled=False,
                max_retries=0,
                trigger=CustomTriggerConfig(condition="true"),
            ),
            # non-custom trigger must be ignored
            SimpleNamespace(
                workflow_id=uuid4(),
                enabled=True,
                max_retries=0,
                trigger=SimpleNamespace(type=TriggerType.TIME),
            ),
        ]

    def list_all(self):
        return self._workflows


def test_dispatch_custom_triggers_emits_only_truthy_enabled(monkeypatch):
    fake_session = FakeSession()
    fake_run_repo = FakeRunRepo(fake_session)
    fake_trigger_service = FakeTriggerService(run_repo=fake_run_repo)

    monkeypatch.setattr("app.trigger.tasks.new_session", lambda: fake_session)
    monkeypatch.setattr("app.trigger.tasks.WorkflowRepository", FakeCustomWorkflowRepo)
    monkeypatch.setattr("app.trigger.tasks.WorkflowRunRepository", lambda s: fake_run_repo)
    monkeypatch.setattr(
        "app.trigger.tasks.TriggerService",
        lambda run_repo=None: fake_trigger_service,
    )

    emitted = dispatch_custom_triggers()

    assert emitted == 1
    assert len(fake_trigger_service.emitted) == 1
    assert fake_trigger_service.emitted[0][1] == "custom"


def test_dispatch_custom_triggers_respects_dedup_window(monkeypatch):
    fake_session = FakeSession()
    fake_run_repo = FakeRunRepo(fake_session)
    fake_trigger_service = FakeTriggerService(run_repo=fake_run_repo)

    now = datetime.now(UTC)
    recent = SimpleNamespace(trigger_type="custom", status=RunStatus.SUCCESS, triggered_at=now)

    def _wf_repo_factory(session):
        repo = FakeCustomWorkflowRepo(session)
        truthy_wf = repo.list_all()[0]
        fake_run_repo.latest_by_workflow[truthy_wf.workflow_id] = recent
        return repo

    monkeypatch.setattr("app.trigger.tasks.new_session", lambda: fake_session)
    monkeypatch.setattr("app.trigger.tasks.WorkflowRepository", _wf_repo_factory)
    monkeypatch.setattr("app.trigger.tasks.WorkflowRunRepository", lambda s: fake_run_repo)
    monkeypatch.setattr(
        "app.trigger.tasks.TriggerService",
        lambda run_repo=None: fake_trigger_service,
    )

    emitted = dispatch_custom_triggers()

    assert emitted == 0
    assert fake_trigger_service.emitted == []


def test_dispatch_tasks_build_a_real_session():
    """Smoke test: run the tasks against the real (empty) test DB.

    This test intentionally does NOT mock out new_session / SessionFactory — if
    someone later reintroduces the `SessionFactory(bind=engine)()` typo, this
    test raises TypeError before any assertion runs. With an empty DB and no
    workflows, both dispatch tasks must return 0 without errors.
    """
    assert dispatch_time_triggers() == 0
    assert dispatch_custom_triggers() == 0