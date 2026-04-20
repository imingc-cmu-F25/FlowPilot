"""Unit tests for app.trigger.webhook_auth.

These exercise the pure crypto / verification helpers in isolation so
the integration tests for the HTTP route stay focused on the plumbing.
"""

import hashlib
import hmac
import time

from app.trigger.webhook_auth import verify_webhook_auth


def _slack_sign(secret: str, timestamp: str, body: bytes) -> str:
    base = f"v0:{timestamp}:".encode() + body
    return "v0=" + hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()


class TestNoAuth:
    def test_empty_secret_ref_accepts_everything(self):
        outcome = verify_webhook_auth(
            secret_ref="",
            raw_body=b"anything",
            headers={},
        )
        assert outcome.ok is True


class TestSlackAuth:
    SECRET = "s3cr3t"
    BODY = b"token=abc&user_name=alice&text=hello"

    def test_valid_slack_signature_passes(self):
        now = 1_700_000_000.0
        ts = str(int(now))
        headers = {
            "x-slack-request-timestamp": ts,
            "x-slack-signature": _slack_sign(self.SECRET, ts, self.BODY),
        }
        outcome = verify_webhook_auth(
            secret_ref=f"slack:{self.SECRET}",
            raw_body=self.BODY,
            headers=headers,
            now=now,
        )
        assert outcome.ok is True
        assert "slack" in outcome.reason

    def test_bad_signature_rejected(self):
        now = 1_700_000_000.0
        ts = str(int(now))
        headers = {
            "x-slack-request-timestamp": ts,
            "x-slack-signature": "v0=deadbeef",
        }
        outcome = verify_webhook_auth(
            secret_ref=f"slack:{self.SECRET}",
            raw_body=self.BODY,
            headers=headers,
            now=now,
        )
        assert outcome.ok is False
        assert "signature" in outcome.reason.lower()

    def test_stale_request_rejected(self):
        now = 1_700_000_000.0
        # 10 minutes old > Slack's 5-minute replay window
        stale_ts = str(int(now) - 60 * 10)
        headers = {
            "x-slack-request-timestamp": stale_ts,
            "x-slack-signature": _slack_sign(self.SECRET, stale_ts, self.BODY),
        }
        outcome = verify_webhook_auth(
            secret_ref=f"slack:{self.SECRET}",
            raw_body=self.BODY,
            headers=headers,
            now=now,
        )
        assert outcome.ok is False
        assert "stale" in outcome.reason.lower()

    def test_missing_headers_rejected(self):
        outcome = verify_webhook_auth(
            secret_ref=f"slack:{self.SECRET}",
            raw_body=self.BODY,
            headers={},
            now=time.time(),
        )
        assert outcome.ok is False

    def test_empty_slack_secret_fails_closed(self):
        outcome = verify_webhook_auth(
            secret_ref="slack:",
            raw_body=self.BODY,
            headers={"x-slack-signature": "v0=abc", "x-slack-request-timestamp": "0"},
            now=0.0,
        )
        assert outcome.ok is False


class TestGenericHmacAuth:
    SECRET = "shared"
    BODY = b'{"event":"ping"}'

    def _sig(self) -> str:
        return hmac.new(self.SECRET.encode(), self.BODY, hashlib.sha256).hexdigest()

    def test_valid_hex_signature_passes(self):
        outcome = verify_webhook_auth(
            secret_ref=self.SECRET,
            raw_body=self.BODY,
            headers={"x-signature-sha256": self._sig()},
        )
        assert outcome.ok is True

    def test_sha256_prefixed_signature_passes(self):
        outcome = verify_webhook_auth(
            secret_ref=self.SECRET,
            raw_body=self.BODY,
            headers={"x-signature-sha256": f"sha256={self._sig()}"},
        )
        assert outcome.ok is True

    def test_missing_header_rejected(self):
        outcome = verify_webhook_auth(
            secret_ref=self.SECRET,
            raw_body=self.BODY,
            headers={},
        )
        assert outcome.ok is False

    def test_wrong_signature_rejected(self):
        outcome = verify_webhook_auth(
            secret_ref=self.SECRET,
            raw_body=self.BODY,
            headers={"x-signature-sha256": "a" * 64},
        )
        assert outcome.ok is False
