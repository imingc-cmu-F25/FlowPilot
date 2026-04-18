from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from app.trigger.tasks import dispatch_time_triggers
from app.trigger.trigger import TriggerType
from app.trigger.triggerConfig import TimeTriggerConfig
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
                trigger=TimeTriggerConfig(trigger_at=now - timedelta(minutes=1)),
            ),
            # not due time trigger
            SimpleNamespace(
                workflow_id=uuid4(),
                enabled=True,
                trigger=TimeTriggerConfig(trigger_at=now + timedelta(minutes=10)),
            ),
            # disabled workflow
            SimpleNamespace(
                workflow_id=uuid4(),
                enabled=False,
                trigger=TimeTriggerConfig(trigger_at=now - timedelta(minutes=1)),
            ),
            # non-time trigger
            SimpleNamespace(
                workflow_id=uuid4(),
                enabled=True,
                trigger=SimpleNamespace(type=TriggerType.WEBHOOK),
            ),
        ]

    def list_all(self):
        return self._workflows


class FakeRunRepo:
    def __init__(self, _session):
        self.latest_by_workflow = {}

    def list_for_workflow(self, workflow_id, limit=1):
        run = self.latest_by_workflow.get(workflow_id)
        return [run] if run else []


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

    monkeypatch.setattr("app.trigger.tasks.get_engine", lambda: object())
    monkeypatch.setattr("app.trigger.tasks.SessionFactory", lambda bind=None: lambda: fake_session)
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


def test_dispatch_time_triggers_skips_if_recent_time_run_exists(monkeypatch):
    fake_session = FakeSession()
    fake_run_repo = FakeRunRepo(fake_session)
    fake_trigger_service = FakeTriggerService(run_repo=fake_run_repo)

    now = datetime.now(UTC)
    already_run = SimpleNamespace(trigger_type="time", status=RunStatus.SUCCESS, triggered_at=now)

    def _wf_repo_factory(session):
        repo = FakeWorkflowRepo(session)
        first_wf = repo.list_all()[0]
        fake_run_repo.latest_by_workflow[first_wf.workflow_id] = already_run
        return repo

    monkeypatch.setattr("app.trigger.tasks.get_engine", lambda: object())
    monkeypatch.setattr("app.trigger.tasks.SessionFactory", lambda bind=None: lambda: fake_session)
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