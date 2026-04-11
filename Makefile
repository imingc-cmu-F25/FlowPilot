SHELL := /bin/bash

.PHONY: up down logs frontend-dev backend-dev worker-dev

up:
	docker compose -f infra/docker-compose.yml up --build -d --remove-orphans

down:
	docker compose -f infra/docker-compose.yml down --remove-orphans

logs:
	docker compose -f infra/docker-compose.yml logs -f --tail=200

frontend-dev:
	cd frontend && npm run dev

backend-dev:
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

worker-dev:
	cd backend && uv run celery -A app.worker.celery_app worker --loglevel=info
