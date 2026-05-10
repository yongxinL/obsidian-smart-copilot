"""structlog redaction processor — D-27 (T-1b-10).

These tests are IMPLEMENTED in Plan 01 (not stubbed) — they validate Task 01-03
in this same plan. Every other auth test relies on D-27 redaction to prevent
secret leakage in test logs.
"""

from __future__ import annotations

import pytest

from app.logging.redaction import REDACTED_KEYS, REDACTED_PLACEHOLDER, redact_processor

pytestmark = [pytest.mark.unit, pytest.mark.auth]


def test_redaction_replaces_all_seven_keys() -> None:
    """All 7 D-27 keys at the top level are replaced with the placeholder."""
    event_dict = {
        "msg": "auth event",
        "password": "p@ss",
        "password_hash": "$argon2id$...",
        "encrypted_key": b"\x80\x00",
        "token": "scmcp_xxx",
        "token_hash": "deadbeef",
        "refresh_token": "rtok_yyy",
        "access_jwt": "eyJhbGciOi...",
        "user_id": "u1",
    }
    out = redact_processor(None, "info", event_dict)
    for key in REDACTED_KEYS:
        assert out[key] == REDACTED_PLACEHOLDER, f"{key} not redacted at top level"
    # Non-secret key preserved
    assert out["msg"] == "auth event"
    assert out["user_id"] == "u1"


def test_redaction_recurses_into_nested_dicts() -> None:
    """Secrets nested inside dict / list values are redacted at every level."""
    event_dict = {
        "msg": "audit",
        "details": {
            "token": "scmcp_inner",
            "ok": True,
            "deeper": {"refresh_token": "deep_secret", "user_id": "u2"},
            "list_of_dicts": [
                {"password": "leak", "ok": "keep"},
                {"safe": 1},
            ],
        },
    }
    out = redact_processor(None, "info", event_dict)
    assert out["msg"] == "audit"
    assert out["details"]["token"] == REDACTED_PLACEHOLDER
    assert out["details"]["ok"] is True
    assert out["details"]["deeper"]["refresh_token"] == REDACTED_PLACEHOLDER
    assert out["details"]["deeper"]["user_id"] == "u2"
    assert out["details"]["list_of_dicts"][0]["password"] == REDACTED_PLACEHOLDER
    assert out["details"]["list_of_dicts"][0]["ok"] == "keep"
    assert out["details"]["list_of_dicts"][1]["safe"] == 1


def test_non_secret_keys_preserved() -> None:
    """No false positives — non-secret keys + scalar values pass through unchanged."""
    event_dict = {
        "event": "login_success",
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "ip": "10.0.0.1",
        "request_id": "req-abc",
        "duration_ms": 42,
        "tags": ["auth", "rest"],
    }
    out = redact_processor(None, "info", event_dict)
    assert out == {
        "event": "login_success",
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "ip": "10.0.0.1",
        "request_id": "req-abc",
        "duration_ms": 42,
        "tags": ["auth", "rest"],
    }
