"""structlog field redaction — D-27. IMPLEMENTED in Plan 01."""
from __future__ import annotations

import pytest

from app.logging.redaction import (
    REDACTED_PLACEHOLDER,
    redact_processor,
)

pytestmark = [pytest.mark.unit]


def test_redaction_replaces_all_seven_keys():
    """D-27: all 7 sensitive keys must be replaced with <redacted>."""
    event = {
        "msg": "login_attempt",
        "password": "s3cr3t",
        "password_hash": "$argon2id$v=19$...",
        "encrypted_key": b"\x00\x01\x02",
        "token": "scmcp_abc123",
        "token_hash": "deadbeef",
        "refresh_token": "opaque_refresh",
        "access_jwt": "eyJhbGciOiJIUzI1NiJ9...",
        "user_id": "u1",
        "ok": 1,
    }
    result = redact_processor(None, "info", event)
    assert result["password"] == REDACTED_PLACEHOLDER
    assert result["password_hash"] == REDACTED_PLACEHOLDER
    assert result["encrypted_key"] == REDACTED_PLACEHOLDER
    assert result["token"] == REDACTED_PLACEHOLDER
    assert result["token_hash"] == REDACTED_PLACEHOLDER
    assert result["refresh_token"] == REDACTED_PLACEHOLDER
    assert result["access_jwt"] == REDACTED_PLACEHOLDER
    assert result["user_id"] == "u1"
    assert result["ok"] == 1


def test_redaction_recurses_into_nested_dicts():
    """Secrets nested inside dicts are also redacted."""
    event = {
        "msg": "audit_detail",
        "request": {
            "token": "scmcp_nested",
            "password": "deep_secret",
            "safe_field": "visible",
        },
        "level": "info",
    }
    result = redact_processor(None, "info", event)
    assert result["request"]["token"] == REDACTED_PLACEHOLDER
    assert result["request"]["password"] == REDACTED_PLACEHOLDER
    assert result["request"]["safe_field"] == "visible"


def test_non_secret_keys_preserved():
    """Keys not in the D-27 list pass through unchanged."""
    event = {
        "msg": "user_login",
        "username": "alice",
        "ip": "10.0.0.1",
        "user_id": "alice-uuid",
        "count": 42,
    }
    result = redact_processor(None, "info", event)
    assert result["msg"] == "user_login"
    assert result["username"] == "alice"
    assert result["ip"] == "10.0.0.1"
    assert result["user_id"] == "alice-uuid"
    assert result["count"] == 42