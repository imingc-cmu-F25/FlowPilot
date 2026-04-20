"""Authentication / filtering helpers for the webhook trigger.

The ``secret_ref`` field on WebhookTriggerConfig is overloaded so the
single field can drive multiple auth schemes without bloating the
config. Prefix-based dispatch:

- ``""``              → no auth (accept any caller)
- ``"slack:<secret>"`` → verify Slack's v0 signing scheme
- anything else       → generic HMAC-SHA256(body) compared against the
                         ``X-Signature-SHA256`` header, in ``<hex>`` or
                         ``sha256=<hex>`` form

Kept in its own module so the router stays thin and so we can unit
test the crypto without spinning up FastAPI.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class AuthOutcome:
    ok: bool
    # Human-readable reason for the audit log / 401 body. Kept short
    # on purpose: the webhook caller sees this verbatim, and we don't
    # want to leak which header or which timestamp we rejected.
    reason: str = ""


def verify_webhook_auth(
    secret_ref: str,
    raw_body: bytes,
    headers: dict[str, str],
    *,
    now: float | None = None,
) -> AuthOutcome:
    """Return an AuthOutcome for the given (secret_ref, request) pair.

    ``headers`` must be lower-cased keys (the caller already normalises
    when it hands us the dict). ``now`` is injectable for tests.
    """

    if not secret_ref:
        return AuthOutcome(ok=True, reason="no-auth-configured")

    if secret_ref.startswith("slack:"):
        return _verify_slack(
            secret=secret_ref[len("slack:"):],
            raw_body=raw_body,
            headers=headers,
            now=now if now is not None else time.time(),
        )

    return _verify_generic_hmac(
        secret=secret_ref,
        raw_body=raw_body,
        headers=headers,
    )


def _verify_slack(
    secret: str,
    raw_body: bytes,
    headers: dict[str, str],
    now: float,
) -> AuthOutcome:
    """Validate a Slack-signed request using Slack's v0 scheme.

    See https://api.slack.com/authentication/verifying-requests-from-slack.
    The signature is ``v0=HMAC_SHA256(secret, f"v0:{ts}:{body}")``. We
    also enforce a 5-minute freshness window to mitigate replay.
    """

    if not secret:
        # User configured "slack:" with an empty secret. Fail closed —
        # a blank Slack secret would otherwise accept anyone's v0= hash
        # over the same body.
        return AuthOutcome(ok=False, reason="missing Slack signing secret")

    timestamp = headers.get("x-slack-request-timestamp", "")
    signature = headers.get("x-slack-signature", "")
    if not timestamp or not signature:
        return AuthOutcome(ok=False, reason="missing Slack signature headers")

    try:
        ts_int = int(timestamp)
    except ValueError:
        return AuthOutcome(ok=False, reason="invalid Slack timestamp")

    if abs(now - ts_int) > 60 * 5:
        return AuthOutcome(ok=False, reason="stale Slack request")

    base = f"v0:{timestamp}:".encode() + raw_body
    expected = "v0=" + hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return AuthOutcome(ok=False, reason="bad Slack signature")

    return AuthOutcome(ok=True, reason="slack-verified")


def _verify_generic_hmac(
    secret: str,
    raw_body: bytes,
    headers: dict[str, str],
) -> AuthOutcome:
    """Validate HMAC-SHA256(body) against ``X-Signature-SHA256``.

    Accepts bare hex (``deadbeef…``) or the GitHub-style ``sha256=…``
    prefix for convenience, so the same secret can front both shapes
    without a second field.
    """

    provided = headers.get("x-signature-sha256", "")
    if not provided:
        return AuthOutcome(ok=False, reason="missing X-Signature-SHA256 header")

    if provided.startswith("sha256="):
        provided = provided[len("sha256="):]

    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, provided):
        return AuthOutcome(ok=False, reason="bad signature")

    return AuthOutcome(ok=True, reason="hmac-verified")
