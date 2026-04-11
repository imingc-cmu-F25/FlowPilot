"""Persists workflow run state transitions — single place for DB writes from execution."""

from uuid import UUID

from app.workflow.run_repo import WorkflowRunRepository


class RunStatePersister:
    """Wraps WorkflowRunRepository for the execution engine (State pattern collaborator)."""

    def __init__(self, repo: WorkflowRunRepository, run_id: UUID) -> None:
        self._repo = repo
        self._run_id = run_id

    def persist_success(self, output: dict | None) -> None:
        self._repo.mark_success(self._run_id, output)

    def persist_failed(self, error: str) -> None:
        self._repo.mark_failed(self._run_id, error)

    def persist_retrying(self, retry_count: int) -> None:
        self._repo.mark_retrying(self._run_id, retry_count)

    def persist_running_after_retry(self) -> None:
        self._repo.mark_running_from_retry(self._run_id)
