SHELL := /bin/bash

COMPOSE_DEV  := docker compose -f infra/docker-compose.yml
COMPOSE_PROD := docker compose --env-file .env -f infra/docker-compose.prod.yml

.PHONY: up down logs frontend-dev backend-dev worker-dev \
        ci ci-frontend ci-backend \
        prod-up prod-down prod-logs prod-restart prod-rebuild

up:
	$(COMPOSE_DEV) up --build -d --remove-orphans

down:
	$(COMPOSE_DEV) down --remove-orphans

logs:
	$(COMPOSE_DEV) logs -f --tail=200

# ---- Production (EC2) ----

prod-up:
	$(COMPOSE_PROD) up --build -d --remove-orphans

prod-down:
	$(COMPOSE_PROD) down --remove-orphans

prod-logs:
	$(COMPOSE_PROD) logs -f --tail=200

prod-restart:
	$(COMPOSE_PROD) restart

prod-rebuild:
	$(COMPOSE_PROD) build --no-cache && $(COMPOSE_PROD) up -d --remove-orphans

frontend-dev:
	cd frontend && npm run dev

backend-dev:
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

worker-dev:
	cd backend && uv run celery -A app.worker.celery_app worker --loglevel=info

ci-frontend:
	cd frontend && npm ci && npm run lint && npm run build

ci-backend:
	cd backend && uv sync --all-groups && uv run ruff check . && uv run pytest

ci: ci-frontend ci-backend
