"""Authorization scoping: authenticated callers cannot access other users' data.

These tests lock in the behavior added by enforce_workflow_access /
enforce_run_access / enforce_owner_match: once a caller supplies a bearer
token, cross-user reads/writes are hidden behind 404 (to avoid leaking ids).
"""

from uuid import uuid4

import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def _register(name: str) -> None:
    r = client.post(
        "/api/users/register",
        json={"name": name, "password": "password123", "email": f"{name}@example.com"},
    )
    assert r.status_code in (200, 409)


def _login(name: str) -> str:
    r = client.post("/api/users/login", json={"name": name, "password": "password123"})
    assert r.status_code == 200, r.json()
    token = r.json()["token"]
    assert token
    return token


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _schedule_payload(owner: str) -> dict:
    return {
        "owner_name": owner,
        "name": "WF",
        "description": "",
        "trigger": {
            "type": "time",
            "parameters": {"trigger_at": "2026-05-01T09:00:00+00:00"},
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


@pytest.fixture
def two_users() -> tuple[str, str]:
    _register("alice-scoped")
    _register("bob-scoped")
    return _login("alice-scoped"), _login("bob-scoped")


class TestWorkflowScoping:
    def test_other_user_cannot_get_workflow(self, two_users):
        alice_token, bob_token = two_users
        created = client.post(
            "/api/workflows",
            json=_schedule_payload("alice-scoped"),
            headers=_auth(alice_token),
        )
        wf_id = created.json()["workflow_id"]

        r = client.get(f"/api/workflows/{wf_id}", headers=_auth(bob_token))
        assert r.status_code == 404

    def test_other_user_cannot_update_workflow(self, two_users):
        alice_token, bob_token = two_users
        wf_id = client.post(
            "/api/workflows",
            json=_schedule_payload("alice-scoped"),
            headers=_auth(alice_token),
        ).json()["workflow_id"]

        r = client.put(
            f"/api/workflows/{wf_id}",
            json={"name": "pwned"},
            headers=_auth(bob_token),
        )
        assert r.status_code == 404

    def test_other_user_delete_is_noop(self, two_users):
        alice_token, bob_token = two_users
        wf_id = client.post(
            "/api/workflows",
            json=_schedule_payload("alice-scoped"),
            headers=_auth(alice_token),
        ).json()["workflow_id"]

        r = client.delete(f"/api/workflows/{wf_id}", headers=_auth(bob_token))
        assert r.status_code == 204
        # Workflow must still exist from alice's perspective.
        assert (
            client.get(f"/api/workflows/{wf_id}", headers=_auth(alice_token)).status_code
            == 200
        )

    def test_list_is_scoped_to_authenticated_user(self, two_users):
        alice_token, bob_token = two_users
        client.post(
            "/api/workflows",
            json=_schedule_payload("alice-scoped"),
            headers=_auth(alice_token),
        )
        bob_list = client.get("/api/workflows", headers=_auth(bob_token)).json()
        assert all(wf["owner_name"] == "bob-scoped" for wf in bob_list)


class TestReportScoping:
    def test_cannot_generate_report_for_other_user(self, two_users):
        _alice_token, bob_token = two_users
        r = client.post(
            "/api/reports/generate",
            json={
                "owner_name": "alice-scoped",
                "period_start": "2026-03-01T00:00:00+00:00",
                "period_end": "2026-03-31T23:59:59+00:00",
            },
            headers=_auth(bob_token),
        )
        assert r.status_code == 404

    def test_cannot_list_other_users_reports(self, two_users):
        _alice_token, bob_token = two_users
        r = client.get(
            "/api/reports",
            params={"owner_name": "alice-scoped"},
            headers=_auth(bob_token),
        )
        assert r.status_code == 404


class TestUnknownIds:
    def test_unknown_workflow_still_404_when_authed(self, two_users):
        alice_token, _ = two_users
        r = client.get(f"/api/workflows/{uuid4()}", headers=_auth(alice_token))
        assert r.status_code == 404
