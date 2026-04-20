"""Celery tasks for external connectors.

Today: periodic Google Calendar sync. Runs every 10 minutes (see
``app.worker``) and walks every user with a linked Google connection,
refreshing the ``cached_calendar_events`` table so workflows can read
recent calendar data without an outbound API call during execution.
"""

from __future__ import annotations

import logging

from celery import shared_task

from app.connectors import google_calendar as gcal
from app.connectors.repo import UserConnectionRepository
from app.db.session import new_session

logger = logging.getLogger(__name__)


@shared_task(name="connectors.sync_google_calendars", bind=True)
def sync_google_calendars(self) -> dict[str, int]:
    """Refresh every linked Google calendar into the local cache.

    A single user's failure must not poison the whole sweep; each user is
    processed inside its own try-block and the task returns a summary
    dict (``{ok, failed, events}``) so Celery's flower / logs show what
    happened at a glance.
    """
    if not gcal.is_configured():
        logger.info("Skipping Google Calendar sync: GOOGLE_CLIENT_ID/SECRET not set")
        return {"ok": 0, "failed": 0, "events": 0}

    session = new_session()
    total_events = 0
    ok = 0
    failed = 0
    try:
        connections = UserConnectionRepository(session).list_for_provider(gcal.PROVIDER)
        for conn in connections:
            sub = new_session()
            try:
                total_events += gcal.sync_events(sub, conn.user_name)
                sub.commit()
                ok += 1
            except Exception:
                sub.rollback()
                failed += 1
                logger.exception(
                    "Google Calendar sync failed for user=%s",
                    conn.user_name,
                )
            finally:
                sub.close()
    finally:
        session.close()

    return {"ok": ok, "failed": failed, "events": total_events}
