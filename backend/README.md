# FlowPilot Backend

This service hosts the FastAPI API layer and Celery worker skeleton for FlowPilot.

## Local Development (uv)

```bash
cp .env.example .env
uv sync --all-groups
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

In another terminal:

```bash
uv run celery -A app.worker.celery_app worker --loglevel=info
```

## Workflow execution (Celery + team contracts)

- **Task name**: `execution.execute_workflow_run` (see `app/execution/contracts.py`).
- **Enqueue from Python** (after inserting a `pending` row in `workflow_runs`):

```python
from uuid import UUID
from app.execution.contracts import enqueue_execute_run

enqueue_execute_run(UUID("..."))  # run_id must exist in DB
```

- **Manual API**: `POST /api/workflows/{workflow_id}/runs` creates a pending run and enqueues by default (`enqueue: true`). Set `enqueue: false` to only create the DB row.

- **Run status strings** (stored in `workflow_runs.status`): `pending`, `running`, `retrying`, `success`, `failed` — see `RunStatus` in `app/workflow/run.py`.
