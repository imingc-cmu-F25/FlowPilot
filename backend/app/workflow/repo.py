from datetime import UTC, datetime
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy.orm import Session

from app.action.action import ActionStep
from app.db.schema import WorkflowORM, WorkflowStepORM, WorkflowTriggerORM
from app.trigger.triggerConfig import TriggerConfig, WebhookTriggerConfig
from app.workflow.workflow import WorkflowDefinition, WorkflowStatus

# TypeAdapters for discriminated-union reconstruction
_trigger_adapter = TypeAdapter(TriggerConfig)
_step_adapter = TypeAdapter(ActionStep)


class WorkflowRepository:
    """
    Persists WorkflowDefinition objects across three tables:
      - workflows        → metadata (queryable columns)
      - workflow_triggers → one trigger per workflow (type column + JSON config)
      - workflow_steps    → ordered steps (action_type, step_order columns + JSON config)

    The JSON config columns store the full Pydantic model dict so domain objects
    can be reconstructed without loss via the discriminated-union TypeAdapters.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def save(self, wf: WorkflowDefinition) -> WorkflowDefinition:
        """Insert or update all rows for a workflow atomically."""
        self._upsert_workflow(wf)
        self._upsert_trigger(wf)
        self._replace_steps(wf)
        self._db.flush()
        return wf

    def delete(self, wf_id: UUID) -> bool:
        """Soft-delete a workflow by archiving it."""
        orm = self._db.get(WorkflowORM, wf_id)
        if orm is None:
            return False
        orm.status = WorkflowStatus.ARCHIVED.value
        orm.enabled = False
        orm.updated_at = datetime.now(UTC)
        self._db.flush()
        return True

    def get(self, wf_id: UUID) -> WorkflowDefinition | None:
        wf_orm = self._db.get(WorkflowORM, wf_id)
        if wf_orm is None or wf_orm.status == WorkflowStatus.ARCHIVED.value:
            return None
        trigger_orm = (
            self._db.query(WorkflowTriggerORM)
            .filter(WorkflowTriggerORM.workflow_id == wf_id)
            .one_or_none()
        )
        step_orms = (
            self._db.query(WorkflowStepORM)
            .filter(WorkflowStepORM.workflow_id == wf_id)
            .order_by(WorkflowStepORM.step_order)
            .all()
        )
        return self._to_domain(wf_orm, trigger_orm, step_orms)

    def list_all(self) -> list[WorkflowDefinition]:
        """
        List all workflows
        """
        wf_orms = (
            self._db.query(WorkflowORM)
            .filter(WorkflowORM.status != WorkflowStatus.ARCHIVED.value)
            .all()
        )
        if not wf_orms:
            return []
        wf_ids = [wf.id for wf in wf_orms]

        triggers = {
            t.workflow_id: t
            for t in self._db.query(WorkflowTriggerORM)
            .filter(WorkflowTriggerORM.workflow_id.in_(wf_ids))
            .all()
        }

        steps_by_wf: dict[UUID, list[WorkflowStepORM]] = {wf_id: [] for wf_id in wf_ids}
        for s in (
            self._db.query(WorkflowStepORM)
            .filter(WorkflowStepORM.workflow_id.in_(wf_ids))
            .order_by(WorkflowStepORM.step_order)
            .all()
        ):
            steps_by_wf[s.workflow_id].append(s)

        return [
            self._to_domain(wf, triggers.get(wf.id), steps_by_wf.get(wf.id, []))
            for wf in wf_orms
        ]

    def list_enabled_for_webhook(self, path: str, method: str) -> list[WorkflowDefinition]:
        """
        Return enabled workflows whose webhook trigger matches (path, method).
        """
        normalized_method = method.upper()

        wf_orms = (
            self._db.query(WorkflowORM)
            .join(WorkflowTriggerORM, WorkflowTriggerORM.workflow_id == WorkflowORM.id)
            .filter(
                WorkflowORM.enabled.is_(True),
                WorkflowORM.status != WorkflowStatus.ARCHIVED.value,
                WorkflowTriggerORM.type == "webhook",
            )
            .all()
        )

        matched: list[WorkflowDefinition] = []
        for wf_orm in wf_orms:
            trigger_orm = (
                self._db.query(WorkflowTriggerORM)
                .filter(WorkflowTriggerORM.workflow_id == wf_orm.id)
                .one_or_none()
            )
            if trigger_orm is None:
                continue

            trigger_cfg = _trigger_adapter.validate_python(trigger_orm.config)
            if not isinstance(trigger_cfg, WebhookTriggerConfig):
                continue

            if trigger_cfg.path != path:
                continue
            if trigger_cfg.method.upper() != normalized_method:
                continue

            step_orms = (
                self._db.query(WorkflowStepORM)
                .filter(WorkflowStepORM.workflow_id == wf_orm.id)
                .order_by(WorkflowStepORM.step_order)
                .all()
            )
            matched.append(self._to_domain(wf_orm, trigger_orm, step_orms))

        return matched

    #  private helpers
    def _upsert_workflow(self, wf: WorkflowDefinition) -> None:
        """
        insert or update the WorkflowORM row
        """
        orm = self._db.get(WorkflowORM, wf.workflow_id)
        if orm is None:
            self._db.add(WorkflowORM(
                id=wf.workflow_id,
                owner_name=wf.owner_name,
                name=wf.name,
                description=wf.description,
                status=str(wf.status),
                enabled=wf.enabled,
                created_at=wf.created_at,
                updated_at=wf.updated_at,
            ))
        else:
            orm.owner_name = wf.owner_name
            orm.name = wf.name
            orm.description = wf.description
            orm.status = str(wf.status)
            orm.enabled = wf.enabled
            orm.updated_at = wf.updated_at

    def _upsert_trigger(self, wf: WorkflowDefinition) -> None:
        """
        upsert the WorkflowTriggerORM row for the workflow's trigger
        """
        trigger = wf.trigger
        orm = (
            self._db.query(WorkflowTriggerORM)
            .filter(WorkflowTriggerORM.workflow_id == wf.workflow_id)
            .one_or_none()
        )
        config = trigger.model_dump(mode="json")  # includes discriminator `type` field
        if orm is None:
            self._db.add(WorkflowTriggerORM(
                trigger_id=trigger.trigger_id,
                workflow_id=wf.workflow_id,
                type=str(trigger.type),
                config=config,
            ))
        else:
            orm.trigger_id = trigger.trigger_id
            orm.type = str(trigger.type)
            orm.config = config

    def _replace_steps(self, wf: WorkflowDefinition) -> None:
        """Delete existing steps and re-insert. Simpler than diffing for step lists."""
        self._db.query(WorkflowStepORM).filter(
            WorkflowStepORM.workflow_id == wf.workflow_id
        ).delete(synchronize_session=False)

        for step in wf.steps:
            self._db.add(WorkflowStepORM(
                step_id=step.step_id,
                workflow_id=wf.workflow_id,
                action_type=str(step.action_type),
                name=step.name,
                step_order=step.step_order,
                config=step.model_dump(mode="json"),  # includes discriminator `action_type`
            ))

    @staticmethod
    def _to_domain(
        wf_orm: WorkflowORM,
        trigger_orm: WorkflowTriggerORM | None,
        step_orms: list[WorkflowStepORM],
    ) -> WorkflowDefinition:
        trigger = _trigger_adapter.validate_python(trigger_orm.config) if trigger_orm else None
        steps = [_step_adapter.validate_python(s.config) for s in step_orms]
        return WorkflowDefinition(
            workflow_id=wf_orm.id,
            owner_name=wf_orm.owner_name,
            name=wf_orm.name,
            description=wf_orm.description,
            status=wf_orm.status,
            enabled=wf_orm.enabled,
            trigger=trigger,
            steps=steps,
            created_at=wf_orm.created_at,
            updated_at=wf_orm.updated_at,
        )
