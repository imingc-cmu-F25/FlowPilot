from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.action.actionRegistry import ActionRegistry
from app.core.config import settings
from app.db.session import get_db
from app.trigger.triggerRegistry import TriggerRegistry
from app.workflow.repo import WorkflowRepository
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


# System

@api_router.get("/healthz", tags=["system"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


# Workflow CRUD 

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
        wf = svc.create_workflow(cmd)
    except (ValidationError, ValueError) as exc:
        raise HTTPException(422, detail=str(exc))
    return WorkflowRepository(db).save(wf)


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
    if existing is None:
        raise HTTPException(404, detail="Workflow not found")
    updated = svc.update_workflow(existing, cmd)
    return repo.save(updated)


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


# Registry

@api_router.get("/registry/actions")
def list_actions():
    return ActionRegistry.list_schemas()


@api_router.get("/registry/triggers")
def list_triggers():
    return TriggerRegistry.list_schemas()
