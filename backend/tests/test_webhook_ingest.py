"""End-to-end tests for the /hooks ingress.

Exercises the features added for Slack-style integration:
- payload capture into workflow_runs.trigger_context
- Slack signature verification driven by secret_ref=slack:<secret>
- event_filter / header_filters enforcement
- Slack slash command friendly response
- engine seeds step 1's previous_output from trigger_context
"""

import hashlib
import hmac
from uuid import UUID

import pytest
from app.db.session import new_session
from app.execution.engine import ExecutionEngine
from app.main import app
from app.workflow.run_repo import WorkflowRunRepository
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture(autouse=True)
def ensure_owner_user() -> None:
    response = client.post(
        "/api/users/register",
        json={
            "name": "hook-owner",
            "password": "password123",
            "email": "hook-owner@example.com",
        },
    )
    assert response.status_code in (200, 409)


def _webhook_workflow(**trigger_overrides) -> str:
    """Create an enabled webhook workflow and return its id."""
    trigger_params = {"path": "/hooks/slack", "method": "POST"}
    trigger_params.update(trigger_overrides)
    r = client.post(
        "/api/workflows",
        json={
            "owner_name": "hook-owner",
            "name": "Webhook WF",
            "description": "",
            "trigger": {"type": "webhook", "parameters": trigger_params},
            "steps": [
                {
                    "action_type": "send_email",
                    "name": "Noop",
                    "step_order": 0,
                    "parameters": {
                        "to_template": "a@b.com",
                        "subject_template": "s",
                        "body_template": "b",
                    },
                }
            ],
            "enabled": True,
        },
    )
    assert r.status_code == 201, r.json()
    return r.json()["workflow_id"]


def _latest_run_context(workflow_id: str) -> dict | None:
    db = new_session()
    try:
        runs = WorkflowRunRepository(db).list_for_workflow(UUID(workflow_id), limit=1)
    finally:
        db.close()
    if not runs:
        return None
    return runs[0].trigger_context


class TestPayloadCapture:
    def test_json_body_captured_and_parsed(self, monkeypatch):
        monkeypatch.setattr(
            "app.trigger.service.enqueue_execute_run", lambda _run_id: None
        )
        wf_id = _webhook_workflow()

        r = client.post(
            "/api/hooks/slack",
            json={"user": "alice", "text": "review"},
            headers={"X-Trace-Id": "abc-123"},
        )
        assert r.status_code == 200
        assert r.json()["emitted_runs"] == 1

        ctx = _latest_run_context(wf_id)
        assert ctx is not None
        assert ctx["source"] == "webhook"
        assert ctx["path"] == "/hooks/slack"
        assert ctx["method"] == "POST"
        assert ctx["body"] == {"user": "alice", "text": "review"}
        # Headers are lower-cased and include the custom one we set.
        assert ctx["headers"]["x-trace-id"] == "abc-123"

    def test_form_encoded_body_parsed_as_flat_dict(self, monkeypatch):
        monkeypatch.setattr(
            "app.trigger.service.enqueue_execute_run", lambda _run_id: None
        )
        wf_id = _webhook_workflow()

        r = client.post(
            "/api/hooks/slack",
            data={
                "token": "xoxb",
                "user_name": "alice",
                "text": "block focus 30m",
                "command": "/block",
            },
        )
        assert r.status_code == 200

        ctx = _latest_run_context(wf_id)
        assert ctx is not None
        assert ctx["body"]["user_name"] == "alice"
        assert ctx["body"]["text"] == "block focus 30m"
        assert ctx["body"]["command"] == "/block"

    def test_authorization_header_redacted(self, monkeypatch):
        monkeypatch.setattr(
            "app.trigger.service.enqueue_execute_run", lambda _run_id: None
        )
        wf_id = _webhook_workflow()

        r = client.post(
            "/api/hooks/slack",
            json={},
            headers={"Authorization": "Bearer super-secret"},
        )
        assert r.status_code == 200

        ctx = _latest_run_context(wf_id)
        assert ctx is not None
        assert "authorization" not in ctx["headers"]


