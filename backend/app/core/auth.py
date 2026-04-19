"""
Authentication helpers — resolves the current user from the Authorization header
and enforces per-resource ownership checks.

Tokens are issued by the login endpoint and stored in the user_sessions table.
The resolver is intentionally lenient: it returns None when no token is present,
so endpoints can choose between required and optional authentication without
duplicating header parsing logic.

The ownership helpers (enforce_*_access) implement a uniform policy:
  * If no user is authenticated, allow the call (MVP backwards-compat; caller
    decides whether to tighten further).
  * If a user *is* authenticated, the resource owner_name must match the
    authenticated user; otherwise raise 404 (not 403) so we don't leak resource
    existence to outsiders.
"""

from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db.schema import UserSessionORM
from app.db.session import get_db


def _extract_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip() or None
    return authorization.strip() or None


def get_current_user_optional(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> str | None:
    """Return the username for the bearer token, or None if unauthenticated.

    Important distinction:
      * no Authorization header at all   -> None (anonymous; kept for MVP back-compat)
      * header present but token invalid -> 401 (don't silently downgrade to anon,
                                                 otherwise a bad token would bypass
                                                 enforce_*_access ownership checks)
    """
    token = _extract_token(authorization)
    if not token:
        return None
    session = db.get(UserSessionORM, token)
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return session.user_name


def get_current_user(
    current: str | None = Depends(get_current_user_optional),
) -> str:
    """Require an authenticated user; raise 401 otherwise."""
    if current is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return current


def enforce_workflow_access(db: Session, wf_id: UUID, current_user: str | None):
    """Return the workflow if the caller may access it, else raise HTTPException.

    404 is used for both "workflow not found" and "belongs to another user" so
    outsiders can't probe for valid ids.
    """
    from app.workflow.repo import WorkflowRepository

    wf = WorkflowRepository(db).get(wf_id)
    if wf is None:
        raise HTTPException(404, detail="Workflow not found")
    if current_user is not None and wf.owner_name != current_user:
        raise HTTPException(404, detail="Workflow not found")
    return wf


def enforce_run_access(db: Session, wf_id: UUID, run_id: UUID, current_user: str | None):
    """Load a run and ensure it belongs to (wf_id, current_user)."""
    from app.workflow.run_repo import WorkflowRunRepository

    enforce_workflow_access(db, wf_id, current_user)
    run = WorkflowRunRepository(db).get(run_id)
    if run is None or run.workflow_id != wf_id:
        raise HTTPException(404, detail="Run not found")
    return run


def enforce_owner_match(owner_name: str, current_user: str | None) -> None:
    """Raise 404 if an authenticated caller is asking about someone else's data."""
    if current_user is not None and current_user != owner_name:
        raise HTTPException(404, detail="Owner not found")
