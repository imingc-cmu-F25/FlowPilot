from collections.abc import Generator

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.connector import get_engine

SessionFactory = sessionmaker(autoflush=False, autocommit=False, expire_on_commit=False)


def _ensure_users_emails_column() -> None:
    engine = get_engine()
    insp = inspect(engine)
    if not insp.has_table("users"):
        return
    cols = {c["name"] for c in insp.get_columns("users")}
    if "emails" in cols:
        return
    ddl = "ALTER TABLE users ADD COLUMN emails JSON"
    if engine.dialect.name == "sqlite":
        ddl = "ALTER TABLE users ADD COLUMN emails TEXT"
    with engine.begin() as conn:
        conn.execute(text(ddl))


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())
    _ensure_users_emails_column()


def get_db() -> Generator[Session, None, None]:
    db = SessionFactory(bind=get_engine())
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
