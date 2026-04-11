"""WorkflowRunRepository — persists WorkflowRun records to workflow_runs table."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.schema import WorkflowRunORM
from app.workflow.run import RunStatus, WorkflowRun


class WorkflowRunRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    # write

    def create(self, run: WorkflowRun) -> WorkflowRun:
        """Insert a new run record."""
        orm = WorkflowRunORM(
            id=run.run_id,
            workflow_id=run.workflow_id,
            status=run.status,
            trigger_type=run.trigger_type,
            triggered_at=run.triggered_at,
            started_at=run.started_at,
            finished_at=run.finished_at,
            error=run.error,
            output=run.output,
        )
        self._db.add(orm)
        self._db.flush()
        return run

    def mark_running(self, run_id: UUID) -> WorkflowRun | None:
        """Transition a run from PENDING to RUNNING."""
        orm = self._db.get(WorkflowRunORM, run_id)
        if orm is None:
            return None
        orm.status = RunStatus.RUNNING
        orm.started_at = datetime.now(timezone.utc)
        self._db.flush()
        return self._to_domain(orm)

    def mark_success(self, run_id: UUID, output: dict | None = None) -> WorkflowRun | None:
        """Transition a run to SUCCESS and store final output."""
        orm = self._db.get(WorkflowRunORM, run_id)
        if orm is None:
            return None
        orm.status = RunStatus.SUCCESS
        orm.finished_at = datetime.now(timezone.utc)
        orm.output = output
        self._db.flush()
        return self._to_domain(orm)

    def mark_failed(self, run_id: UUID, error: str) -> WorkflowRun | None:
        """Transition a run to FAILED and store the error message."""
        orm = self._db.get(WorkflowRunORM, run_id)
        if orm is None:
            return None
        orm.status = RunStatus.FAILED
        orm.finished_at = datetime.now(timezone.utc)
        orm.error = error
        self._db.flush()
        return self._to_domain(orm)

    #  read

    def get(self, run_id: UUID) -> WorkflowRun | None:
        orm = self._db.get(WorkflowRunORM, run_id)
        return self._to_domain(orm) if orm else None

    def list_for_workflow(
        self,
        workflow_id: UUID,
        limit: int = 50,
    ) -> list[WorkflowRun]:
        """Return the most recent runs for a workflow, newest first."""
        rows = (
            self._db.query(WorkflowRunORM)
            .filter(WorkflowRunORM.workflow_id == workflow_id)
            .order_by(WorkflowRunORM.triggered_at.desc())
            .limit(limit)
            .all()
        )
        return [self._to_domain(r) for r in rows]

    #  private 

    @staticmethod
    def _to_domain(orm: WorkflowRunORM) -> WorkflowRun:
        return WorkflowRun(
            run_id=orm.id,
            workflow_id=orm.workflow_id,
            status=RunStatus(orm.status),
            trigger_type=orm.trigger_type,
            triggered_at=orm.triggered_at,
            started_at=orm.started_at,
            finished_at=orm.finished_at,
            error=orm.error,
            output=orm.output,
        )
