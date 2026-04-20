"""FastAPI routes for external connectors.

Exposes the Google Calendar OAuth flow + status + disconnect + cached
event readout. All write endpoints require an authenticated user.

State handling: the OAuth ``state`` parameter is the caller's bearer
session token. It's generated server-side (on login), unguessable, and
already scoped to a single user — reusing it here gives us CSRF
protection + user binding without introducing a second secret.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.connectors import google_calendar as gcal
from app.connectors.repo import CachedCalendarEventRepository, UserConnectionRepository
from app.core.auth import get_current_user
from app.core.config import settings
from app.db.schema import UserSessionORM
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connectors", tags=["connectors"])


def _serialize_connection(row) -> dict[str, Any]:
    return {
        "provider": row.provider,
        "scopes": list(row.scopes or []),
        "expiry": row.expiry.isoformat() if row.expiry else None,
        "connected_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _serialize_event(row) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "calendar_id": row.calendar_id,
        "provider_event_id": row.provider_event_id,
        "title": row.title,
        "description": row.description,
        "start": row.start.isoformat() if row.start else None,
        "end": row.end.isoformat() if row.end else None,
        "status": row.status,
        "html_link": row.html_link,
        "synced_at": row.synced_at.isoformat() if row.synced_at else None,
    }


@router.get("/google/status")
def google_status(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    row = UserConnectionRepository(db).get(current_user, gcal.PROVIDER)
    return {
        "configured": gcal.is_configured(),
        "connected": row is not None,
        "connection": _serialize_connection(row) if row is not None else None,
    }


@router.get("/google/authorize")
def google_authorize(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Return the Google consent URL (the frontend opens it in a new tab).

    ``state`` is the caller's bearer token, so when Google redirects the
    browser back (without an Authorization header) we can still resolve
    which user is completing the flow. We also stash the PKCE
    code_verifier on the session row so /callback can finish the exchange.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    parts = authorization.split(" ", 1)
    token = parts[1].strip() if len(parts) == 2 and parts[0].lower() == "bearer" else authorization
    try:
        result = gcal.build_authorize_url(db, state=token)
    except gcal.GoogleCalendarNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"authorize_url": result.url, "configured": True, "user": current_user}


@router.get("/google/callback")
def google_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Handle the OAuth redirect from Google.

    Browser-facing: finishes by 302'ing back to the frontend Integrations
    page (``/dashboard/integrations``) with a
    ``google_calendar=connected|error`` query flag so the UI can render
    a toast without polling.
    """
    redirect_back = f"{settings.frontend_base_url.rstrip('/')}/dashboard/integrations"

    if error:
        return RedirectResponse(
            url=f"{redirect_back}?google_calendar=error&reason={error}",
            status_code=302,
        )
    if not code or not state:
        return RedirectResponse(
            url=f"{redirect_back}?google_calendar=error&reason=missing_code_or_state",
            status_code=302,
        )

    session = db.get(UserSessionORM, state)
    if session is None:
        return RedirectResponse(
            url=f"{redirect_back}?google_calendar=error&reason=invalid_state",
            status_code=302,
        )

    verifier = session.oauth_code_verifier
    try:
        gcal.exchange_code(
            db,
            user_name=session.user_name,
            code=code,
            code_verifier=verifier,
        )
        # Verifier is single-use; clear it so a replayed callback can't
        # reuse it (and so the column doesn't linger in plaintext).
        session.oauth_code_verifier = None
        db.add(session)
        db.commit()
    except gcal.GoogleCalendarNotConfigured:
        return RedirectResponse(
            url=f"{redirect_back}?google_calendar=error&reason=not_configured",
            status_code=302,
        )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.exception(
            "Google Calendar OAuth exchange_code failed for user %r (exc=%s)",
            session.user_name,
            type(exc).__name__,
        )
        return RedirectResponse(
            url=(
                f"{redirect_back}?google_calendar=error"
                f"&reason=exchange_failed&detail={type(exc).__name__}"
            ),
            status_code=302,
        )

    return RedirectResponse(
        url=f"{redirect_back}?google_calendar=connected",
        status_code=302,
    )


@router.delete("/google", status_code=204)
def google_disconnect(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    UserConnectionRepository(db).delete(current_user, gcal.PROVIDER)
    CachedCalendarEventRepository(db).delete_for_user(current_user)
    return None


@router.get("/google/events")
def google_events(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200),
    include_past: bool = Query(default=False),
):
    rows = CachedCalendarEventRepository(db).list_for_user(
        current_user,
        limit=limit,
        upcoming_only=not include_past,
    )
    return [_serialize_event(r) for r in rows]


@router.post("/google/sync")
def google_sync(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
    calendar_id: str = Query(default="primary"),
):
    try:
        saved = gcal.sync_events(db, current_user, calendar_id=calendar_id)
        db.commit()
    except gcal.GoogleCalendarNotConnected as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except gcal.GoogleCalendarNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail=f"Google Calendar sync failed: {exc}",
        ) from exc
    return {"synced": saved, "calendar_id": calendar_id}
