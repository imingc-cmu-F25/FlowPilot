"""Integration tests for ExecutionEngine (DB + mocked I/O)."""

from unittest.mock import patch

import pytest
from app.db.connector import get_engine
from app.db.session import init_db
from app.execution.engine import ExecutionEngine
from app.user.repo import UserRepository
from app.workflow.repo import WorkflowRepository
from app.workflow.run import RunStatus, WorkflowRun
from app.workflow.run_repo import WorkflowRunRepository
from app.workflow.service import CreateWorkflowCommand, WorkflowService
from app.workflow.workflow import WorkflowDefinitionBuilder, WorkflowStatus
from sqlalchemy.orm import sessionmaker
from tests.test_workflow_service import EMAIL_STEP, TIME_SPEC
from app.trigger.service import TriggerService

@pytest.fixture
def db_session():
    init_db()
    maker = sessionmaker(
        bind=get_engine(),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    session = maker()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _seed_user_and_workflow(session) -> tuple[object, object]:
    UserRepository(session).create("exec-owner", "x" * 60)
    cmd = CreateWorkflowCommand(
        owner_name="exec-owner",
        name="Exec WF",
        trigger=TIME_SPEC,
        steps=[EMAIL_STEP],
        enabled=True,
    )
    wf = WorkflowService(WorkflowDefinitionBuilder(), TriggerService()).create_workflow(cmd)
    wf = wf.model_copy(update={"status": WorkflowStatus.ACTIVE, "enabled": True})
    saved = WorkflowRepository(session).save(wf)
    session.commit()
    return saved


def test_engine_marks_success_with_mocked_action(db_session):
    wf = _seed_user_and_workflow(db_session)
    run = WorkflowRun(workflow_id=wf.workflow_id, trigger_type="manual")
    created = WorkflowRunRepository(db_session).create(run)
    db_session.commit()
    rid = created.run_id

    with patch("app.execution.engine.run_action_sync", return_value={"ok": True}):
        ExecutionEngine(db_session).execute(rid)

    db_session.expire_all()
    final = WorkflowRunRepository(db_session).get(rid)
    assert final is not None
    assert final.status == RunStatus.SUCCESS
    assert final.output == {"ok": True}


def test_try_claim_idempotent_second_worker(db_session):
    wf = _seed_user_and_workflow(db_session)
    run = WorkflowRun(workflow_id=wf.workflow_id, trigger_type="manual")
    created = WorkflowRunRepository(db_session).create(run)
    db_session.commit()
    rid = created.run_id

    with patch("app.execution.engine.run_action_sync", return_value={"ok": True}):
        ExecutionEngine(db_session).execute(rid)
        # Second invocation should not fail; run already terminal
        ExecutionEngine(db_session).execute(rid)

    final = WorkflowRunRepository(db_session).get(rid)
    assert final.status == RunStatus.SUCCESS


def test_engine_fails_when_workflow_disabled(db_session):
    wf = _seed_user_and_workflow(db_session)
    wf_disabled = wf.model_copy(update={"enabled": False})
    WorkflowRepository(db_session).save(wf_disabled)
    session = db_session
    run = WorkflowRun(workflow_id=wf.workflow_id, trigger_type="manual")
    created = WorkflowRunRepository(session).create(run)
    session.commit()

    ExecutionEngine(session).execute(created.run_id)
    final = WorkflowRunRepository(session).get(created.run_id)
    assert final.status == RunStatus.FAILED
    assert "not enabled" in (final.error or "")
