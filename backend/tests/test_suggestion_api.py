"""Integration tests for /api/suggestions endpoints."""

import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture(autouse=True)
def ensure_user() -> None:
    response = client.post(
        "/api/users/register",
        json={"name": "alice", "password": "password123", "email": "alice@acme.com"},
    )
    assert response.status_code in (200, 409)


@pytest.fixture(autouse=True)
def disable_openai(monkeypatch):
    from app.suggestion import openai_client as oc

    oc._cached_client = None
    oc._cached_key = None
    monkeypatch.setattr("app.core.config.settings.openai_api_key", "")
    yield
    oc._cached_client = None
    oc._cached_key = None


def test_create_suggestion_returns_draft_for_daily_email():
    res = client.post(
        "/api/suggestions",
        json={
            "raw_text": "Send a daily email at 9am to ops@acme.com",
            "user_name": "alice",
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["strategy_used"] == "rule_based"
    assert body["workflow_draft"] is not None
    assert body["workflow_draft"]["trigger"]["type"] == "time"


def test_list_suggestions_returns_user_history():
    client.post(
        "/api/suggestions",
        json={"raw_text": "daily email to a@b.com", "user_name": "alice"},
    )
    res = client.get("/api/suggestions?user_name=alice")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
    assert len(res.json()) >= 1


def test_get_suggestion_by_id():
    create_res = client.post(
        "/api/suggestions",
        json={"raw_text": "daily email to a@b.com", "user_name": "alice"},
    )
    sid = create_res.json()["id"]
    res = client.get(f"/api/suggestions/{sid}")
    assert res.status_code == 200
    assert res.json()["id"] == sid


def test_accept_suggestion_returns_draft():
    create_res = client.post(
        "/api/suggestions",
        json={"raw_text": "daily email to a@b.com", "user_name": "alice"},
    )
    sid = create_res.json()["id"]
    res = client.post(f"/api/suggestions/{sid}/accept")
    assert res.status_code == 200
    assert res.json()["workflow_draft"] is not None
