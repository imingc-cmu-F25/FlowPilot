from app.main import app
from fastapi.testclient import TestClient


def test_healthcheck() -> None:
    client = TestClient(app)
    response = client.get("/api/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
