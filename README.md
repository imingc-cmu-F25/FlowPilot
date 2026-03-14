# FlowPilot

FlowPilot is a lightweight workflow automation platform for students and individual knowledge workers.  
This repository is a **bootstrap monorepo** for team collaboration, with architecture-aligned folders and setup only (no business features yet).

## Tech Stack

- **Frontend**: React + TypeScript + Vite
- **Backend**: FastAPI (Python) + Celery
- **Data & Queue**: PostgreSQL + Redis
- **Infra**: Docker + Docker Compose
- **AI Integration (planned)**: Third-party AI API (for workflow suggestions and monthly summaries)

## Repository Structure

```text
.
├── frontend/                # WebClient
│   └── src/
│       ├── app/
│       ├── features/
│       ├── pages/
│       └── shared/
├── backend/                 # APILayer + core backend services
│   └── app/
│       ├── api/
│       ├── core/
│       ├── workflow/
│       ├── trigger/
│       ├── execution/
│       ├── action/
│       ├── reporting/
│       └── connectors/
├── infra/
│   ├── docker-compose.yml
│   └── postgres/init.sql
├── docs/
│   ├── architecture.md
│   └── contributing.md
└── .github/workflows/ci.yml
```

## Service Mapping (from architecture docs)

- `frontend/`: WebClient
- `backend/app/api/`: APILayer
- `backend/app/workflow/`: WorkflowService
- `backend/app/trigger/`: TriggerService
- `backend/app/execution/`: ExecutionEngine
- `backend/app/action/`: ActionService
- `backend/app/reporting/`: ReportingService
- `backend/app/connectors/`: ExternalConnector

## Prerequisites

- Node.js 22+
- Python 3.11+
- `uv` (Python package/project manager)
- Docker Desktop (or Docker Engine + Compose)

## Environment Setup

Copy env files before running:

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Notes:
- Compose services read variables from root `.env`.
- Backend local `uv` run uses `backend/.env`.

## Quick Start (Docker)

```bash
make up
```

After startup:
- Frontend: <http://localhost:5173>
- Backend docs: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/api/healthz>

Stop all services:

```bash
make down
```

Tail logs:

```bash
make logs
```

## Local Dev Without Docker

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Backend API

```bash
cd backend
uv sync --all-groups
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Celery Worker

```bash
cd backend
uv run celery -A app.worker.celery_app worker --loglevel=info
```

## Collaboration Workflow

- Create branches using `feat/...`, `fix/...`, or `chore/...`.
- Keep pull requests focused and small.
- Document setup/contract changes in README or `docs/`.
- Follow `docs/contributing.md` for team ownership and DoD.

## What Is Included vs Not Included

Included:
- Architecture-aligned directories
- Base dependencies and tooling
- Health check endpoint
- Celery worker bootstrap
- Docker local stack

Not included (intentional):
- Workflow business logic
- Auth and authorization implementation
- Database schema/migrations
- Third-party connector implementations
