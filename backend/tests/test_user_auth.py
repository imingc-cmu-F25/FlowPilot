from app.api.router import SESSION_COOKIE_NAME
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_register_returns_201_with_message() -> None:
    r = client.post("/api/auth/register", json={"name": "alice", "password": "secret"})
    assert r.status_code == 201
    data = r.json()
    assert data["ok"] is True
    assert data["message"] == "Registration successful"
    assert data["user"] == {"name": "alice"}
    assert data["token"] is None


def test_register_duplicate_returns_409_with_message() -> None:
    body = {"name": "bob", "password": "p1"}
    assert client.post("/api/auth/register", json=body).status_code == 201
    r2 = client.post("/api/auth/register", json=body)
    assert r2.status_code == 409
    data = r2.json()
    assert data["ok"] is False
    assert data["message"] == "Username already registered"
    assert data["user"] is None
    assert data["token"] is None


def test_login_success_sets_cookie_and_returns_token() -> None:
    client.post("/api/auth/register", json={"name": "carol", "password": "pw"})
    r = client.post("/api/auth/login", json={"name": "carol", "password": "pw"})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["message"] == "Login successful"
    assert data["user"] == {"name": "carol"}
    assert data["token"]
    assert r.cookies.get(SESSION_COOKIE_NAME) == data["token"]


def test_login_wrong_password_returns_401_with_message() -> None:
    client.post("/api/auth/register", json={"name": "dave", "password": "right"})
    r = client.post("/api/auth/login", json={"name": "dave", "password": "wrong"})
    assert r.status_code == 401
    data = r.json()
    assert data["ok"] is False
    assert data["message"] == "Invalid username or password"
    assert data["user"] is None
    assert data["token"] is None


def test_login_unknown_user_returns_401_with_message() -> None:
    r = client.post("/api/auth/login", json={"name": "nobody", "password": "x"})
    assert r.status_code == 401
    data = r.json()
    assert data["ok"] is False
    assert data["message"] == "Invalid username or password"


def test_list_users_empty() -> None:
    r = client.get("/api/users")
    assert r.status_code == 200
    assert r.json() == []


def test_list_users_returns_all_without_passwords() -> None:
    client.post("/api/auth/register", json={"name": "zebra", "password": "a"})
    client.post("/api/auth/register", json={"name": "amy", "password": "b"})
    r = client.get("/api/users")
    assert r.status_code == 200
    assert r.json() == [{"name": "amy"}, {"name": "zebra"}]
    for row in r.json():
        assert "password" not in row
