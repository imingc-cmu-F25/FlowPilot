import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SuggestionORM(Base):
    """
    Stores AI-generated workflow suggestions for history + accept flow.
    """
    __tablename__ = "suggestions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    user_name: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.name", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    strategy_used: Mapped[str] = mapped_column(String(32), nullable=False)
    analysis: Mapped[dict] = mapped_column(JSON, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    workflow_draft: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
