import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserTriggerORM(Base):
    """
    User-defined reusable trigger configurations.

    A user can save named trigger configs (e.g. "Every Monday 9am") that can
    be attached to any of their workflows. Mirrors the structure of
    WorkflowTriggerORM but owned at the user level.
    """
    __tablename__ = "user_triggers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    user_name: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.name", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)   # "time" | "webhook"
    config: Mapped[dict] = mapped_column(JSON, nullable=False)       # full TriggerConfig dict
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
