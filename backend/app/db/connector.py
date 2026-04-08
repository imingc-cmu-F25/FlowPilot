import logging

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from app.core.config import settings

logger = logging.getLogger(__name__)

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = settings.sqlalchemy_database_url
        if url.startswith("sqlite"):
            _engine = create_engine(
                url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        else:
            _engine = create_engine(url, pool_pre_ping=True)
    return _engine


def report_connection_at_startup() -> None:
    if not settings.database_check_on_startup:
        msg = "PostgreSQL: startup check skipped (database_check_on_startup=false)"
        logger.info(msg)
        print(f"[db] {msg}", flush=True)
        return
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        if settings.database_url_override:
            msg = f"Database: connected ({settings.sqlalchemy_database_url})"
        else:
            msg = (
                f"PostgreSQL: connected (host={settings.postgres_host} "
                f"port={settings.postgres_port} database={settings.postgres_db})"
            )
        logger.info(msg)
        print(f"[db] {msg}", flush=True)
    except Exception as exc:
        if settings.database_url_override:
            msg = f"Database: connection failed ({settings.sqlalchemy_database_url!r}): {exc}"
        else:
            msg = (
                f"PostgreSQL: connection failed (host={settings.postgres_host} "
                f"port={settings.postgres_port} database={settings.postgres_db}): {exc}"
            )
        logger.error(msg)
        print(f"[db] {msg}", flush=True)
