from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_register_returns_success_message() -> None:
    r = client.post("/api/users/register", json={"name": "alice", "password": "secret"})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["message"] == "Registration successful"
    assert data["user"] == {"name": "alice", "emails": []}
    assert data["token"] is None


def test_register_duplicate_returns_409() -> None:
    body = {"name": "bob", "password": "p1"}
    assert client.post("/api/users/register", json=body).status_code == 200
    r2 = client.post("/api/users/register", json=body)
    assert r2.status_code == 409
    assert r2.json()["detail"] == "Username already registered"


def test_login_success_returns_auth_response_and_token_tuple() -> None:
    client.post("/api/users/register", json={"name": "carol", "password": "pw"})
    r = client.post("/api/users/login", json={"name": "carol", "password": "pw"})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert data[0]["ok"] is True
    assert data[0]["message"] == "Login successful"
    assert data[0]["user"] == {"name": "carol", "emails": []}
    assert data[0]["token"] is None
    assert isinstance(data[1], str)
    assert data[1]


def test_login_wrong_password_returns_400() -> None:
    client.post("/api/users/register", json={"name": "dave", "password": "right"})
    r = client.post("/api/users/login", json={"name": "dave", "password": "wrong"})
    assert r.status_code == 400
    assert r.json()["detail"] == "Invalid username or password"


def test_login_unknown_user_returns_400() -> None:
    r = client.post("/api/users/login", json={"name": "nobody", "password": "x"})
    assert r.status_code == 400
    assert r.json()["detail"] == "Invalid username or password"


def test_list_users_empty() -> None:
    r = client.get("/api/users/users")
    assert r.status_code == 200
    assert r.json() == []


def test_list_users_returns_all_without_passwords() -> None:
    client.post("/api/users/register", json={"name": "zebra", "password": "a"})
    client.post("/api/users/register", json={"name": "amy", "password": "b"})
    r = client.get("/api/users/users")
    assert r.status_code == 200
    assert r.json() == [
        {"name": "amy", "emails": []},
        {"name": "zebra", "emails": []},
    ]
    for row in r.json():
        assert "password" not in row
