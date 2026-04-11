import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserActionORM(Base):
    """
    User-defined reusable action configurations.

    A user can save named action configs (e.g. "Send Slack alert") that can
    be reused as steps across any of their workflows. Mirrors the structure of
    WorkflowStepORM but owned at the user level and not tied to a workflow.
    """
    __tablename__ = "user_actions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    user_name: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.name", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)  # "http_request" | …
    config: Mapped[dict] = mapped_column(JSON, nullable=False)             # full ActionStep dict
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
