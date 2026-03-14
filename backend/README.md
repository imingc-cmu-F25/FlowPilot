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
