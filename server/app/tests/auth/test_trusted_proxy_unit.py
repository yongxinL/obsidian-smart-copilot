"""AUTH-08 unit tests — TrustedProxyMiddleware D-29 logic."""

from __future__ import annotations

import pytest

from app.auth.middleware import TrustedProxyMiddleware

pytestmark = [pytest.mark.auth, pytest.mark.unit]


def _scope(*, peer: str, xff: str | None = None) -> dict:
    headers = []
    if xff:
        headers.append((b"x-forwarded-for", xff.encode()))
    return {"type": "http", "client": (peer, 12345), "headers": headers}


def test_leftmost_xff_chosen() -> None:
    mw = TrustedProxyMiddleware(
        app=None, trust_proxy=True, allowlist_cidrs=["10.0.0.0/8"]
    )
    scope = _scope(peer="10.0.0.5", xff="203.0.113.10, 198.51.100.1")
    assert mw._resolve_client_ip(scope) == "203.0.113.10"


def test_xff_ignored_when_trust_disabled() -> None:
    mw = TrustedProxyMiddleware(
        app=None, trust_proxy=False, allowlist_cidrs=["10.0.0.0/8"]
    )
    scope = _scope(peer="10.0.0.5", xff="203.0.113.10")
    assert mw._resolve_client_ip(scope) == "10.0.0.5"


def test_xff_ignored_when_peer_not_in_allowlist() -> None:
    mw = TrustedProxyMiddleware(
        app=None, trust_proxy=True, allowlist_cidrs=["10.0.0.0/8"]
    )
    scope = _scope(peer="8.8.8.8", xff="203.0.113.10")
    # Peer is NOT in 10.0.0.0/8 → peer wins
    assert mw._resolve_client_ip(scope) == "8.8.8.8"
