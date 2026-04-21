"""Integration tests for /api/suggestions endpoints."""

import uuid

import pytest
from app.db.session import new_session
from app.main import app
from app.suggestion.repo import SuggestionRepository
from fastapi.testclient import TestClient

client = TestClient(app)


def _alice_auth_headers() -> dict:
    """Log in as alice (registered by the autouse fixture) and return Bearer.

    /api/suggestions/* now requires auth (get_current_user), so every test
    must attach a token. Re-issued per call since the in-memory session
    table is dropped between tests by conftest.
    """
    r = client.post(
        "/api/users/login",
        json={"name": "alice", "password": "password123"},
    )
    assert r.status_code == 200, r.json()
    body = r.json()
    token = body.get("token") if isinstance(body, dict) else body[1]
    return {"Authorization": f"Bearer {token}"}


def _create_workflow_for_alice() -> str:
    """Helper: POST a minimal valid workflow owned by alice and return its id."""
    payload = {
        "owner_name": "alice",
        "name": "Linked WF",
        "description": "",
        "trigger": {
            "type": "time",
            "parameters": {"trigger_at": "2030-01-01T09:00:00+00:00"},
        },
        "steps": [
            {
                "action_type": "send_email",
                "name": "Send",
                "step_order": 0,
                "parameters": {
                    "to_template": "a@b.com",
                    "subject_template": "S",
                    "body_template": "B",
                },
            }
        ],
        "enabled": False,
    }
    res = client.post("/api/workflows", json=payload)
    assert res.status_code == 201, res.json()
    return res.json()["workflow_id"]


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
        headers=_alice_auth_headers(),
    )
    assert res.status_code == 201
    body = res.json()
    assert body["strategy_used"] == "rule_based"
    assert body["workflow_draft"] is not None
    assert body["workflow_draft"]["trigger"]["type"] == "time"


def test_create_suggestion_without_token_returns_401():
    res = client.post(
        "/api/suggestions",
        json={"raw_text": "daily email to a@b.com"},
    )
    assert res.status_code == 401


def test_list_suggestions_returns_user_history():
    headers = _alice_auth_headers()
    client.post(
        "/api/suggestions",
        json={"raw_text": "daily email to a@b.com", "user_name": "alice"},
        headers=headers,
    )
    res = client.get("/api/suggestions?user_name=alice", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)
    assert len(res.json()) >= 1


def test_get_suggestion_by_id():
    headers = _alice_auth_headers()
    create_res = client.post(
        "/api/suggestions",
        json={"raw_text": "daily email to a@b.com", "user_name": "alice"},
        headers=headers,
    )
    sid = create_res.json()["id"]
    res = client.get(f"/api/suggestions/{sid}", headers=headers)
    assert res.status_code == 200
    assert res.json()["id"] == sid


def test_accept_suggestion_returns_draft():
    headers = _alice_auth_headers()
    create_res = client.post(
        "/api/suggestions",
        json={"raw_text": "daily email to a@b.com", "user_name": "alice"},
        headers=headers,
    )
    sid = create_res.json()["id"]
    res = client.post(f"/api/suggestions/{sid}/accept", headers=headers)
    assert res.status_code == 200
    assert res.json()["workflow_draft"] is not None


def test_accept_rejects_draft_with_invalid_trigger():
    """The accept endpoint must surface bad trigger config as 422 instead of
    happily handing the user a draft that /api/workflows would later reject."""
    headers = _alice_auth_headers()
    create_res = client.post(
        "/api/suggestions",
        json={"raw_text": "daily email to a@b.com", "user_name": "alice"},
        headers=headers,
    )
    sid = create_res.json()["id"]

    # Mutate the stored draft to carry a bad cron expression.
    db = new_session()
    try:
        orm = SuggestionRepository(db).get(uuid.UUID(sid))
        bad_draft = dict(orm.workflow_draft or {})
        bad_draft["trigger"] = {
            "type": "time",
            "trigger_at": "2030-01-01T09:00:00+00:00",
            "timezone": "UTC",
            "recurrence": {
                "frequency": "custom",
                "interval": 1,
                "days_of_week": [],
                "cron_expression": "not a cron",
            },
        }
        orm.workflow_draft = bad_draft
        db.commit()
    finally:
        db.close()

    res = client.post(f"/api/suggestions/{sid}/accept", headers=headers)
    assert res.status_code == 422
    assert "trigger" in str(res.json()["detail"]).lower()


def test_accept_link_records_workflow_id():
    """End-to-end: create a suggestion, create a workflow, then link them
    via /accept/link and confirm accepted_workflow_id is persisted."""
    headers = _alice_auth_headers()
    create_res = client.post(
        "/api/suggestions",
        json={"raw_text": "daily email to a@b.com", "user_name": "alice"},
        headers=headers,
    )
    sid = create_res.json()["id"]

    wf_id = _create_workflow_for_alice()

    link_res = client.post(
        f"/api/suggestions/{sid}/accept/link",
        json={"workflow_id": wf_id},
        headers=headers,
    )
    assert link_res.status_code == 200, link_res.json()
    assert link_res.json()["accepted_workflow_id"] == wf_id

    # Confirm persistence by re-reading the suggestion through the GET path.
    get_res = client.get(f"/api/suggestions/{sid}", headers=headers)
    assert get_res.json()["accepted_workflow_id"] == wf_id


def test_accept_link_unknown_workflow_returns_404():
    headers = _alice_auth_headers()
    create_res = client.post(
        "/api/suggestions",
        json={"raw_text": "daily email to a@b.com", "user_name": "alice"},
        headers=headers,
    )
    sid = create_res.json()["id"]

    res = client.post(
        f"/api/suggestions/{sid}/accept/link",
        json={"workflow_id": str(uuid.uuid4())},
        headers=headers,
    )
    assert res.status_code == 404
