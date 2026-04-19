"""Quick check: print row counts and sample data for the March 2026 seed."""
import os
from datetime import UTC, datetime

import app.db.schema  # noqa: F401
from app.db.schema.user import UserORM
from app.db.schema.workflow import WorkflowORM
from app.db.schema.workflow_run import WorkflowRunORM
from app.db.schema.workflow_step_run import WorkflowStepRunORM
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

_host = os.environ.get("POSTGRES_HOST", "localhost")
_port = os.environ.get("POSTGRES_PORT", "5432")
_db   = os.environ.get("POSTGRES_DB", "flowpilot")
_user = os.environ.get("POSTGRES_USER", "flowpilot")
_pw   = os.environ.get("POSTGRES_PASSWORD", "flowpilot")
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"postgresql+psycopg://{_user}:{_pw}@{_host}:{_port}/{_db}",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

MARCH_START = datetime(2026, 3, 1, tzinfo=UTC)
MARCH_END   = datetime(2026, 3, 31, tzinfo=UTC)

with Session() as s:
    users      = s.execute(select(func.count()).select_from(UserORM)).scalar()
    workflows  = s.execute(select(func.count()).select_from(WorkflowORM)).scalar()
    runs_total = s.execute(select(func.count()).select_from(WorkflowRunORM)).scalar()
    runs_march = s.execute(
        select(func.count()).select_from(WorkflowRunORM)
        .where(WorkflowRunORM.triggered_at >= MARCH_START)
        .where(WorkflowRunORM.triggered_at <  MARCH_END)
    ).scalar()
    step_runs  = s.execute(select(func.count()).select_from(WorkflowStepRunORM)).scalar()

    print("=== Seed verification ===")
    print(f"  users:           {users}")
    print(f"  workflows:       {workflows}")
    print(f"  workflow_runs:   {runs_total}  (March 2026: {runs_march})")
    print(f"  workflow_step_runs: {step_runs}")

    print("\n--- Workflows ---")
    for wf in s.execute(select(WorkflowORM)).scalars():
        print(f"  [{wf.status:8s}] {wf.name}")

    print("\n--- Run status breakdown (March) ---")
    for status in ("success", "failed", "pending", "running"):
        n = s.execute(
            select(func.count()).select_from(WorkflowRunORM)
            .where(WorkflowRunORM.triggered_at >= MARCH_START)
            .where(WorkflowRunORM.triggered_at <  MARCH_END)
            .where(WorkflowRunORM.status == status)
        ).scalar()
        print(f"  {status:10s}: {n}")
