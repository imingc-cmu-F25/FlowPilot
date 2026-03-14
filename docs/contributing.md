# Contributing Guide

## Branching

- Use feature branches from `main`.
- Naming suggestion: `feat/<area>-<short-description>`, `fix/<area>-<short-description>`.

## Commit Messages

- Prefer conventional style:
  - `feat: ...`
  - `fix: ...`
  - `docs: ...`
  - `chore: ...`

## Pull Requests

- Keep each PR focused on one concern.
- Include:
  - What changed
  - Why it changed
  - How to test it

## Team Responsibility Split (initial)

- Frontend team: `frontend/src/features/*`, `frontend/src/pages/*`.
- API team: `backend/app/api/*`, `backend/app/core/*`.
- Workflow/Execution team: `backend/app/workflow/*`, `backend/app/trigger/*`, `backend/app/execution/*`.
- Integrations/Reporting team: `backend/app/action/*`, `backend/app/reporting/*`, `backend/app/connectors/*`.

## Definition of Done

- Lint passes for changed area.
- Basic tests added/updated when behavior changes.
- README/docs updated for changes in setup, env vars, or architecture.
