"""Repository for per-step execution records."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.db.schema import WorkflowStepRunORM
from app.execution.states import StepRun, StepRunStatus


class WorkflowStepRunRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, step_run: StepRun) -> StepRun:
        orm = WorkflowStepRunORM(
            id=step_run.id,
            run_id=step_run.run_id,
            step_order=step_run.step_order,
            step_name=step_run.step_name,
            action_type=step_run.action_type,
            status=step_run.status,
            started_at=step_run.started_at,
            finished_at=step_run.finished_at,
            inputs=step_run.inputs,
            output=step_run.output,
            error=step_run.error,
        )
        self._db.add(orm)
        self._db.flush()
        return step_run

    def list_for_run(self, run_id: UUID) -> list[StepRun]:
        rows = (
            self._db.query(WorkflowStepRunORM)
            .filter(WorkflowStepRunORM.run_id == run_id)
            .order_by(WorkflowStepRunORM.step_order)
            .all()
        )
        return [self._to_domain(r) for r in rows]

    @staticmethod
    def _to_domain(orm: WorkflowStepRunORM) -> StepRun:
        return StepRun(
            id=orm.id,
            run_id=orm.run_id,
            step_order=orm.step_order,
            step_name=orm.step_name,
            action_type=orm.action_type,
            status=StepRunStatus(orm.status),
            started_at=orm.started_at,
            finished_at=orm.finished_at,
            inputs=orm.inputs,
            output=orm.output,
            error=orm.error,
        )
