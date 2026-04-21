# UPDATE NOTE
Sigrid is now enabled for this repo.
You have new GitHub Actions workflow files.
You will receive a Sigrid invitation shortly - accept it and review the architecture analysis of your repo as part of the project documentation assignment. There's no need to improve the codebase or architecture when working on the implementation. 
Visit Sigrid at https://sigrid-says.com/cmusvfse

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

## Production Deployment (single EC2 + Caddy + HTTPS)

The repo ships with a standalone production compose file at
`infra/docker-compose.prod.yml`. Compared to the dev compose file, it:

- Postgres and Redis no longer publish ports to the host (internal network
  only).
- `backend` / `worker` / `beat` stop bind-mounting the host source tree and
  stop running in `--reload` mode; the backend runs with `--workers 2`.
- `frontend` is built with `frontend/Dockerfile.prod` (Vite build → static
  files served by nginx). `VITE_API_BASE_URL` is baked in as `/api`.
- A `caddy` service terminates TLS on :80/:443, reverse-proxies `/api/*` and
  `/hooks/*` to the backend, and serves everything else from the frontend
  container. HTTPS certificates are issued automatically by Let's Encrypt.

### One-time setup on the EC2 host

```bash
# Install Docker + the compose plugin (Ubuntu 24.04)
sudo apt update && sudo apt install -y docker.io docker-compose-plugin git make
sudo usermod -aG docker $USER   # log out & back in for this to take effect

# Clone + configure
git clone <your-repo-url> FlowPilot && cd FlowPilot
cp .env.example .env
# Edit .env:
#   APP_ENV=production
#   POSTGRES_PASSWORD=<strong random value, e.g. `openssl rand -base64 24`>
#   DOMAIN=flowpilot.example.com
#   CADDY_EMAIL=you@example.com
#   (plus any external provider keys)
```

### DNS + security group

- Point an **A record** for `$DOMAIN` at the elastic IP.
- Open the following inbound ports in the EC2 security group:
  `22` (SSH from your IP), `80`, `443`. Do **not** open 5432/6379/8000.
- Caddy needs :80 reachable from the public internet for the initial HTTP-01
  challenge.

### Launch

```bash
make prod-up     # build images and start the full stack (detached)
make prod-logs   # tail logs (Ctrl-C to stop tailing)
make prod-down   # stop and remove containers
```

First-time boot takes a minute or two while Caddy requests a certificate.
After that you can hit `https://$DOMAIN` in the browser.

### Upgrading

```bash
git pull
make prod-up        # rebuilds only what changed
# or, to force a clean rebuild:
make prod-rebuild
```

### Notes

- The dev CORS allow-list in `backend/app/main.py` only trusts `localhost`.
  In the production setup this is fine because the browser calls the API via
  the same origin (`https://$DOMAIN/api/...`) that Caddy serves, so the
  browser never issues a cross-origin request. If you later split frontend
  and backend onto different domains, add the frontend origin there.
- Persistent data lives in the `postgres_data`, `caddy_data`, and
  `caddy_config` named volumes. Back them up (e.g. `docker run --rm
  -v flowpilot_postgres_data:/src -v "$PWD":/dst alpine tar czf
  /dst/pg.tgz -C /src .`) before instance migrations.
- If you need to inspect the DB on the server, don't re-open 5432. Instead:
  `docker compose -f infra/docker-compose.prod.yml exec postgres psql -U flowpilot`.

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

### Celery Workers & Beat

```bash
cd backend
# Engine worker — runs workflow/reporting/trigger tasks on the default
# "celery" queue:
uv run celery -A app.worker.celery_app worker --loglevel=info --queues=celery

# Action worker — subscribes only to the "actions" queue. Required when
# ACTION_WORKER_ENABLED=true; otherwise optional for local dev.
uv run celery -A app.worker.celery_app worker --loglevel=info --queues=actions -n action@%h

# In a separate terminal (for scheduled time triggers + calendar sync):
uv run celery -A app.worker.celery_app beat --loglevel=info
```

Or with the Make targets: `make worker-dev`, `make action-worker-dev`.

The engine worker consumes workflow jobs from Redis; Beat emits a heartbeat
every 60 seconds for time triggers and every 10 minutes for Google Calendar
sync.

## End-to-End Execution Pipeline

