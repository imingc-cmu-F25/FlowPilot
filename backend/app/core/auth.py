"""
Authentication helper — resolves the current user from the Authorization header.

Tokens are issued by the login endpoint and stored in the user_sessions table.
The resolver is intentionally lenient: it returns None when no token is present,
so endpoints can choose between required and optional authentication without
duplicating header parsing logic.
"""

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
    """Return the username for the bearer token, or None if unauthenticated."""
    token = _extract_token(authorization)
    if not token:
        return None
    session = db.get(UserSessionORM, token)
    return session.user_name if session else None


def get_current_user(
    current: str | None = Depends(get_current_user_optional),
) -> str:
    """Require an authenticated user; raise 401 otherwise."""
    if current is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return current
