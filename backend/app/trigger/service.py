from app.execution.contracts import enqueue_execute_run
from app.trigger.trigger import TriggerSpec
from app.trigger.triggerConfig import TriggerConfig
from app.trigger.triggerFactories import build_trigger_config
from app.workflow.run import RunStatus, WorkflowRun
from app.workflow.run_repo import WorkflowRunRepository


class TriggerService:
    """Coordinates trigger config creation and event emission."""

    def __init__(self, run_repo: WorkflowRunRepository | None = None) -> None:
        self._run_repo = run_repo

    def build_config(self, spec: TriggerSpec) -> TriggerConfig:
        return build_trigger_config(spec)

    def emit_workflow_event(
        self,
        workflow_id,
        trigger_type: str,
        enqueue: bool = True,
        max_retries: int = 0,
    ) -> WorkflowRun:
    
        if self._run_repo is None:
            raise RuntimeError("run_repo is required for event emission")

        run = WorkflowRun(
            workflow_id=workflow_id,
            status=RunStatus.PENDING,
            trigger_type=trigger_type,
            max_retries=max_retries,
        )

        created = self._run_repo.create(run)
        if enqueue:
            # Commit before enqueueing so the Celery worker can actually see
            # the new PENDING row (see create_workflow_run for the same fix).
            self._run_repo.commit()
            enqueue_execute_run(created.run_id)
        return created