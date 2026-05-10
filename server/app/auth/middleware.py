"""Trusted-proxy XFF middleware (D-29 / REQ-422-425).

Populates scope['state']['client_ip'] which Starlette exposes as request.state.client_ip.
Rate-limit logic and audit_log read from there.

D-29 rule:
  IF settings.smartcopilot_trust_proxy is True
     AND socket peer IP is in any CIDR in settings.smartcopilot_trusted_proxy_cidrs
     AND X-Forwarded-For header is present
  THEN client_ip = left-most XFF entry
  ELSE client_ip = socket peer IP
"""
from __future__ import annotations

from collections.abc import Sequence
from ipaddress import ip_address, ip_network


class TrustedProxyMiddleware:
    def __init__(self, app, *, trust_proxy: bool, allowlist_cidrs: Sequence[str]):
        self.app = app
        self.trust = trust_proxy
        self.cidrs = []
        for c in allowlist_cidrs:
            if not c:
                continue
            try:
                self.cidrs.append(ip_network(c, strict=False))
            except ValueError:
                # Skip malformed CIDR — silent (logged at config-load time elsewhere)
                continue

    def _resolve_client_ip(self, scope: dict) -> str | None:
        peer = scope["client"][0] if scope.get("client") else None
        if not peer:
            return None
        if not self.trust:
            return peer
        try:
            peer_ip = ip_address(peer)
        except ValueError:
            return peer
        if not any(peer_ip in c for c in self.cidrs):
            return peer
        xff = next(
            (v for k, v in scope.get("headers", []) if k == b"x-forwarded-for"),
            None,
        )
        if not xff:
            return peer
        # D-29 / REQ-425: left-most IP — guard against non-UTF-8 bytes (WR-02)
        try:
            leftmost = xff.decode("utf-8", errors="replace").split(",")[0].strip()
        except Exception:  # noqa: BLE001 — defensive; fall back to peer IP
            leftmost = None
        return leftmost or peer

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        client_ip = self._resolve_client_ip(scope)
        state = scope.setdefault("state", {})
        state["client_ip"] = client_ip
        await self.app(scope, receive, send)
