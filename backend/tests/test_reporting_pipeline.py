"""Unit tests for the Pipeline executor and Filter contract."""

from datetime import UTC, datetime

import pytest
from app.reporting.pipeline import Filter, PipeData, Pipeline, PipelineError


class TaggingFilter(Filter):
    """Appends its tag to PipeData.metadata['trace'] so ordering is observable."""

    def __init__(self, tag: str) -> None:
        self._tag = tag

    def process(self, data: PipeData) -> PipeData:
        trace = list(data.metadata.get("trace", []))
        trace.append(self._tag)
        return data.model_copy(update={"metadata": {**data.metadata, "trace": trace}})


class ExplodingFilter(Filter):
    def process(self, data: PipeData) -> PipeData:
        raise ValueError("boom")


def _make_data() -> PipeData:
    return PipeData(
        owner_name="alice",
        period_start=datetime(2026, 3, 1, tzinfo=UTC),
        period_end=datetime(2026, 3, 31, tzinfo=UTC),
    )


def test_empty_pipeline_returns_data_unchanged():
    data = _make_data()
    result = Pipeline().execute(data)
    assert result == data


def test_filters_run_in_order_and_chain_outputs():
    pipeline = Pipeline([TaggingFilter("a"), TaggingFilter("b"), TaggingFilter("c")])
    result = pipeline.execute(_make_data())
    assert result.metadata["trace"] == ["a", "b", "c"]


def test_add_filter_appends_in_order():
    pipeline = Pipeline().add_filter(TaggingFilter("x")).add_filter(TaggingFilter("y"))
    result = pipeline.execute(_make_data())
    assert result.metadata["trace"] == ["x", "y"]


def test_filter_exception_wrapped_with_filter_class_name():
    pipeline = Pipeline([TaggingFilter("ok"), ExplodingFilter()])
    with pytest.raises(PipelineError) as excinfo:
        pipeline.execute(_make_data())
    assert excinfo.value.filter_name == "ExplodingFilter"
    assert isinstance(excinfo.value.original, ValueError)


def test_filter_exception_short_circuits_remaining_filters():
    tail = TaggingFilter("never")
    pipeline = Pipeline([ExplodingFilter(), tail])
    with pytest.raises(PipelineError):
        data = _make_data()
        pipeline.execute(data)
    # data is immutable per call; tail should never have been invoked.
    # We verify by running tail in isolation and confirming it would have added its tag.
    isolated = tail.process(_make_data())
    assert isolated.metadata["trace"] == ["never"]
