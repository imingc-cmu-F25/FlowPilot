"""Tests for the Custom Trigger dry-run helper and HTTP endpoint.

These cover the happy path (valid expression → ok/true/false),
whitelist enforcement (attribute access / function calls → error),
and the empty-condition / syntax-error cases that the builder UI
needs to render inline.
"""

from app.main import app
from app.trigger.customTrigger import AVAILABLE_VARIABLES, dry_run_condition
from fastapi.testclient import TestClient


def test_dry_run_true_literal_reports_ok_true():
    report = dry_run_condition("true")
    assert report["ok"] is True
    assert report["value"] is True
    assert report["error"] is None


def test_dry_run_false_literal_reports_ok_false():
    report = dry_run_condition("false")
    assert report["ok"] is True
    assert report["value"] is False


def test_dry_run_comparison_evaluates_against_live_clock():
    # 1 < 2 is a clock-independent truth, keeps the test deterministic.
    report = dry_run_condition("1 < 2")
    assert report["ok"] is True
    assert report["value"] is True


def test_dry_run_rejects_attribute_access():
    report = dry_run_condition("__import__('os').getcwd()")
    assert report["ok"] is False
    assert report["value"] is None
    assert report["error"]  # non-empty human-readable reason


def test_dry_run_rejects_unknown_name():
    report = dry_run_condition("foobar == 1")
    assert report["ok"] is False
    assert "foobar" in (report["error"] or "").lower()


def test_dry_run_reports_syntax_error():
    report = dry_run_condition("1 +")
    assert report["ok"] is False
    assert "syntax" in (report["error"] or "").lower()


def test_dry_run_empty_condition():
    report = dry_run_condition("   ")
    assert report["ok"] is False
    assert "empty" in (report["error"] or "").lower()


def test_dry_run_env_contains_expected_variables():
    report = dry_run_condition("true")
    env = report["env"]
    for name in ("hour", "minute", "weekday", "day", "month", "year", "now", "source"):
        assert name in env


def test_endpoint_returns_report_and_catalogue():
    client = TestClient(app)
    res = client.post(
        "/api/triggers/custom/evaluate",
        json={"condition": "hour >= 0 and hour <= 23"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["value"] is True
    # Catalogue echoed for the builder hint block; every entry has
    # name+description so the UI can render without any fallback.
    assert len(data["available_variables"]) == len(AVAILABLE_VARIABLES)
    assert all("name" in v and "description" in v for v in data["available_variables"])


def test_endpoint_surfaces_evaluation_error():
    client = TestClient(app)
    res = client.post(
        "/api/triggers/custom/evaluate",
        json={"condition": "weekday.attr"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert data["error"]


def test_dry_run_respects_explicit_timezone():
    """The 'hour' variable must reflect the configured zone, not UTC.

    We pick two zones that are guaranteed to straddle a different hour
    at any instant (Asia/Taipei is UTC+8, no DST; Pacific/Honolulu is
    UTC-10, no DST). Their hour readings differ by 18 modulo 24 — so
    they can never both show the same hour value simultaneously, giving
    us a deterministic cross-check without mocking the clock.
    """
    taipei = dry_run_condition("true", timezone="Asia/Taipei")
    honolulu = dry_run_condition("true", timezone="Pacific/Honolulu")
    assert taipei["ok"] is True
    assert honolulu["ok"] is True
    assert taipei["env"]["hour"] != honolulu["env"]["hour"]
    assert taipei["env"]["timezone"] == "Asia/Taipei"
    assert honolulu["env"]["timezone"] == "Pacific/Honolulu"


def test_dry_run_falls_back_to_utc_on_unknown_timezone():
    report = dry_run_condition("true", timezone="Not/A_Real_Zone")
    assert report["ok"] is True
    assert report["env"]["timezone"] == "UTC"


def test_endpoint_accepts_timezone_field():
    client = TestClient(app)
    res = client.post(
        "/api/triggers/custom/evaluate",
        json={"condition": "hour >= 0", "timezone": "Asia/Taipei"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["env"]["timezone"] == "Asia/Taipei"
