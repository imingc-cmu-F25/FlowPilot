"""SuggestionService — orchestrates Analyzer → Selector → Strategy → Rephraser → Repo."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.schema import SuggestionORM
from app.suggestion.analyzer import AIAnalyzer
from app.suggestion.base import UserInput
from app.suggestion.context import SuggestionContext
from app.suggestion.rephraser import AIRephraser
from app.suggestion.repo import SuggestionRepository
from app.suggestion.selector import StrategySelector


class SuggestionService:
    def __init__(
        self,
        db: Session,
        analyzer: AIAnalyzer | None = None,
        selector: StrategySelector | None = None,
        context: SuggestionContext | None = None,
        rephraser: AIRephraser | None = None,
    ) -> None:
        self._analyzer = analyzer or AIAnalyzer()
        self._selector = selector or StrategySelector()
        self._context = context or SuggestionContext()
        self._rephraser = rephraser or AIRephraser()
        self._repo = SuggestionRepository(db)

    async def suggest(self, user_input: UserInput) -> SuggestionORM:
        analysis = await self._analyzer.analyze(user_input)
        strategy = self._selector.select_strategy(analysis)
        self._context.set_strategy(strategy)
        result = await self._context.execute(user_input)

        # Fallback: if non-LLM strategy returns no draft, re-route to LLM.
        if result.workflow_draft is None and result.strategy_used != "llm":
            self._context.set_strategy(self._selector.llm_fallback)
            result = await self._context.execute(user_input)

        polished = await self._rephraser.rephrase(result)
        return self._repo.save(user_input, analysis, polished)

    @property
    def repo(self) -> SuggestionRepository:
        return self._repo
