"""WorkflowRunRepository — persists WorkflowRun records to workflow_runs table."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.db.schema import WorkflowORM, WorkflowRunORM
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
            retry_count=run.retry_count,
            max_retries=run.max_retries,
        )
        self._db.add(orm)
        self._db.flush()
        return run

    def commit(self) -> None:
        """Commit the underlying session. Exposed so callers that need the row
        to be visible to other processes (e.g. a Celery worker about to pick up
        the run) can flush the write without reaching into self._db directly.
        """
        self._db.commit()

    def try_claim_running(self, run_id: UUID) -> WorkflowRun | None:
        """
        Atomically transition PENDING -> RUNNING. Returns the run if claimed, else None.
        Used to avoid duplicate execution when multiple workers see the same task.
        """
        now = datetime.now(UTC)
        stmt = (
            update(WorkflowRunORM)
            .where(
                WorkflowRunORM.id == run_id,
                WorkflowRunORM.status == RunStatus.PENDING.value,
            )
            .values(
                status=RunStatus.RUNNING.value,
                started_at=now,
            )
            .execution_options(synchronize_session=False)
        )
        result = self._db.execute(stmt)
        if result.rowcount == 0:
            return None
        self._db.flush()
        return self.get(run_id)

    def mark_running(self, run_id: UUID) -> WorkflowRun | None:
        """Transition a run from PENDING to RUNNING (non-atomic; prefer try_claim_running)."""
        orm = self._db.get(WorkflowRunORM, run_id)
        if orm is None:
            return None
        orm.status = RunStatus.RUNNING.value
        orm.started_at = datetime.now(UTC)
        self._db.flush()
        return self._to_domain(orm)

    def mark_retrying(self, run_id: UUID, retry_count: int) -> WorkflowRun | None:
        orm = self._db.get(WorkflowRunORM, run_id)
        if orm is None:
            return None
        orm.status = RunStatus.RETRYING.value
        orm.retry_count = retry_count
        self._db.flush()
        return self._to_domain(orm)

    def mark_running_from_retry(self, run_id: UUID) -> WorkflowRun | None:
        """RETRYING -> RUNNING before re-attempting a step."""
        orm = self._db.get(WorkflowRunORM, run_id)
        if orm is None:
            return None
        orm.status = RunStatus.RUNNING.value
        self._db.flush()
        return self._to_domain(orm)

    def mark_success(self, run_id: UUID, output: dict | None = None) -> WorkflowRun | None:
        """Transition a run to SUCCESS and store final output."""
        orm = self._db.get(WorkflowRunORM, run_id)
        if orm is None:
            return None
        orm.status = RunStatus.SUCCESS.value
        orm.finished_at = datetime.now(UTC)
        orm.output = output
        self._db.flush()
        return self._to_domain(orm)

    def mark_failed(self, run_id: UUID, error: str) -> WorkflowRun | None:
        """Transition a run to FAILED and store the error message."""
        orm = self._db.get(WorkflowRunORM, run_id)
        if orm is None:
            return None
        orm.status = RunStatus.FAILED.value
        orm.finished_at = datetime.now(UTC)
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

    def latest_triggered_at_for_type(
        self,
        workflow_id: UUID,
        trigger_type: str,
    ) -> datetime | None:
        """Return the most recent ``triggered_at`` for a given trigger type,
        or None if the workflow has never been triggered that way.

        Used by the calendar-event dispatcher to decide which cached
        events are "new since last fire" for a given workflow.
        """
        row = (
            self._db.query(WorkflowRunORM.triggered_at)
            .filter(
                WorkflowRunORM.workflow_id == workflow_id,
                WorkflowRunORM.trigger_type == trigger_type,
            )
            .order_by(WorkflowRunORM.triggered_at.desc())
            .first()
        )
        return row[0] if row else None

    def exists_with_trigger_type(
        self,
        workflow_id: UUID,
        trigger_type: str,
        since: datetime | None = None,
    ) -> bool:
        """Return True if any run exists for (workflow, trigger_type) since `since`.

        Used by the time-trigger dispatcher to guarantee one-time triggers
        fire exactly once, even when newer manual / webhook / custom runs are
        logged in between and would otherwise hide the original time run from
        a simple "latest run" check.
        """
        q = self._db.query(WorkflowRunORM.id).filter(
            WorkflowRunORM.workflow_id == workflow_id,
            WorkflowRunORM.trigger_type == trigger_type,
        )
        if since is not None:
            q = q.filter(WorkflowRunORM.triggered_at >= since)
        return self._db.query(q.exists()).scalar() is True

    def list_for_owner_in_period(
        self,
        owner_name: str,
        period_start: datetime,
        period_end: datetime,
    ) -> list[WorkflowRun]:
        """Return all runs owned by `owner_name` triggered within [start, end].

        Joins workflow_runs against workflows to scope by owner. Used by the
        reporting pipeline's DataCollectionFilter.
        """
        rows = (
            self._db.query(WorkflowRunORM)
            .join(WorkflowORM, WorkflowRunORM.workflow_id == WorkflowORM.id)
            .filter(
                WorkflowORM.owner_name == owner_name,
                WorkflowRunORM.triggered_at >= period_start,
                WorkflowRunORM.triggered_at <= period_end,
            )
            .order_by(WorkflowRunORM.triggered_at.asc())
            .all()
        )
        return [self._to_domain(r) for r in rows]

    def list_owner_workflow_names(self, owner_name: str) -> dict[str, str]:
        """Return {workflow_id_str: name} for every workflow owned by `owner_name`.

        Used by the reporting pipeline to turn UUIDs into human-readable
        names in the rendered report. Kept here (rather than in the workflow
        repo) so the reporting pipeline depends on a single repo.
        """
        rows = (
            self._db.query(WorkflowORM.id, WorkflowORM.name)
            .filter(WorkflowORM.owner_name == owner_name)
            .all()
        )
        return {str(wf_id): name for wf_id, name in rows}

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
            retry_count=getattr(orm, "retry_count", 0),
            max_retries=getattr(orm, "max_retries", 0),
        )
