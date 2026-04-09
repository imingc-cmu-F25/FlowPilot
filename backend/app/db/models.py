import uuid

from sqlalchemy import JSON, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserORM(Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(255), primary_key=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    emails: Mapped[list | None] = mapped_column(JSON, nullable=True)


class UserSessionORM(Base):
    __tablename__ = "user_sessions"

    token: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_name: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.name", ondelete="CASCADE"),
        nullable=False,
    )


class WorkflowORM(Base):
    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
