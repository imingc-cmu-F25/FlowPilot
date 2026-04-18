"""Unit tests for StrategySelector routing logic."""

from app.suggestion.base import AnalysisResult
from app.suggestion.selector import StrategySelector
from app.suggestion.strategies.llm import LLMStrategy
from app.suggestion.strategies.rule_based import RuleBasedStrategy
from app.suggestion.strategies.template import TemplateStrategy


def test_selector_picks_rule_based_for_simple_high_confidence():
    selector = StrategySelector()
    analysis = AnalysisResult(
        complexity_level="simple", input_type="automation_request", confidence=0.9
    )
    strategy = selector.select_strategy(analysis)
    assert isinstance(strategy, RuleBasedStrategy)


def test_selector_picks_template_for_known_input_type_medium_confidence():
    selector = StrategySelector()
    analysis = AnalysisResult(
        complexity_level="medium", input_type="automation_request", confidence=0.75
    )
    strategy = selector.select_strategy(analysis)
    assert isinstance(strategy, TemplateStrategy)


def test_selector_falls_back_to_llm_for_low_confidence():
    selector = StrategySelector()
    analysis = AnalysisResult(
        complexity_level="complex", input_type="other", confidence=0.3
    )
    strategy = selector.select_strategy(analysis)
    assert isinstance(strategy, LLMStrategy)


def test_selector_falls_back_to_llm_when_simple_but_low_confidence():
    selector = StrategySelector()
    analysis = AnalysisResult(
        complexity_level="simple", input_type="automation_request", confidence=0.5
    )
    strategy = selector.select_strategy(analysis)
    assert isinstance(strategy, LLMStrategy)
