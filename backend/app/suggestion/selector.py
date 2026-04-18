"""StrategySelector — picks the best-fit strategy from an AnalysisResult."""

from __future__ import annotations

from app.suggestion.base import AnalysisResult
from app.suggestion.strategies.base import SuggestionStrategy
from app.suggestion.strategies.llm import LLMStrategy
from app.suggestion.strategies.rule_based import RuleBasedStrategy
from app.suggestion.strategies.template import TemplateStrategy

KNOWN_TEMPLATE_INPUT_TYPES = {"automation_request", "task_plan"}


class StrategySelector:
    def __init__(
        self,
        rule_based: SuggestionStrategy | None = None,
        template: SuggestionStrategy | None = None,
        llm: SuggestionStrategy | None = None,
    ) -> None:
        self._rule_based = rule_based or RuleBasedStrategy()
        self._template = template or TemplateStrategy()
        self._llm = llm or LLMStrategy()

    def select_strategy(self, analysis: AnalysisResult) -> SuggestionStrategy:
        if analysis.complexity_level == "simple" and analysis.confidence >= 0.8:
            return self._rule_based
        if analysis.input_type in KNOWN_TEMPLATE_INPUT_TYPES and analysis.confidence >= 0.7:
            return self._template
        return self._llm

    @property
    def llm_fallback(self) -> SuggestionStrategy:
        return self._llm
