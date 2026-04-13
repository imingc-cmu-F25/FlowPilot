from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.action.actionRegistry import ActionRegistry
from app.core.config import settings
from app.db.session import get_db
from app.execution.contracts import enqueue_execute_run
from app.reporting.repo import ReportRepository
from app.reporting.service import make_reporting_service
from app.trigger.triggerRegistry import TriggerRegistry
from app.user.repo import UserRepository
from app.workflow.repo import WorkflowRepository
from app.workflow.run import RunStatus, WorkflowRun
from app.workflow.run_repo import WorkflowRunRepository
from app.workflow.service import (
    CreateWorkflowCommand,
    UpdateWorkflowCommand,
    WorkflowService,
    make_workflow_service,
)
from app.workflow.validator import validate_workflow
from app.workflow.workflow import WorkflowStatus

api_router = APIRouter()


def _format_validation_errors(exc: ValidationError) -> dict:
    errors = []
    for err in exc.errors():
        loc = ".".join(str(part) for part in err.get("loc", []))
        errors.append({"field": loc, "message": err.get("msg", "Invalid value")})
    return {"message": "Validation failed", "errors": errors}


def _format_value_error(exc: ValueError) -> dict:
    return {"message": str(exc)}


def _format_integrity_error(exc: IntegrityError) -> dict:
    message = "Database constraint violated"
    errors = []
    details = str(exc.orig) if exc.orig else str(exc)
    if "workflows_owner_name_fkey" in details:
        message = "Owner not found"
        errors.append({"field": "owner_name", "message": "User does not exist"})
    return {"message": message, "errors": errors}


