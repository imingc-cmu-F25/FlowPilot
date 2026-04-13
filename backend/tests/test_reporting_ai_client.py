"""Unit tests for OpenAIAISummaryClient.

Mocks httpx at the module boundary so tests never touch the network.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import httpx
import pytest
from app.reporting.ai_client import OpenAIAISummaryClient
from app.reporting.filters.ai_summary import AISummaryFilter
from app.reporting.pipeline import PipeData
from app.reporting.report import AggregatedMetrics


def _fake_response(json_body: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_body
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


def _patched_client(response: MagicMock) -> MagicMock:
    """Build a MagicMock that mimics `httpx.Client()` as a context manager."""
    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = False
    client.post.return_value = response
    return client


def test_rejects_empty_api_key():
    with pytest.raises(ValueError, match="non-empty api_key"):
        OpenAIAISummaryClient(api_key="")


def test_summarize_returns_content_from_openai_response():
    response = _fake_response({
        "choices": [{"message": {"content": "  3 runs, all succeeded.  "}}]
    })
    fake_client = _patched_client(response)

    with patch("app.reporting.ai_client.httpx.Client", return_value=fake_client):
        result = OpenAIAISummaryClient(api_key="sk-test").summarize(
            {"total_runs": 3, "success_rate": 1.0}
        )

    assert result == "3 runs, all succeeded."
    fake_client.post.assert_called_once()
    call = fake_client.post.call_args
    assert call.kwargs["headers"]["Authorization"] == "Bearer sk-test"
    payload = call.kwargs["json"]
    assert payload["model"] == "gpt-4o-mini"
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["role"] == "user"
    assert "total_runs" in payload["messages"][1]["content"]


def test_summarize_propagates_http_error_status():
    response = _fake_response({"error": "bad"}, status_code=500)
    fake_client = _patched_client(response)

    with patch("app.reporting.ai_client.httpx.Client", return_value=fake_client):
        with pytest.raises(httpx.HTTPStatusError):
            OpenAIAISummaryClient(api_key="sk-test").summarize({"total_runs": 0})


def test_summarize_propagates_network_error():
    fake_client = MagicMock()
    fake_client.__enter__.return_value = fake_client
    fake_client.__exit__.return_value = False
    fake_client.post.side_effect = httpx.ConnectError("down")

    with patch("app.reporting.ai_client.httpx.Client", return_value=fake_client):
        with pytest.raises(httpx.ConnectError):
            OpenAIAISummaryClient(api_key="sk-test").summarize({"total_runs": 0})


def test_ai_summary_filter_swallows_openai_failure():
    """Belt-and-braces: the existing filter fallback should still catch
    real OpenAI client errors end-to-end."""
    fake_client = MagicMock()
    fake_client.__enter__.return_value = fake_client
    fake_client.__exit__.return_value = False
    fake_client.post.side_effect = httpx.ConnectError("down")

    with patch("app.reporting.ai_client.httpx.Client", return_value=fake_client):
        client = OpenAIAISummaryClient(api_key="sk-test")
        data = PipeData(
            owner_name="a",
            period_start=datetime(2026, 3, 1, tzinfo=UTC),
            period_end=datetime(2026, 3, 31, tzinfo=UTC),
            aggregated_metrics=AggregatedMetrics(total_runs=1),
        )
        result = AISummaryFilter(client).process(data)

    assert result.ai_summary == "AI summary unavailable: ConnectError"


def test_default_ai_client_picks_fake_when_no_api_key():
    from app.reporting.ai_client import FakeAISummaryClient
    from app.reporting.service import _default_ai_client

    with patch("app.reporting.service.settings") as mock_settings:
        mock_settings.openai_api_key = ""
        assert isinstance(_default_ai_client(), FakeAISummaryClient)


def test_default_ai_client_picks_openai_when_key_present():
    from app.reporting.service import _default_ai_client

    with patch("app.reporting.service.settings") as mock_settings:
        mock_settings.openai_api_key = "sk-whatever"
        client = _default_ai_client()
        assert isinstance(client, OpenAIAISummaryClient)
