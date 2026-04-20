"""Integration tests for the workflow API endpoints."""

from uuid import uuid4

import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture(autouse=True)
def ensure_owner_user() -> None:
    response = client.post(
        "/api/users/register",
        json={
            "name": "test-owner",
            "password": "password123",
            "email": "test-owner@example.com",
        },
    )
    assert response.status_code in (200, 409)


#  Shared payload builders


def schedule_payload(**overrides) -> dict:
    base = {
        "owner_name": "test-owner",
        "name": "Test Workflow",
        "description": "A test",
        "trigger": {
            "type": "time",
            "parameters": {"trigger_at": "2026-05-01T09:00:00+00:00"},
        },
        "steps": [
            {
                "action_type": "send_email",
                "name": "Send report",
                "step_order": 0,
                "parameters": {
                    "to_template": "a@b.com",
                    "subject_template": "Report",
                    "body_template": "Hello",
                },
            }
        ],
        "enabled": False,
    }
    base.update(overrides)
    return base


def webhook_payload(**overrides) -> dict:
    base = schedule_payload()
    base["trigger"] = {
        "type": "webhook",
        "parameters": {"path": "/hooks/test"},
    }
    base.update(overrides)
    return base


def create_workflow(**overrides) -> dict:
    """Helper: POST a workflow and return the response JSON."""
    r = client.post("/api/workflows", json=schedule_payload(**overrides))
    assert r.status_code == 201, r.json()
    return r.json()


#  POST /workflows
class TestCreateWorkflow:
    def test_returns_201(self):
        r = client.post("/api/workflows", json=schedule_payload())
        assert r.status_code == 201

    def test_response_contains_workflow_id(self):
        data = create_workflow()
        assert "workflow_id" in data

    def test_response_contains_name(self):
        data = create_workflow(name="My WF")
        assert data["name"] == "My WF"

    def test_response_status_is_draft(self):
        data = create_workflow()
        assert data["status"] == "draft"

    def test_response_trigger_type_matches(self):
        data = create_workflow()
        assert data["trigger"]["type"] == "time"

    def test_webhook_trigger_stored(self):
        r = client.post("/api/workflows", json=webhook_payload())
        assert r.status_code == 201
        assert r.json()["trigger"]["type"] == "webhook"

    def test_invalid_trigger_type_returns_422(self):
        payload = schedule_payload()
        payload["trigger"]["type"] = "nonexistent"
        r = client.post("/api/workflows", json=payload)
        assert r.status_code == 422

    def test_missing_name_returns_422(self):
        payload = schedule_payload()
        del payload["name"]
        r = client.post("/api/workflows", json=payload)
        assert r.status_code == 422

    def test_step_with_missing_required_param_returns_422(self):
        payload = schedule_payload()
        payload["steps"][0]["parameters"] = {}  # missing to_template etc.
        r = client.post("/api/workflows", json=payload)
        assert r.status_code == 422


#  GET /workflows
class TestListWorkflows:
    def test_empty_list_initially(self):
        r = client.get("/api/workflows")
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_created_workflows(self):
        login_r = client.post(
            "/api/users/login", json={"name": "test-owner", "password": "password123"}
        )
        token = login_r.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        create_workflow(name="WF1")
        create_workflow(name="WF2")
        r = client.get("/api/workflows", headers=headers)
        assert r.status_code == 200
        names = {w["name"] for w in r.json()}
        assert "WF1" in names
        assert "WF2" in names

    def test_returns_list_type(self):
        r = client.get("/api/workflows")
        assert isinstance(r.json(), list)


#  GET /workflows/{wf_id}
class TestGetWorkflow:
    def test_returns_workflow_by_id(self):
        created = create_workflow(name="Fetch Me")
        wf_id = created["workflow_id"]
        r = client.get(f"/api/workflows/{wf_id}")
        assert r.status_code == 200
        assert r.json()["name"] == "Fetch Me"

    def test_unknown_id_returns_404(self):
        r = client.get(f"/api/workflows/{uuid4()}")
        assert r.status_code == 404

    def test_response_includes_trigger(self):
        created = create_workflow()
        wf_id = created["workflow_id"]
        r = client.get(f"/api/workflows/{wf_id}")
        assert "trigger" in r.json()

    def test_response_includes_steps(self):
        created = create_workflow()
        wf_id = created["workflow_id"]
        r = client.get(f"/api/workflows/{wf_id}")
        assert len(r.json()["steps"]) == 1