class TestSlackSignature:
    SECRET = "signing_secret"

    @staticmethod
    def _sign(secret: str, ts: str, body: bytes) -> str:
        base = f"v0:{ts}:".encode() + body
        return "v0=" + hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()

    def test_rejects_unsigned_slack_configured_workflow(self, monkeypatch):
        monkeypatch.setattr(
            "app.trigger.service.enqueue_execute_run", lambda _run_id: None
        )
        _webhook_workflow(secret_ref=f"slack:{self.SECRET}")

        r = client.post("/api/hooks/slack", data={"user_name": "alice"})
        assert r.status_code == 401

    def test_accepts_valid_slack_signature(self, monkeypatch):
        monkeypatch.setattr(
            "app.trigger.service.enqueue_execute_run", lambda _run_id: None
        )
        _webhook_workflow(secret_ref=f"slack:{self.SECRET}")

        body = b"user_name=alice&text=hi&command=%2Fblock"
        # Use server "now" (we can't inject it through HTTP); just
        # craft a fresh timestamp so the 5-minute window is satisfied.
        import time as _time
        ts = str(int(_time.time()))
        sig = self._sign(self.SECRET, ts, body)

        r = client.post(
            "/api/hooks/slack",
            content=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Slack-Request-Timestamp": ts,
                "X-Slack-Signature": sig,
            },
        )
        assert r.status_code == 200
        # Slack-style response, not the regular JSON summary.
        assert r.json()["response_type"] == "ephemeral"
        assert "workflow" in r.json()["text"].lower()

    def test_bad_signature_returns_401(self, monkeypatch):
        monkeypatch.setattr(
            "app.trigger.service.enqueue_execute_run", lambda _run_id: None
        )
        _webhook_workflow(secret_ref=f"slack:{self.SECRET}")

        import time as _time
        ts = str(int(_time.time()))
        r = client.post(
            "/api/hooks/slack",
            content=b"anything",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Slack-Request-Timestamp": ts,
                "X-Slack-Signature": "v0=deadbeef",
            },
        )
        assert r.status_code == 401


class TestFilters:
    def test_event_filter_blocks_non_matching(self, monkeypatch):
        monkeypatch.setattr(
            "app.trigger.service.enqueue_execute_run", lambda _run_id: None
        )
        _webhook_workflow(event_filter="push")

        r = client.post("/api/hooks/slack", json={}, headers={"X-Event-Type": "ping"})
        assert r.status_code == 200
        assert r.json()["emitted_runs"] == 0
        assert r.json()["skipped_filter"] == 1

    def test_event_filter_accepts_matching(self, monkeypatch):
        monkeypatch.setattr(
            "app.trigger.service.enqueue_execute_run", lambda _run_id: None
        )
        _webhook_workflow(event_filter="push")

        r = client.post("/api/hooks/slack", json={}, headers={"X-Event-Type": "push"})
        assert r.status_code == 200
        assert r.json()["emitted_runs"] == 1


class TestSlackFriendlyResponse:
    def test_slack_signed_header_triggers_ephemeral_reply(self, monkeypatch):
        monkeypatch.setattr(
            "app.trigger.service.enqueue_execute_run", lambda _run_id: None
        )
        _webhook_workflow()  # no secret; request still looks like Slack

        # Any value in X-Slack-Signature flips the response shape, even
        # without a configured secret (handy for development where the
        # user wants the Slack-ish reply without wiring up auth yet).
        r = client.post(
            "/api/hooks/slack",
            data={"text": "hi"},
            headers={"X-Slack-Signature": "v0=whatever",
                     "X-Slack-Request-Timestamp": "0"},
        )
        assert r.status_code == 200
        assert r.json()["response_type"] == "ephemeral"


class TestEngineSeedsTriggerContext:
    """The engine should pass run.trigger_context as step 1's previous_output."""

    def test_first_step_sees_webhook_body(self, monkeypatch):
        from unittest.mock import patch

        monkeypatch.setattr(
            "app.trigger.service.enqueue_execute_run", lambda _run_id: None
        )

        wf_id = _webhook_workflow(path="/hooks/capture")
        payload = {"user_name": "alice", "text": "review"}
        r = client.post("/api/hooks/capture", json=payload)
        assert r.status_code == 200, r.json()

        # Drive the engine synchronously against the emitted run so we
        # can observe what inputs the step actually received.
        captured: dict[str, dict] = {}

        def _fake_dispatch(step, inputs):  # pragma: no cover — trivial
            captured["inputs"] = inputs
            return {"ok": True}

        db = new_session()
        try:
            runs = WorkflowRunRepository(db).list_for_workflow(UUID(wf_id), limit=1)
            assert runs, "expected a run to have been emitted"
            run_id = runs[0].run_id

            with patch(
                "app.execution.engine.dispatch_action_step",
                side_effect=_fake_dispatch,
            ):
                ExecutionEngine(db).execute(run_id)
            db.commit()
        finally:
            db.close()

        prev = captured["inputs"].get("previous_output") or {}
        assert prev.get("source") == "webhook"
        assert prev.get("body") == payload
        # Headers are lower-cased and available for templating.
        assert "content-type" in prev["headers"]
