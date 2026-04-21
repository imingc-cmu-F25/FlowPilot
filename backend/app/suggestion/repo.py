"""SuggestionRepository — persists and retrieves Suggestion rows."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.schema import SuggestionORM
from app.suggestion.base import AnalysisResult, SuggestionResult, UserInput


class SuggestionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def save(
        self,
        user_input: UserInput,
        analysis: AnalysisResult,
        result: SuggestionResult,
    ) -> SuggestionORM:
        orm = SuggestionORM(
            id=uuid.uuid4(),
            user_name=user_input.user_name or "anonymous",
            raw_text=user_input.raw_text,
            strategy_used=result.strategy_used,
            analysis=analysis.model_dump(mode="json"),
            content=result.content,
            workflow_draft=result.workflow_draft,
            pending_questions=[q.model_dump() for q in result.pending_questions],
            created_at=datetime.now(UTC),
            accepted_workflow_id=None,
        )
        self._db.add(orm)
        self._db.flush()
        return orm

    def get(self, suggestion_id: uuid.UUID) -> SuggestionORM | None:
        return self._db.get(SuggestionORM, suggestion_id)

    def list_for_user(self, user_name: str) -> list[SuggestionORM]:
        return (
            self._db.query(SuggestionORM)
            .filter(SuggestionORM.user_name == user_name)
            .order_by(SuggestionORM.created_at.desc())
            .all()
        )

    def mark_accepted(self, suggestion_id: uuid.UUID, workflow_id: uuid.UUID) -> None:
        orm = self._db.get(SuggestionORM, suggestion_id)
        if orm is None:
            return
        orm.accepted_workflow_id = workflow_id
        self._db.flush()