#  PUT /workflows/{wf_id}
class TestUpdateWorkflow:
    def test_update_name(self):
        created = create_workflow(name="Old Name")
        wf_id = created["workflow_id"]
        r = client.put(f"/api/workflows/{wf_id}", json={"name": "New Name"})
        assert r.status_code == 200
        assert r.json()["name"] == "New Name"

    def test_update_description(self):
        created = create_workflow()
        wf_id = created["workflow_id"]
        r = client.put(f"/api/workflows/{wf_id}", json={"description": "Updated"})
        assert r.status_code == 200
        assert r.json()["description"] == "Updated"

    def test_update_preserves_unspecified_fields(self):
        created = create_workflow(name="Keep Me")
        wf_id = created["workflow_id"]
        r = client.put(f"/api/workflows/{wf_id}", json={"description": "X"})
        assert r.json()["name"] == "Keep Me"

    def test_unknown_id_returns_404(self):
        r = client.put(f"/api/workflows/{uuid4()}", json={"name": "X"})
        assert r.status_code == 404

    def test_update_trigger(self):
        created = create_workflow()
        wf_id = created["workflow_id"]
        r = client.put(
            f"/api/workflows/{wf_id}",
            json={"trigger": {"type": "webhook", "parameters": {"path": "/hooks/new"}}},
        )
        assert r.status_code == 200
        assert r.json()["trigger"]["type"] == "webhook"


#  DELETE /workflows/{wf_id}
class TestDeleteWorkflow:
    def test_returns_204(self):
        created = create_workflow()
        wf_id = created["workflow_id"]
        r = client.delete(f"/api/workflows/{wf_id}")
        assert r.status_code == 204

    def test_deleted_workflow_is_gone(self):
        created = create_workflow()
        wf_id = created["workflow_id"]
        client.delete(f"/api/workflows/{wf_id}")
        r = client.get(f"/api/workflows/{wf_id}")
        assert r.status_code == 404

    def test_delete_unknown_id_returns_204(self):
        # idempotent delete
        r = client.delete(f"/api/workflows/{uuid4()}")
        assert r.status_code == 204


#  POST /workflows/{wf_id}/validate
class TestValidateEndpoint:
    def test_valid_workflow_returns_valid_true(self):
        created = create_workflow()
        wf_id = created["workflow_id"]
        r = client.post(f"/api/workflows/{wf_id}/validate")
        assert r.status_code == 200
        body = r.json()
        assert body["valid"] is True
        assert body["errors"] == []

    def test_unknown_id_returns_404(self):
        r = client.post(f"/api/workflows/{uuid4()}/validate")
        assert r.status_code == 404

    def test_response_has_errors_key(self):
        created = create_workflow()
        r = client.post(f"/api/workflows/{created['workflow_id']}/validate")
        assert "errors" in r.json()


#  POST /workflows/{wf_id}/activate
class TestActivateEndpoint:
    def test_valid_workflow_activates_successfully(self):
        created = create_workflow()
        wf_id = created["workflow_id"]
        r = client.post(f"/api/workflows/{wf_id}/activate")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "active"
        assert data["enabled"] is True

    def test_unknown_id_returns_404(self):
        r = client.post(f"/api/workflows/{uuid4()}/activate")
        assert r.status_code == 404

    def test_activated_workflow_persisted(self):
        created = create_workflow()
        wf_id = created["workflow_id"]
        client.post(f"/api/workflows/{wf_id}/activate")
        r = client.get(f"/api/workflows/{wf_id}")
        assert r.json()["status"] == "active"


#  GET /registry/actions
class TestRegistryEndpoints:
    def test_list_actions_returns_200(self):
        r = client.get("/api/registry/actions")
        assert r.status_code == 200

    def test_list_actions_contains_send_email(self):
        r = client.get("/api/registry/actions")
        ids = [a["id"] for a in r.json()]
        assert "send_email" in ids

    def test_list_actions_contains_http_request(self):
        r = client.get("/api/registry/actions")
        ids = [a["id"] for a in r.json()]
        assert "http_request" in ids

    def test_list_triggers_returns_200(self):
        r = client.get("/api/registry/triggers")
        assert r.status_code == 200

    def test_list_triggers_contains_time(self):
        r = client.get("/api/registry/triggers")
        ids = [t["id"] for t in r.json()]
        assert "time" in ids

    def test_list_triggers_contains_webhook(self):
        r = client.get("/api/registry/triggers")
        ids = [t["id"] for t in r.json()]
        assert "webhook" in ids