# System
@api_router.get("/healthz", tags=["system"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


# Workflow 
@api_router.get("/workflows")
def list_workflows(db: Session = Depends(get_db)):
    return WorkflowRepository(db).list_all()


@api_router.post("/workflows", status_code=201)
def create_workflow(
    cmd: CreateWorkflowCommand,
    db: Session = Depends(get_db),
    svc: WorkflowService = Depends(make_workflow_service),
):
    try:
        if UserRepository(db).get_by_name(cmd.owner_name) is None:
            raise HTTPException(
                422,
                detail={
                    "message": "Owner not found",
                    "errors": [
                        {"field": "owner_name", "message": "User does not exist"}
                    ],
                },
            )
        wf = svc.create_workflow(cmd)
        return WorkflowRepository(db).save(wf)
    
    except (ValidationError, ValueError) as exc:
        if isinstance(exc, ValidationError):
            raise HTTPException(422, detail=_format_validation_errors(exc))
        raise HTTPException(422, detail=_format_value_error(exc))
    
    except IntegrityError as exc:
        raise HTTPException(422, detail=_format_integrity_error(exc))
    
    except Exception:
        raise HTTPException(500, detail={"message": "Unexpected server error"})


@api_router.get("/workflows/{wf_id}")
def get_workflow(wf_id: UUID, db: Session = Depends(get_db)):
    wf = WorkflowRepository(db).get(wf_id)
    if wf is None:
        raise HTTPException(404, detail="Workflow not found")
    return wf


@api_router.put("/workflows/{wf_id}")
def update_workflow(
    wf_id: UUID,
    cmd: UpdateWorkflowCommand,
    db: Session = Depends(get_db),
    svc: WorkflowService = Depends(make_workflow_service),
):
    repo = WorkflowRepository(db)
    existing = repo.get(wf_id)
    # Find existing workflow for editing
    if existing is None:
        raise HTTPException(404, detail="Workflow not found")
    
    try:
        updated = svc.update_workflow(existing, cmd)
        return repo.save(updated)
    
    except (ValidationError, ValueError) as exc:
        if isinstance(exc, ValidationError):
            raise HTTPException(422, detail=_format_validation_errors(exc))
        raise HTTPException(422, detail=_format_value_error(exc))
    
    except IntegrityError as exc:
        raise HTTPException(422, detail=_format_integrity_error(exc))
    
    except Exception:
        raise HTTPException(500, detail={"message": "Unexpected server error"})


@api_router.delete("/workflows/{wf_id}", status_code=204)
def delete_workflow(wf_id: UUID, db: Session = Depends(get_db)):
    WorkflowRepository(db).delete(wf_id)


# Validation & Activation 
@api_router.post("/workflows/{wf_id}/validate")
def validate(wf_id: UUID, db: Session = Depends(get_db)):
    wf = WorkflowRepository(db).get(wf_id)
    
    if wf is None:
        raise HTTPException(404, detail="Workflow not found")
    
    errors = validate_workflow(wf)
    return {"valid": len(errors) == 0, "errors": errors}


@api_router.post("/workflows/{wf_id}/activate")
def activate_workflow(wf_id: UUID, db: Session = Depends(get_db)):
    repo = WorkflowRepository(db)
    wf = repo.get(wf_id)
    if wf is None:
        raise HTTPException(404, detail="Workflow not found")
    
    errors = validate_workflow(wf)
    if errors:
        raise HTTPException(422, detail={"message": "Workflow is invalid", "errors": errors})
    
    activated = wf.model_copy(update={"status": WorkflowStatus.ACTIVE, "enabled": True})
    return repo.save(activated)


# Workflow Runs
@api_router.get("/workflows/{wf_id}/runs")
def list_runs(wf_id: UUID, db: Session = Depends(get_db)):
    if WorkflowRepository(db).get(wf_id) is None:
        raise HTTPException(404, detail="Workflow not found")
    return WorkflowRunRepository(db).list_for_workflow(wf_id)


@api_router.get("/workflows/{wf_id}/runs/{run_id}")
def get_run(wf_id: UUID, run_id: UUID, db: Session = Depends(get_db)):
    run = WorkflowRunRepository(db).get(run_id)
    if run is None or run.workflow_id != wf_id:
        raise HTTPException(404, detail="Run not found")
    return run


class CreateWorkflowRunBody(BaseModel):
    """Manual / dev trigger — creates a pending run and optionally enqueues execution."""

    trigger_type: str = Field(default="manual", description="Stored on workflow_runs.trigger_type")
    max_retries: int = Field(default=0, ge=0, le=10)
    enqueue: bool = Field(
        default=True,
        description="If true, dispatch Celery task execution.execute_workflow_run",
    )


@api_router.post("/workflows/{wf_id}/runs", status_code=201, tags=["workflow-runs"])
def create_workflow_run(
    wf_id: UUID,
    body: CreateWorkflowRunBody,
    db: Session = Depends(get_db),
):
    """Create a workflow run row (pending) and optionally enqueue the execution engine."""
    wf_repo = WorkflowRepository(db)
    if wf_repo.get(wf_id) is None:
        raise HTTPException(404, detail="Workflow not found")
    run = WorkflowRun(
        workflow_id=wf_id,
        status=RunStatus.PENDING,
        trigger_type=body.trigger_type,
        max_retries=body.max_retries,
    )
    created = WorkflowRunRepository(db).create(run)
    if body.enqueue:
        enqueue_execute_run(created.run_id)
    return {"run_id": str(created.run_id), "status": created.status.value, "enqueued": body.enqueue}


# Registry
@api_router.get("/registry/actions")
def list_actions():
    return ActionRegistry.list_schemas()


@api_router.get("/registry/triggers")
def list_triggers():
    return TriggerRegistry.list_schemas()


# Reports
class GenerateReportBody(BaseModel):
    owner_name: str
    period_start: datetime
    period_end: datetime


@api_router.get("/reports", tags=["reports"])
def list_reports(owner_name: str, db: Session = Depends(get_db)):
    if UserRepository(db).get_by_name(owner_name) is None:
        raise HTTPException(404, detail="Owner not found")
    return ReportRepository(db).list_for_owner(owner_name)


@api_router.get("/reports/{report_id}", tags=["reports"])
def get_report(report_id: UUID, db: Session = Depends(get_db)):
    report = ReportRepository(db).get(report_id)
    if report is None:
        raise HTTPException(404, detail="Report not found")
    return report


@api_router.post("/reports/generate", status_code=201, tags=["reports"])
def generate_report(body: GenerateReportBody, db: Session = Depends(get_db)):
    """Synchronous manual trigger for the reporting pipeline.

    Runs the pipeline in-process (no Celery) for dev/testing. The async,
    beat-driven path enqueues reporting.generate_monthly_report via Celery.
    """
    if UserRepository(db).get_by_name(body.owner_name) is None:
        raise HTTPException(404, detail="Owner not found")
    if body.period_end <= body.period_start:
        raise HTTPException(
            422,
            detail={"message": "period_end must be after period_start"},
        )
    service = make_reporting_service(db)
    report = service.generate_monthly_report(
        owner_name=body.owner_name,
        period_start=body.period_start,
        period_end=body.period_end,
    )
    return report
