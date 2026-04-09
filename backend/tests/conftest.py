import os

os.environ.setdefault("DATABASE_CHECK_ON_STARTUP", "false")
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

import pytest

from app.db.base import Base
from app.db.connector import get_engine
from app.db.session import init_db


@pytest.fixture(autouse=True)
def reset_db_tables() -> None:
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    init_db()
    yield
    Base.metadata.drop_all(bind=engine)
