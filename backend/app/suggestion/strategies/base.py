"""SuggestionStrategy — the abstract Strategy interface."""

from abc import ABC, abstractmethod

from app.suggestion.base import SuggestionResult, UserInput


class SuggestionStrategy(ABC):
    """Abstract Strategy for generating workflow suggestions from user input."""

    @abstractmethod
    async def generate_suggestion(self, user_input: UserInput) -> SuggestionResult:
        """Produce a SuggestionResult for the given user input."""
        ...
