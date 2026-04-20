"""Local cache of Google Calendar events per user.

The Architecture Haiku calls for the ExternalConnector to synchronize
external data locally so workflow execution does not depend on the
availability of third-party APIs. Events are identified by the
(user, provider_event_id) pair so a re-sync is idempotent.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CachedCalendarEventORM(Base):
    __tablename__ = "cached_calendar_events"
    __table_args__ = (
        UniqueConstraint(
            "user_name",
            "provider",
            "provider_event_id",
            name="uq_cached_calendar_event_identity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_name: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.name", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="google_calendar")
    calendar_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(255), nullable=False)

    title: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    html_link: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    raw: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Last time we wrote to this row (any field). Bumped by every sync
    # tick even when nothing changed, so it's fine for "is the cache
    # fresh?" checks but unsafe to use as a "new-event" signal.
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Timestamp of the *first* time this (user, calendar, event_id) tuple
    # landed in our cache. Immutable after insert — that's what makes
    # the calendar_event trigger ("fire on new events") dedup correctly
    # across 10-minute re-syncs. Nullable for backfill from pre-column
    # rows; repo.upsert treats NULL as "never seen" and fills it in.
    first_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