# GET /hooks/{hook_path:path}
class TestWebhookIngest:
    def test_matching_enabled_webhook_emits_run(self, monkeypatch):
        # create enabled webhook workflow
        r = client.post(
            "/api/workflows",
            json=webhook_payload(
                enabled=True,
                trigger={
                    "type": "webhook",
                    "parameters": {"path": "/hooks/test", "method": "POST"},
                },
            ),
        )
        assert r.status_code == 201, r.json()
        wf_id = r.json()["workflow_id"]

        monkeypatch.setattr(
            "app.trigger.service.enqueue_execute_run",
            lambda _run_id: None,
        )

        # ingest webhook
        ingest = client.post("/api/hooks/test")
        assert ingest.status_code == 200
        body = ingest.json()
        assert body["matched_workflows"] >= 1
        assert body["emitted_runs"] >= 1

        # verify run exists
        runs = client.get(f"/api/workflows/{wf_id}/runs")
        assert runs.status_code == 200
        assert any(run["trigger_type"] == "webhook" for run in runs.json())

    def test_non_matching_path_emits_nothing(self):
        r = client.post(
            "/api/workflows",
            json=webhook_payload(
                enabled=True,
                trigger={"type": "webhook", "parameters": {"path": "/hooks/a", "method": "POST"}},
            ),
        )
        assert r.status_code == 201, r.json()

        ingest = client.post("/api/hooks/b")
        assert ingest.status_code == 200
        body = ingest.json()
        assert body["matched_workflows"] == 0
        assert body["emitted_runs"] == 0

    def test_disabled_workflow_not_emitted(self):
        r = client.post(
            "/api/workflows",
            json=webhook_payload(
                enabled=False,
                trigger={"type": "webhook", "parameters": {"path": "/hooks/off", "method": "POST"}},
            ),
        )
        assert r.status_code == 201, r.json()

        ingest = client.post("/api/hooks/off")
        assert ingest.status_code == 200
        body = ingest.json()
        assert body["matched_workflows"] == 0
        assert body["emitted_runs"] == 0


# POST|PUT /workflows — webhook path uniqueness
class TestWebhookPathUniqueness:
    """Two enabled webhook workflows must never share the same
    (path, method). Otherwise a single incoming request fans out to
    both owners, which is a cross-tenant correctness bug.
    """

    def test_second_enabled_webhook_on_same_path_is_rejected(self):
        r1 = client.post(
            "/api/workflows",
            json=webhook_payload(
                enabled=True,
                trigger={
                    "type": "webhook",
                    "parameters": {"path": "/hooks/shared", "method": "POST"},
                },
            ),
        )
        assert r1.status_code == 201, r1.json()

        r2 = client.post(
            "/api/workflows",
            json=webhook_payload(
                enabled=True,
                trigger={
                    "type": "webhook",
                    "parameters": {"path": "/hooks/shared", "method": "POST"},
                },
            ),
        )
        assert r2.status_code == 409, r2.json()
        detail = r2.json()["detail"]
        assert "already" in detail["message"].lower()
        assert detail["errors"][0]["field"] == "trigger.path"

    def test_disabled_second_webhook_on_same_path_is_allowed(self):
        """Disabled workflows don't route HTTP traffic, so they can
        happily share a path with an enabled one — enabling them later
        is what re-runs the check.
        """
        client.post(
            "/api/workflows",
            json=webhook_payload(
                enabled=True,
                trigger={
                    "type": "webhook",
                    "parameters": {"path": "/hooks/shared2", "method": "POST"},
                },
            ),
        )
        r2 = client.post(
            "/api/workflows",
            json=webhook_payload(
                enabled=False,
                trigger={
                    "type": "webhook",
                    "parameters": {"path": "/hooks/shared2", "method": "POST"},
                },
            ),
        )
        assert r2.status_code == 201, r2.json()

    def test_enabling_a_colliding_workflow_later_is_rejected(self):
        r1 = client.post(
            "/api/workflows",
            json=webhook_payload(
                enabled=True,
                trigger={
                    "type": "webhook",
                    "parameters": {"path": "/hooks/shared3", "method": "POST"},
                },
            ),
        )
        assert r1.status_code == 201

        r2 = client.post(
            "/api/workflows",
            json=webhook_payload(
                enabled=False,
                trigger={
                    "type": "webhook",
                    "parameters": {"path": "/hooks/shared3", "method": "POST"},
                },
            ),
        )
        wf2_id = r2.json()["workflow_id"]

        # Flipping the second to enabled would now collide.
        r3 = client.put(f"/api/workflows/{wf2_id}", json={"enabled": True})
        assert r3.status_code == 409, r3.json()

    def test_different_methods_on_same_path_do_not_collide(self):
        r1 = client.post(
            "/api/workflows",
            json=webhook_payload(
                enabled=True,
                trigger={
                    "type": "webhook",
                    "parameters": {"path": "/hooks/mixed", "method": "POST"},
                },
            ),
        )
        assert r1.status_code == 201

        r2 = client.post(
            "/api/workflows",
            json=webhook_payload(
                enabled=True,
                trigger={
                    "type": "webhook",
                    "parameters": {"path": "/hooks/mixed", "method": "GET"},
                },
            ),
        )
        assert r2.status_code == 201, r2.json()

    def test_updating_own_workflow_does_not_self_collide(self):
        """A workflow must not collide with itself when it re-saves the same path."""
        r1 = client.post(
            "/api/workflows",
            json=webhook_payload(
                enabled=True,
                trigger={"type": "webhook", "parameters": {"path": "/hooks/own", "method": "POST"}},
            ),
        )
        wf_id = r1.json()["workflow_id"]

        # Re-saving with the same path should succeed (exclude-self).
        r2 = client.put(
            f"/api/workflows/{wf_id}",
            json={
                "trigger": {
                    "type": "webhook",
                    "parameters": {"path": "/hooks/own", "method": "POST"},
                }
            },
        )
        assert r2.status_code == 200, r2.json()
