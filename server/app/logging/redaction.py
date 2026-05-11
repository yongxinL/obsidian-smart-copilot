"""Field-level redaction processor for structlog (D-27).

The 7 keys MUST never appear in plaintext in any log sink:
  password, password_hash, encrypted_key, token, token_hash, refresh_token, access_jwt

The processor walks the event_dict, replaces matching keys with "<redacted>",
and recurses into dict values (audit_log details may nest secrets). It is the
FIRST processor in the chain — runs before the JSON renderer.
"""

from __future__ import annotations

from typing import Any

import structlog

REDACTED_KEYS: frozenset[str] = frozenset(
    {
        "password",
        "password_hash",
        "encrypted_key",
        "token",
        "token_hash",
        "refresh_token",
        "access_jwt",
    }
)
REDACTED_PLACEHOLDER = "<redacted>"


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: (REDACTED_PLACEHOLDER if k in REDACTED_KEYS else _redact(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def redact_processor(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:  # noqa: ARG001
    """structlog processor: redact D-27 keys at every nesting level."""
    for key in list(event_dict.keys()):
        if key in REDACTED_KEYS:
            event_dict[key] = REDACTED_PLACEHOLDER
        else:
            event_dict[key] = _redact(event_dict[key])
    return event_dict


def configure_logging() -> None:
    """Idempotent structlog configuration. Phase 1b minimal: redact + JSON renderer.

    CRITICAL: All log output goes to stderr to preserve MCP stdio stdout cleanliness.
    We use a custom processor that writes JSON to stderr so stdout remains pure JSON-RPC.
    """
    import sys

    def _write_json_to_stderr(
        logger: Any, method_name: str, event_dict: dict[str, Any]
    ) -> dict[str, Any]:  # noqa: ARG001
        """structlog processor: write JSON to stderr instead of stdout."""
        import json as _json

        _json.dump(event_dict, sys.stderr)
        sys.stderr.write("\n")
        sys.stderr.flush()
        # Don't pass to next processor — we already wrote the output
        raise structlog.DropEvent

    structlog.configure(
        processors=[
            redact_processor,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _write_json_to_stderr,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
        cache_logger_on_first_use=True,
    )
