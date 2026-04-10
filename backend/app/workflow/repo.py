from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import WorkflowORM
from app.workflow.workflow import WorkflowDefinition


class WorkflowRepository:
    """
    Persists WorkflowDefinition objects via WorkflowORM (JSON payload column).
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def save(self, wf: WorkflowDefinition) -> WorkflowDefinition:
        payload = wf.model_dump(mode="json")
        orm = self._db.get(WorkflowORM, wf.workflow_id)
        if orm is not None:
            orm.payload = payload
        else:
            self._db.add(WorkflowORM(id=wf.workflow_id, payload=payload))
        self._db.flush()
        return wf

    def get(self, wf_id: UUID) -> WorkflowDefinition | None:
        orm = self._db.get(WorkflowORM, wf_id)
        if orm is None:
            return None
        return WorkflowDefinition.model_validate(orm.payload)

    def list_all(self) -> list[WorkflowDefinition]:
        rows = self._db.query(WorkflowORM).all()
        return [WorkflowDefinition.model_validate(r.payload) for r in rows]

    def delete(self, wf_id: UUID) -> None:
        orm = self._db.get(WorkflowORM, wf_id)
        if orm is not None:
            self._db.delete(orm)
            self._db.flush()
