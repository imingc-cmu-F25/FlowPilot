"""SuggestionContext — holds an active strategy and runs it."""

from __future__ import annotations

from app.suggestion.base import SuggestionResult, UserInput
from app.suggestion.strategies.base import SuggestionStrategy


class SuggestionContext:
    def __init__(self, strategy: SuggestionStrategy | None = None) -> None:
        self._strategy = strategy

    def set_strategy(self, strategy: SuggestionStrategy) -> None:
        self._strategy = strategy

    async def execute(self, user_input: UserInput) -> SuggestionResult:
        if self._strategy is None:
            raise RuntimeError("SuggestionContext has no active strategy")
        return await self._strategy.generate_suggestion(user_input)
