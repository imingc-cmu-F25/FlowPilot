from uuid import uuid4

import pytest
from app.trigger.service import TriggerService
from app.trigger.trigger import TriggerSpec, TriggerType
from app.workflow.run import RunStatus


class FakeRunRepo:
    def __init__(self):
        self.created = []

    def create(self, run):
        self.created.append(run)
        return run


def test_build_config_delegates_to_factory_entry():
    svc = TriggerService(run_repo=FakeRunRepo())
    spec = TriggerSpec(
        type=TriggerType.CUSTOM,
        parameters={"condition": "true"},
    )
    cfg = svc.build_config(spec)
    assert cfg.type == TriggerType.CUSTOM


def test_emit_workflow_event_creates_pending_run_without_enqueue(monkeypatch):
    from app.trigger import service as trigger_service_module

    called = {"enqueued": False}

    def fake_enqueue(_run_id):
        called["enqueued"] = True

    monkeypatch.setattr(trigger_service_module, "enqueue_execute_run", fake_enqueue)

    repo = FakeRunRepo()
    svc = TriggerService(run_repo=repo)

    created = svc.emit_workflow_event(
        workflow_id=uuid4(),
        trigger_type="custom",
        enqueue=False,
    )

    assert created.status == RunStatus.PENDING
    assert called["enqueued"] is False
    assert len(repo.created) == 1

def test_emit_workflow_event_requires_repo():
    svc = TriggerService()
    with pytest.raises(RuntimeError, match="run_repo is required"):
        svc.emit_workflow_event(
            workflow_id=uuid4(),
            trigger_type="time",
            enqueue=False,
        )