"""Integration tests for the reports API endpoints."""

import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture(autouse=True)
def ensure_owner_user() -> None:
    response = client.post(
        "/api/users/register",
        json={
            "name": "report-owner",
            "password": "password123",
            "email": "report-owner@example.com",
        },
    )
    assert response.status_code in (200, 409)


def _generate_body(**overrides) -> dict:
    base = {
        "owner_name": "report-owner",
        "period_start": "2026-03-01T00:00:00+00:00",
        "period_end": "2026-03-31T23:59:59+00:00",
    }
    base.update(overrides)
    return base


def test_generate_report_returns_201_and_payload():
    response = client.post("/api/reports/generate", json=_generate_body())
    assert response.status_code == 201
    data = response.json()
    assert data["owner_name"] == "report-owner"
    assert data["status"] == "completed"
    assert data["metrics"]["total_runs"] == 0
    assert "report_id" in data


def test_get_report_by_id():
    created = client.post("/api/reports/generate", json=_generate_body()).json()
    response = client.get(f"/api/reports/{created['report_id']}")
    assert response.status_code == 200
    assert response.json()["report_id"] == created["report_id"]


def test_list_reports_for_owner():
    client.post("/api/reports/generate", json=_generate_body())
    client.post("/api/reports/generate", json=_generate_body(
        period_start="2026-02-01T00:00:00+00:00",
        period_end="2026-02-28T23:59:59+00:00",
    ))
    response = client.get("/api/reports", params={"owner_name": "report-owner"})
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_generate_report_unknown_owner_returns_404():
    response = client.post(
        "/api/reports/generate",
        json=_generate_body(owner_name="nobody"),
    )
    assert response.status_code == 404


def test_get_report_unknown_id_returns_404():
    response = client.get("/api/reports/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_list_reports_unknown_owner_returns_404():
    response = client.get("/api/reports", params={"owner_name": "nobody"})
    assert response.status_code == 404


def test_generate_report_invalid_period_returns_422():
    response = client.post(
        "/api/reports/generate",
        json=_generate_body(
            period_start="2026-03-31T00:00:00+00:00",
            period_end="2026-03-01T00:00:00+00:00",
        ),
    )
    assert response.status_code == 422
