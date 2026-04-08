from collections.abc import Generator

from sqlalchemy.orm import Session, sessionmaker

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.connector import get_engine

SessionFactory = sessionmaker(autoflush=False, autocommit=False, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())


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