1. **Workflow authored** via `/api/workflows` (frontend builder). Trigger +
   steps are validated by the WorkflowService and persisted in Postgres.
2. **Activation** moves a workflow from `draft` → `active` and enables it.
3. **Triggering** happens in one of three ways:
   - Manual: `POST /api/workflows/{id}/run` (e.g. the Run button on the list
     page).
   - Time: Celery Beat runs `execution.tick_time_triggers` every minute; due
     triggers enqueue `execution.run_workflow`.
   - Webhook: `POST|GET|… /hooks/<path>` — the webhook router matches the
     request path+method to a registered webhook trigger and enqueues a run.
4. **Execution** (`app.execution.engine.ExecutionEngine`): transitions the
   `WorkflowRun` through `pending → running → success | failed`, iterates steps
   in `step_order`, resolves `{{...}}` templates against the running context
   (trigger + previous step outputs), dispatches to the registered action via
   `ActionRegistry`, and records a `WorkflowStepRun` per step.
5. **Observability**: `/api/workflows/{id}/runs` and
   `/api/workflows/{id}/runs/{run_id}/steps` expose run history + per-step
   logs. `/api/reports/monthly/{user}` aggregates monthly statistics.

## Auth

- `POST /api/users/register` and `POST /api/users/login` return a bearer token.
- Frontend stores the token in `localStorage` and attaches it as
  `Authorization: Bearer <token>` on every request.
- When a valid token is present, `POST /api/workflows` ignores any
  `owner_name` in the body and uses the authenticated user; `GET /api/workflows`
  returns only the caller's own workflows.

## Collaboration Workflow

- Create branches using `feat/...`, `fix/...`, or `chore/...`.
- Keep pull requests focused and small.
- Document setup/contract changes in README or `docs/`.
- Follow `docs/contributing.md` for team ownership and DoD.

## What Is Included

- User registration, login with bearer tokens, email management
- Workflow CRUD (create/list/get/update/delete)
- Workflow validation and activation
- Triggers: time-based (one-off + recurring), webhook, custom, and
  `calendar_event` (fires when a new event lands in the user's cached
  Google Calendar)
- Actions: `http_request`, `send_email`, `calendar_create_event`,
  `calendar_list_upcoming` (reads upcoming events from the local cache,
  no runtime Google call)
- End-to-end execution pipeline: manual runs, time-driven runs via Celery
  Beat, and webhook-driven runs via `/hooks/…`
- Per-run status (`pending/running/success/failed`) and per-step logs
- Monthly reporting endpoint with AI summary (OpenAI, with a fake fallback)
- AI workflow suggestions with LLM function calling
- **Google Calendar connector** (`app/connectors/google_calendar.py`):
  OAuth 2.0 flow under `/api/connectors/google/*`, real event creation
  when the workflow owner has linked their Google account, periodic sync
  of upcoming events into `cached_calendar_events` (Celery Beat task
  `connectors.sync_google_calendars`, every 10 minutes), and a mock
  fallback when the server is unconfigured or the user is not connected.
  Connect / disconnect / sync UI lives on its own **Dashboard →
  Integrations** page; cached events are filtered to upcoming-only by
  default so the list always answers "what's next" rather than showing
  last week's meetings. Powers both the `calendar_event` trigger (fire a
  workflow when a new event is detected) and the `calendar_list_upcoming`
  action (read the agenda inside a workflow without touching Google at
  runtime).
- **Strong ActionService process isolation** (`ACTION_WORKER_ENABLED=true`):
  the engine worker dispatches each step to a dedicated `actions` Celery
  queue served by the separate `action-worker` container. A crashing or
  OOM-ing action only takes that isolated worker down; the engine keeps
  processing other runs. Disabled in unit tests + single-process dev.
- Frontend: auth flow, workflow list with Run button + run history,
  workflow builder with drag-and-drop palette and AI chat.

## Known Limitations / Not Yet Implemented

- Fine-grained authorization: endpoints scope to the authenticated user but do
  not implement roles or shared workspaces.
- Alembic migrations: the DB applies `create_all` plus a few bespoke
  migrations in `app.db.session`. A proper Alembic setup is the next hardening
  step.
- Token encryption at rest: Google OAuth tokens are stored as plain text in
  `user_connections`. Production hardening should wrap them in Fernet with a
  KMS-managed key.
