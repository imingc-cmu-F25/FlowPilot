import os

os.environ.setdefault("DATABASE_CHECK_ON_STARTUP", "false")
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
# Run Celery tasks inline in tests so we don't need a Redis broker.
os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "true")

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
