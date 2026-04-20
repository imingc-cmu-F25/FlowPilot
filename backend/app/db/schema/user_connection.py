"""Third-party provider connection per user.

Stores the OAuth tokens FlowPilot holds on behalf of a user for external
services (Google Calendar today, easily extensible to Slack, GitHub, etc.).

Token storage is plain text in this MVP so the demo stays self-contained.
For production hardening the ``access_token`` / ``refresh_token`` columns
should be encrypted at rest (e.g. Fernet with a key read from a KMS).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserConnectionORM(Base):
    __tablename__ = "user_connections"
    __table_args__ = (
        UniqueConstraint("user_name", "provider", name="uq_user_connection_provider"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_name: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.name", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)

    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    # Google only returns a refresh_token on the *first* consent with
    # access_type=offline + prompt=consent; keep it nullable so subsequent
    # re-authorizations that omit it don't blow up the constraint.
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_uri: Mapped[str] = mapped_column(String(512), nullable=False)
    scopes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
