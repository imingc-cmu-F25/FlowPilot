"""Repository helpers for external connector state.

Keeps all DB touches for ``UserConnectionORM`` and
``CachedCalendarEventORM`` in one place so the connector + action + tasks
can stay thin.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.schema import CachedCalendarEventORM, UserConnectionORM


class UserConnectionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, user_name: str, provider: str) -> UserConnectionORM | None:
        stmt = select(UserConnectionORM).where(
            UserConnectionORM.user_name == user_name,
            UserConnectionORM.provider == provider,
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def list_for_provider(self, provider: str) -> list[UserConnectionORM]:
        stmt = select(UserConnectionORM).where(UserConnectionORM.provider == provider)
        return list(self._db.execute(stmt).scalars())

    def upsert(
        self,
        *,
        user_name: str,
        provider: str,
        access_token: str,
        refresh_token: str | None,
        token_uri: str,
        scopes: list[str],
        expiry: datetime | None,
    ) -> UserConnectionORM:
        """Create-or-update a connection row idempotently.

        Google only hands out a refresh_token on first consent; a re-auth
        with ``prompt=consent`` will return a new one, while a silent
        re-auth returns only a new access_token. Preserve whatever we
        already have when the provider omits it.
        """
        existing = self.get(user_name, provider)
        now = datetime.now(UTC)
        if existing is None:
            row = UserConnectionORM(
                user_name=user_name,
                provider=provider,
                access_token=access_token,
                refresh_token=refresh_token,
                token_uri=token_uri,
                scopes=scopes,
                expiry=expiry,
                created_at=now,
                updated_at=now,
            )
            self._db.add(row)
            self._db.flush()
            return row

        existing.access_token = access_token
        if refresh_token:
            existing.refresh_token = refresh_token
        existing.token_uri = token_uri
        existing.scopes = scopes
        existing.expiry = expiry
        existing.updated_at = now
        self._db.flush()
        return existing

    def delete(self, user_name: str, provider: str) -> bool:
        existing = self.get(user_name, provider)
        if existing is None:
            return False
        self._db.delete(existing)
        self._db.flush()
        return True


class CachedCalendarEventRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_for_user(
        self,
        user_name: str,
        *,
        limit: int = 50,
        upcoming_only: bool = True,
        now: datetime | None = None,
        max_start: datetime | None = None,
    ) -> list[CachedCalendarEventORM]:
        """Return cached events for a user, upcoming-first by default.

        ``upcoming_only`` filters out events that have already ended
        (``end <= now`` or, for rows missing ``end``, ``start < now``).
        This is what the UI + the ``CalendarListUpcoming`` action almost
        always want — past events remain in the DB for audit / trigger
        bookkeeping but are hidden from "what's next" views.

        ``max_start`` gives callers a "within the next N hours" style
        cap: events whose ``start`` is *after* this moment are excluded.
        Rows with a NULL ``start`` are always kept regardless — treat
        them as "unscheduled but still outstanding" so we don't silently
        drop them from digests.
        """
        now = now or datetime.now(UTC)
        stmt = select(CachedCalendarEventORM).where(
            CachedCalendarEventORM.user_name == user_name,
        )
        if upcoming_only:
            # Prefer end >= now (event still in progress or future); fall
            # back to start >= now for rows where Google didn't return an
            # end (e.g. all-day events in some edge cases).
            stmt = stmt.where(
                (CachedCalendarEventORM.end >= now)
                | (
                    CachedCalendarEventORM.end.is_(None)
                    & (CachedCalendarEventORM.start >= now)
                )
            )
        if max_start is not None:
            stmt = stmt.where(
                CachedCalendarEventORM.start.is_(None)
                | (CachedCalendarEventORM.start <= max_start)
            )
        stmt = stmt.order_by(
            CachedCalendarEventORM.start.is_(None),
            CachedCalendarEventORM.start.asc(),
        ).limit(limit)
        return list(self._db.execute(stmt).scalars())

    def find_since(
        self,
        user_name: str,
        *,
        since: datetime,
        title_contains: str | None = None,
        calendar_id: str | None = None,
        limit: int = 100,
    ) -> list[CachedCalendarEventORM]:
        """Return events that *first appeared* in the cache at/after ``since``.

        Used by the calendar-event trigger to fire only on genuinely new
        Google events. Filters on ``first_seen_at`` (immutable after
        insert) rather than ``synced_at`` (bumped by every re-sync) —
        the latter would fire the trigger on every existing event every
        10 minutes. Rows with ``first_seen_at IS NULL`` are pre-column
        rows from older deployments; treat them as "already known" and
        skip.
        """
        stmt = (
            select(CachedCalendarEventORM)
            .where(
                CachedCalendarEventORM.user_name == user_name,
                CachedCalendarEventORM.first_seen_at.is_not(None),
                CachedCalendarEventORM.first_seen_at >= since,
            )
            .order_by(CachedCalendarEventORM.first_seen_at.asc())
            .limit(limit)
        )
        if calendar_id:
            stmt = stmt.where(CachedCalendarEventORM.calendar_id == calendar_id)
        if title_contains:
            stmt = stmt.where(
                CachedCalendarEventORM.title.ilike(f"%{title_contains}%")
            )
        return list(self._db.execute(stmt).scalars())

    def upsert(
        self,
        *,
        user_name: str,
        calendar_id: str,
        provider_event_id: str,
        title: str,
        description: str | None,
        start: datetime | None,
        end: datetime | None,
        status: str | None,
        html_link: str | None,
        raw: dict[str, Any] | None,
    ) -> CachedCalendarEventORM:
        stmt = select(CachedCalendarEventORM).where(
            CachedCalendarEventORM.user_name == user_name,
            CachedCalendarEventORM.provider == "google_calendar",
            CachedCalendarEventORM.provider_event_id == provider_event_id,
        )
        existing = self._db.execute(stmt).scalar_one_or_none()
        now = datetime.now(UTC)
        if existing is None:
            row = CachedCalendarEventORM(
                user_name=user_name,
                provider="google_calendar",
                calendar_id=calendar_id,
                provider_event_id=provider_event_id,
                title=title,
                description=description,
                start=start,
                end=end,
                status=status,
                html_link=html_link,
                raw=raw,
                synced_at=now,
                first_seen_at=now,
            )
            self._db.add(row)
            self._db.flush()
            return row
        existing.calendar_id = calendar_id
        existing.title = title
        existing.description = description
        existing.start = start
        existing.end = end
        existing.status = status
        existing.html_link = html_link
        existing.raw = raw
        existing.synced_at = now
        # Never touch first_seen_at on an existing row. If it's NULL
        # (legacy row from before this column existed) we leave it NULL
        # on purpose — backfilling to ``now`` would cause every legacy
        # cached event to look "new" on the next sync and spam every
        # matching calendar_event trigger exactly once. find_since()
        # filters ``first_seen_at IS NOT NULL`` so NULL rows are safely
        # treated as "already known, don't fire".
        self._db.flush()
        return existing

    def delete_for_user(self, user_name: str) -> int:
        """Drop every cached row for a user (used when they disconnect)."""
        rows = list(
            self._db.execute(
                select(CachedCalendarEventORM).where(
                    CachedCalendarEventORM.user_name == user_name,
                    CachedCalendarEventORM.provider == "google_calendar",
                )
            ).scalars()
        )
        for r in rows:
            self._db.delete(r)
        self._db.flush()
        return len(rows)
