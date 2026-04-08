import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.action.Register import ActionRegistry
from app.core.config import settings
from app.db.models import UserORM, UserSessionORM, WorkflowORM
from app.db.session import get_db
from app.trigger.Register import TriggerRegistry
from app.user.User import AuthResponse, User, UserCredentials, UserPublic
from app.workflow.Validator import validate_workflow
from app.workflow.Workflow import Workflow

api_router = APIRouter()

SESSION_COOKIE_NAME = "fp_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 7


def _row_to_user(row: UserORM) -> User:
    return User(name=row.name, password=row.password_hash)


@api_router.get("/healthz", tags=["system"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


def _cookie_secure() -> bool:
    return settings.app_env.lower() not in ("development", "dev", "local")


@api_router.post("/auth/register", tags=["auth"])
def register(credentials: UserCredentials, db: Session = Depends(get_db)) -> JSONResponse:
    if db.get(UserORM, credentials.name):
        return JSONResponse(
            status_code=409,
            content=AuthResponse(
                ok=False,
                message="Username already registered",
                user=None,
                token=None,
            ).model_dump(mode="json"),
        )
    temp = User(name=credentials.name, password="")
    temp.set_password(credentials.password)
    db.add(UserORM(name=credentials.name, password_hash=temp.password))
    return JSONResponse(
        status_code=201,
        content=AuthResponse(
            ok=True,
            message="Registration successful",
            user=UserPublic(name=credentials.name),
            token=None,
        ).model_dump(mode="json"),
    )


@api_router.post("/auth/login", tags=["auth"])
def login(credentials: UserCredentials, db: Session = Depends(get_db)) -> JSONResponse:
    row = db.get(UserORM, credentials.name)
    user = _row_to_user(row) if row else None
    if user is None or not user.verify_password(credentials.password):
        return JSONResponse(
            status_code=401,
            content=AuthResponse(
                ok=False,
                message="Invalid username or password",
                user=None,
                token=None,
            ).model_dump(mode="json"),
        )
    token = secrets.token_urlsafe(32)
    db.add(UserSessionORM(token=token, user_name=user.name))
    body = AuthResponse(
        ok=True,
        message="Login successful",
        user=UserPublic(name=user.name),
        token=token,
    )
    response = JSONResponse(status_code=200, content=body.model_dump(mode="json"))
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(),
        path="/",
    )
    return response


@api_router.get("/users", response_model=list[UserPublic], tags=["auth"])
def list_users(db: Session = Depends(get_db)) -> list[UserPublic]:
    rows = db.scalars(select(UserORM).order_by(UserORM.name)).all()
    return [UserPublic(name=r.name) for r in rows]


@api_router.get("/workflows")
async def list_workflows(db: Session = Depends(get_db)):
    rows = db.scalars(select(WorkflowORM)).all()
    return [Workflow.model_validate(r.payload) for r in rows]


@api_router.post("/workflows", status_code=201)
async def create_workflow(wf: Workflow, db: Session = Depends(get_db)):
    if db.get(WorkflowORM, wf.id):
        raise HTTPException(status_code=409, detail="Workflow already exists")
    db.add(WorkflowORM(id=wf.id, payload=wf.model_dump(mode="json")))
    return wf


@api_router.get("/workflows/{wf_id}")
async def get_workflow(wf_id: UUID, db: Session = Depends(get_db)):
    row = db.get(WorkflowORM, wf_id)
    if not row:
        raise HTTPException(404)
    return Workflow.model_validate(row.payload)


@api_router.put("/workflows/{wf_id}")
async def update_workflow(wf_id: UUID, wf: Workflow, db: Session = Depends(get_db)):
    row = db.get(WorkflowORM, wf_id)
    if not row:
        raise HTTPException(404)
    if wf.id != wf_id:
        raise HTTPException(status_code=400, detail="Workflow id must match URL")
    row.payload = wf.model_dump(mode="json")
    return wf


@api_router.delete("/workflows/{wf_id}", status_code=204)
async def delete_workflow(wf_id: UUID, db: Session = Depends(get_db)):
    row = db.get(WorkflowORM, wf_id)
    if row:
        db.delete(row)


@api_router.post("/workflows/{wf_id}/validate")
async def validate(wf_id: UUID, db: Session = Depends(get_db)):
    row = db.get(WorkflowORM, wf_id)
    if not row:
        raise HTTPException(404)
    wf = Workflow.model_validate(row.payload)
    errors = validate_workflow(wf)
    return {"valid": len(errors) == 0, "errors": errors}


@api_router.post("/workflows/{wf_id}/activate")
async def activate_workflow(wf_id: UUID):
    # validate, set status to ACTIVE, register with worker
    ...


@api_router.get("/registry/actions")
async def list_actions():
    return ActionRegistry.list_schemas()


@api_router.get("/registry/triggers")
async def list_triggers():
    return TriggerRegistry.list_schemas()
