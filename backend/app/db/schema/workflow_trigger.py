import uuid

from sqlalchemy import JSON, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WorkflowTriggerORM(Base):
    """
    One trigger per workflow (UNIQUE on workflow_id).

    `type` column mirrors TriggerType for server-side queries (e.g. "fetch all
    time-based triggers due in the next minute" without deserialising JSON).
    `config` stores the full TriggerConfig as JSON so the domain model can be
    reconstructed without loss.
    """
    __tablename__ = "workflow_triggers"

    trigger_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False)   # "time" | "webhook"
    config: Mapped[dict] = mapped_column(JSON, nullable=False)       # full TriggerConfig dict
