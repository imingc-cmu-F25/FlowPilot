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

## Test Data Injection

The script `seed_march_data.py` populates the database with realistic workflow and execution data for a target month. It is intended for testing the monthly report feature.

### What it creates

- 8 workflows (mix of time-triggered and webhook-triggered, active/paused)
- ~340 workflow runs dated within the target period, with realistic success/failure ratios
- Per-step execution records (`workflow_step_runs`) with resolved inputs, outputs, and error messages

### Prerequisites

- The target user account must already exist in the database (create it via the UI or API first).
- The Docker stack must be running (`docker compose up` from `infra/`).

### Configuration

Open `seed_march_data.py` and set `SEED_USER` at the top to the username you want the workflows seeded under:

```python
SEED_USER = "natalie"   # must match an existing user in the users table
```

The script reads the following environment variables for the database connection (defaults match the Docker Compose setup):

| Variable            | Default     |
|---------------------|-------------|
| `POSTGRES_HOST`     | `localhost`  |
| `POSTGRES_PORT`     | `5432`       |
| `POSTGRES_DB`       | `flowpilot`  |
| `POSTGRES_USER`     | `flowpilot`  |
| `POSTGRES_PASSWORD` | `flowpilot`  |
| `DATABASE_URL`      | *(overrides all above)* |

### Running the script

**Option A — inside the backend container (recommended):**

```bash
docker exec -it flowpilot-backend python seed_march_data.py
```

The container already has `POSTGRES_HOST=postgres` injected via `.env`, so no extra flags are needed.

**Option B — from your local machine (port 5432 is exposed):**

```bash
cd backend
POSTGRES_HOST=localhost uv run python seed_march_data.py
```

### Re-running safely

The script deletes any workflows previously seeded under `SEED_USER` before inserting fresh data, so it is safe to run multiple times. Workflows created by the user through the UI are not affected.

### Generating the report

After seeding, trigger report generation from the UI or via the API:

```bash
curl -X POST http://localhost:8000/api/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "owner_name": "natalie",
    "period_start": "2026-03-01T00:00:00Z",
    "period_end": "2026-03-30T23:59:59Z"
  }'
```

### Verifying the injected data

Run the verification script to print row counts and a status breakdown without opening a database shell:

```bash
docker exec -it flowpilot-backend python check_seed.py
```

Expected output (numbers will match the seed):

```
=== Seed verification ===
  users:              1
  workflows:          8
  workflow_runs:    344  (March 2026: 344)
  workflow_step_runs: ...

--- Workflows ---
  [active  ] Daily Slack Digest
  ...

--- Run status breakdown (March) ---
  success   : 317
  failed    :  27
  pending   :   0
  running   :   0
```

### Note on "Top Errors" in the report

The failed runs are seeded with synthetic error messages (e.g. `HTTP 503`, `SMTP error 550`). These are test data only — they do not reflect real service failures.

---

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
