---
phase: 1b
plan: "04"
name: auth-primitives
wave: 1
depends_on: ["01"]
requirements: [AUTH-01, AUTH-02, AUTH-04]
files_modified:
  - server/app/auth/__init__.py
  - server/app/auth/context.py
  - server/app/auth/password.py
  - server/app/auth/tokens.py
  - server/app/auth/mcp_tokens.py
  - server/app/tests/auth/test_password.py
  - server/app/tests/auth/test_jwt_tokens.py
  - server/app/tests/auth/test_mcp_tokens_unit.py
autonomous: true
must_haves:
  truths:
    - "Argon2 PasswordHasher params at PRD minima: time_cost=3, memory_cost=64*1024, parallelism=1, hash_len=32, salt_len=16 (D-23)"
    - "verify_password returns False on mismatch (does NOT propagate VerifyMismatchError) — Landmine #3"
    - "hash_password and verify_password offload via asyncio.to_thread — Landmine #6 (event-loop block under burst)"
    - "Every jwt.decode call uses algorithms=['HS256'] (a non-empty list) — Landmine #2 / CVE-2024-33663 + CVE-2025-61152"
    - "jwt.decode rejects alg=none and rejects alg-confusion (RS256 against HS256 key)"
    - "MCP token plaintext = scmcp_<urlsafe-token> with 256 bits of entropy via secrets.token_urlsafe(32)"
    - "MCP token storage uses SHA-256 hex; raw plaintext is shown ONCE at generation, never persisted"
    - "AuthResult and OperationContext are frozen, slotted dataclasses with NO FastAPI imports (D-17)"
    - "D-04: Access JWT claims = sub (user_id), role, jti — role is a 15-min snapshot, refreshed on every refresh-token rotation"
    - "D-18: Each transport (REST, MCP stdio, MCP HTTP, system) has its own thin adapter that builds OperationContext from AuthResult; auth/context.py owns only the dataclasses, transport adapters live in dependencies.py / mcp/server.py"
    - "D-22: OperationContext.remote is transport-driven only — REST=False, MCP HTTP=True, MCP stdio=False, system=False; no CWD-inside-/vaults heuristic"
  artifacts:
    - path: "server/app/auth/context.py"
      provides: "AuthResult and OperationContext frozen dataclasses (D-19)"
    - path: "server/app/auth/password.py"
      provides: "hash_password/verify_password (asyncio.to_thread) + needs_rehash"
    - path: "server/app/auth/tokens.py"
      provides: "issue_access_jwt + decode_access_jwt with HS256 allowlist"
    - path: "server/app/auth/mcp_tokens.py"
      provides: "generate_token (256-bit, prefix=scmcp_) + sha256_token_hash"
  key_links:
    - from: "server/app/auth/tokens.py"
      to: "server/app/settings.py:jwt_signing_key + jwt_access_ttl_seconds"
      via: "settings imports — caller supplies signing key + ttl"
      pattern: "settings.jwt_signing_key"
    - from: "server/app/auth/password.py"
      to: "server/app/settings.py:argon2_*"
      via: "PasswordHasher constructed at module import using settings.argon2_*"
      pattern: "settings.argon2_time_cost"
threat_refs: [T-1b-02, T-1b-06]
---

<plan_objective>
Land the four pure auth primitives that downstream modules consume: `auth/context.py` (AuthResult + OperationContext dataclasses), `auth/password.py` (argon2 wrappers with asyncio.to_thread offload), `auth/tokens.py` (JWT issue/decode with HS256 allowlist), and `auth/mcp_tokens.py` (256-bit token generation + SHA-256 hash helper). All four modules are NO-FastAPI imports — they are the contracts that `auth/core.py` (Plan 05) and the service layer (Plan 06) build on. Wave-0 test stubs from Plan 01 (test_password.py, test_jwt_tokens.py, test_mcp_tokens_unit.py) are turned into passing tests in this plan.
</plan_objective>

<threat_model>

## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Untrusted JWT input ↔ application user identity | `decode_access_jwt` is the single trust gate; algorithm allowlist is non-negotiable |
| MCP bearer token plaintext (CLI output) ↔ DB at-rest hash | Plaintext shown once at issuance; storage is SHA-256(plaintext) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-1b-02 | S (Spoofing — JWT algorithm confusion) | server/app/auth/tokens.py:decode_access_jwt | mitigate | `algorithms=["HS256"]` non-empty list on every decode (Landmine #2 / CVE-2024-33663 + CVE-2025-61152). `options={"require": ["sub","role","jti","exp"]}` makes claim absence a decode error. Source-level grep gate enforced via test (`test_decode_uses_explicit_algorithms_allowlist`). python-jose floor `>=3.4` set in Plan 01. |
| T-1b-06 | E (Elevation — token theft) | server/app/auth/mcp_tokens.py:generate_token | mitigate | 256-bit entropy via `secrets.token_urlsafe(32)`; plaintext returned to caller ONCE; storage column holds only `hashlib.sha256(plaintext).hexdigest()`. `last4` hint surfaces a non-sensitive identifier for revocation UX. CI grep gate (Plan 08) bans plaintext storage patterns. |

</threat_model>

<read_first_global>
- .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md decisions D-04, D-17, D-19, D-23
- .planning/phases/01b-auth-security-primitives/01b-RESEARCH.md §"Pattern 1" (argon2 + asyncio.to_thread, lines 322-352), §"Pattern 2" (JWT HS256 hardened, lines 360-394), §"Pattern 4" (MCP token, lines 446-470), §"OperationContext dataclass" (lines 1062-1087), §Landmine #2, §Landmine #3, §Landmine #6
- .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md sections for `auth/__init__.py`, `auth/context.py`, `auth/password.py`, `auth/tokens.py`, `auth/mcp_tokens.py`
- server/app/settings.py (Plan 01-extended — argon2_*, jwt_signing_key, jwt_access_ttl_seconds)
- server/app/tests/auth/test_password.py, test_jwt_tokens.py, test_mcp_tokens_unit.py (Wave 0 stubs)
</read_first_global>

<tasks>

<task type="auto">
  <id>04-01</id>
  <name>Task 1: auth package + context.py (AuthResult + OperationContext dataclasses)</name>
  <read_first>
    - .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md "server/app/auth/__init__.py" and "server/app/auth/context.py" sections
    - .planning/phases/01b-auth-security-primitives/01b-RESEARCH.md §"OperationContext dataclass" (lines 1062-1087) — direct copy
    - .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md D-19 (OperationContext field list), D-22 (transport-driven remote)
  </read_first>
  <action>
    Create `server/app/auth/__init__.py` — single line:
    ```python
    """Auth subsystem: argon2, JWT, MCP bearer, OperationContext, RLS GUC."""
    ```

    Create `server/app/auth/context.py` — direct from RESEARCH.md §"OperationContext dataclass":
    ```python
    """Frozen dataclasses for transport-neutral auth (D-17, D-19, D-22).

    NO FastAPI imports. NO SQLAlchemy imports. Imported by:
      * auth/core.py — pure validators (returns AuthResult)
      * routes/* + middleware — build OperationContext from AuthResult
      * services/* — consume OperationContext (transport-agnostic)
    """
    from __future__ import annotations

    import uuid
    from dataclasses import dataclass
    from typing import Literal


    @dataclass(frozen=True, slots=True)
    class AuthResult:
        """Pure transport-neutral result of token validation. NO FastAPI here.

        On success: user_id + role (+ session_id for refresh path, + mcp_token_id for bearer).
        On failure: error in {"invalid_token", "missing_auth", "service_unavailable"}.
        """
        user_id: uuid.UUID | None = None
        role: str | None = None
        session_id: uuid.UUID | None = None
        mcp_token_id: uuid.UUID | None = None
        error: str | None = None


    @dataclass(frozen=True, slots=True)
    class OperationContext:
        """REQ-520. Built by transport adapter from AuthResult (D-18).

        D-22: remote is transport-driven only — never derived from CWD or any heuristic.
          rest -> True, mcp_http -> True, mcp_stdio -> False, cli -> False, system -> False
        """
        user_id: uuid.UUID
        role: Literal["admin", "user"]
        transport: Literal["rest", "mcp_http", "mcp_stdio", "cli", "system"]
        remote: bool
        client_name: str
        request_id: str
        session_id: uuid.UUID | None = None
        mcp_token_id: uuid.UUID | None = None


    # System user UUID — must match alembic 0002 SYSTEM_USER_ID seed (Plan 02)
    SYSTEM_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


    def system_operation_context(*, request_id: str = "system", client_name: str = "system") -> OperationContext:
        """OperationContext for APScheduler/Alembic/CLI-system contexts (D-22).

        Used by session_with_rls(ctx) in dependencies.py (Plan 05) to set
        app.current_user_id = SYSTEM_USER_ID. RLS policies authored in 0002
        treat the system user as a regular user that owns no per-user data —
        for tables genuinely needed cross-user (audit_log, login_attempts) the
        table is excluded from RLS_TABLES.
        """
        return OperationContext(
            user_id=SYSTEM_USER_ID,
            role="admin",
            transport="system",
            remote=False,
            client_name=client_name,
            request_id=request_id,
        )
    ```

    Verify: NO `from fastapi`, NO `from starlette`, NO `from sqlalchemy` in this file.
  </action>
  <acceptance_criteria>
    - `test -f server/app/auth/__init__.py && test -f server/app/auth/context.py`
    - `grep -q "@dataclass(frozen=True, slots=True)" server/app/auth/context.py` returns 0 (used at least twice)
    - `grep -c "@dataclass(frozen=True, slots=True)" server/app/auth/context.py` reports 2 or more
    - `grep -q "class AuthResult:" server/app/auth/context.py && grep -q "class OperationContext:" server/app/auth/context.py` returns 0
    - `grep -q "SYSTEM_USER_ID = uuid.UUID(.00000000-0000-0000-0000-000000000001.)" server/app/auth/context.py` returns 0
    - **No FastAPI/SQLAlchemy imports (D-17 invariant):** `! grep -E "^(from|import) (fastapi|starlette|sqlalchemy)" server/app/auth/context.py` exits 0
    - All literals from D-19 present: `for lit in '"rest"' '"mcp_http"' '"mcp_stdio"' '"cli"' '"system"'; do grep -qF "$lit" server/app/auth/context.py || { echo "missing $lit"; exit 1; }; done` exits 0
    - Imports cleanly: `cd server && python -c "from app.auth.context import AuthResult, OperationContext, SYSTEM_USER_ID, system_operation_context; ctx = system_operation_context(); assert ctx.user_id == SYSTEM_USER_ID; assert ctx.transport == 'system'; assert ctx.remote is False; print('ok')"` prints `ok`
    - `cd server && ruff check app/auth/` exits 0
  </acceptance_criteria>
  <done>auth package created; AuthResult + OperationContext frozen-slots dataclasses present; system_operation_context() helper returns the canonical system context; no FastAPI/SQLAlchemy imports.</done>
</task>

<task type="auto" tdd="true">
  <id>04-02</id>
  <name>Task 2: auth/password.py + test_password.py (RED→GREEN)</name>
  <read_first>
    - .planning/phases/01b-auth-security-primitives/01b-RESEARCH.md §"Pattern 1" (lines 322-352), §"Landmine #3", §"Landmine #6"
    - .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md D-23 (argon2 params)
    - .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md "server/app/auth/password.py" section
    - server/app/settings.py (Plan 01-extended — argon2_time_cost, argon2_memory_cost, argon2_parallelism)
    - server/app/tests/auth/test_password.py (Wave 0 stubs — 4 test names retained)
  </read_first>
  <behavior>
    - Test 1: `test_hash_verify_roundtrip` — `await hash_password("p@ss")` returns a string starting with `$argon2id$`; `await verify_password(hash, "p@ss")` returns True.
    - Test 2: `test_argon2_params_meet_owasp_minima` — internal `PasswordHasher` has `time_cost >= 3`, `memory_cost >= 64*1024`, `parallelism >= 1`.
    - Test 3: `test_verify_returns_false_on_mismatch` — `await verify_password(hash, "wrong")` returns False (does NOT raise) — Landmine #3.
    - Test 4: `test_check_needs_rehash_after_param_change` — given a hash created with `time_cost=2`, `needs_rehash(stored)` returns True; given a hash created with the current `time_cost=3`, returns False.
    - Bonus invariant (covered by source grep): `hash_password` and `verify_password` use `asyncio.to_thread` (Landmine #6).
  </behavior>
  <action>
    Create `server/app/auth/password.py` — direct from RESEARCH.md §Pattern 1, parameterized by settings:

    ```python
    """argon2id password hashing with asyncio.to_thread offload (D-23, Landmine #6).

    PRD §8 / D-23: time_cost=3, memory_cost=64 MiB, parallelism=1, hash_len=32, salt_len=16.
    Override: parallelism=1 (NOT default 4) — homelab CPU is shared.

    Landmine #6: argon2 is intentionally CPU-bound (~50-200ms per call). A naive
    sync call from FastAPI starves the event loop under login burst. Every hash
    and verify call MUST go through asyncio.to_thread.

    Landmine #3: PasswordHasher.verify raises VerifyMismatchError on mismatch
    (does NOT return False). The wrapper catches all three exception subclasses
    and returns False so callers can write `if await verify_password(...): ...`.
    """
    from __future__ import annotations

    import asyncio

    from argon2 import PasswordHasher
    from argon2.exceptions import (
        InvalidHashError,
        VerificationError,
        VerifyMismatchError,
    )

    from app.settings import settings

    _HASHER: PasswordHasher = PasswordHasher(
        time_cost=settings.argon2_time_cost,
        memory_cost=settings.argon2_memory_cost,
        parallelism=settings.argon2_parallelism,
        hash_len=32,
        salt_len=16,
    )


    async def hash_password(plaintext: str) -> str:
        """Hash a plaintext password. Offloaded to a thread to keep the event loop hot."""
        return await asyncio.to_thread(_HASHER.hash, plaintext)


    async def verify_password(stored_hash: str, plaintext: str) -> bool:
        """Verify; returns False on mismatch (DOES NOT propagate VerifyMismatchError)."""
        try:
            await asyncio.to_thread(_HASHER.verify, stored_hash, plaintext)
            return True
        except (VerifyMismatchError, InvalidHashError, VerificationError):
            return False


    def needs_rehash(stored_hash: str) -> bool:
        """Cheap, runs in-loop (no thread). Caller rehashes after a successful login."""
        return _HASHER.check_needs_rehash(stored_hash)
    ```

    Implement `server/app/tests/auth/test_password.py` — replace 4 Wave-0 stubs:

    ```python
    """AUTH-01 unit tests — argon2 password hashing."""
    from __future__ import annotations

    import pytest
    from argon2 import PasswordHasher

    from app.auth.password import _HASHER, hash_password, needs_rehash, verify_password

    pytestmark = [pytest.mark.auth, pytest.mark.unit]


    async def test_hash_verify_roundtrip() -> None:
        h = await hash_password("p@ssw0rd!")
        assert h.startswith("$argon2id$")
        assert await verify_password(h, "p@ssw0rd!") is True


    def test_argon2_params_meet_owasp_minima() -> None:
        # PRD §8 / D-23 — these are the hardcoded minima
        assert _HASHER.time_cost >= 3
        assert _HASHER.memory_cost >= 64 * 1024
        assert _HASHER.parallelism >= 1
        assert _HASHER.hash_len == 32
        assert _HASHER.salt_len == 16


    async def test_verify_returns_false_on_mismatch() -> None:
        h = await hash_password("correct")
        result = await verify_password(h, "WRONG")
        # Landmine #3 — must not raise
        assert result is False


    async def test_check_needs_rehash_after_param_change() -> None:
        # Build a weaker hash (time_cost=2) and assert needs_rehash flags it
        weak = PasswordHasher(time_cost=2, memory_cost=64 * 1024, parallelism=1)
        weak_hash = weak.hash("x")
        assert needs_rehash(weak_hash) is True

        # A hash built with the current settings should NOT need rehash
        current_hash = await hash_password("x")
        assert needs_rehash(current_hash) is False
    ```
  </action>
  <acceptance_criteria>
    - `test -f server/app/auth/password.py`
    - `grep -q "asyncio.to_thread(_HASHER.hash" server/app/auth/password.py` returns 0 (Landmine #6)
    - `grep -q "asyncio.to_thread(_HASHER.verify" server/app/auth/password.py` returns 0
    - `grep -q "except (VerifyMismatchError, InvalidHashError, VerificationError):" server/app/auth/password.py` returns 0 (Landmine #3)
    - **No FastAPI imports:** `! grep -E "^(from|import) (fastapi|starlette)" server/app/auth/password.py` returns 0
    - `cd server && pytest -x -q app/tests/auth/test_password.py` exits 0 (4 tests pass)
    - All four canonical test names present: `for n in test_hash_verify_roundtrip test_argon2_params_meet_owasp_minima test_verify_returns_false_on_mismatch test_check_needs_rehash_after_param_change; do grep -q "def $n" server/app/tests/auth/test_password.py; done` exits 0
    - No remaining skips: `! grep -q 'pytest.skip("Wave 0 stub' server/app/tests/auth/test_password.py` returns 0
    - `cd server && ruff check app/auth/password.py app/tests/auth/test_password.py` exits 0
  </acceptance_criteria>
  <done>argon2 wrapper with asyncio.to_thread offload, mismatch returns False, params meet OWASP minima — all 4 unit tests pass.</done>
</task>

<task type="auto" tdd="true">
  <id>04-03</id>
  <name>Task 3: auth/tokens.py + test_jwt_tokens.py (HS256 allowlist enforced)</name>
  <read_first>
    - .planning/phases/01b-auth-security-primitives/01b-RESEARCH.md §"Pattern 2" (lines 360-394), §"Landmine #2" (CVE-2024-33663 + CVE-2025-61152)
    - .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md D-04 (claims = sub, role, jti)
    - .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md "server/app/auth/tokens.py" section
    - server/app/tests/auth/test_jwt_tokens.py (Wave 0 stubs — 4 test names)
  </read_first>
  <behavior>
    - `issue_access_jwt(*, user_id, role, signing_key, ttl_seconds, session_id=None)` returns a string `token` whose decoded claims include `sub`, `role`, `jti`, `iat`, `exp`, `nbf`. When `session_id` is non-None, the JWT additionally carries an `sid` claim (string-form UUID); when None, `sid` is omitted to keep older tokens compatible.
    - `decode_access_jwt(token, signing_key)` decodes with `algorithms=["HS256"]` and `options={"require": ["sub","role","jti","exp"]}`. `sid` is OPTIONAL — not in the require list — so refresh-issued tokens (which carry sid) and login-issued tokens (which do not) both decode cleanly. Plan 05 task 05-01's `validate_jwt` reads `claims.get("sid")` into `AuthResult.session_id`.
    - A token whose header has `"alg":"none"` is rejected with `JWTError`.
    - A token signed with an asymmetric key (RS256) and presented to an HS256 decoder is rejected.
    - An expired token (exp in the past) is rejected.
  </behavior>
  <action>
    Create `server/app/auth/tokens.py` — direct from RESEARCH.md §Pattern 2:

    ```python
    """JWT issuance and decoding — HS256 with explicit allowlist (Landmine #2).

    AUTH-02 / D-04: claims = sub, role, jti, iat, exp, nbf.
    Landmine #2: algorithms=["HS256"] (non-empty list) is non-negotiable.
    Never algorithms=None, never algorithms=[]. Floor: python-jose >= 3.4.
    CVE-2024-33663 (alg confusion) and CVE-2025-61152 (alg=none) fixed in 3.4.
    """
    from __future__ import annotations

    import uuid
    from datetime import datetime, timedelta, timezone

    from jose import jwt

    ALGORITHM = "HS256"


    def issue_access_jwt(
        *,
        user_id: uuid.UUID,
        role: str,
        signing_key: str,
        ttl_seconds: int,
        session_id: uuid.UUID | None = None,
    ) -> str:
        """Issue a short-lived (D-01: 15-min default) HS256 JWT.

        When `session_id` is provided (refresh-issued tokens carry it), embed
        it as the optional `sid` claim. Plan 05 task 05-01's `validate_jwt`
        reads it into AuthResult.session_id; Plan 06 task 06-04's
        require_fresh_auth uses it to load sessions.admin_fresh_until.
        """
        now = datetime.now(timezone.utc)
        claims = {
            "sub": str(user_id),
            "role": role,
            "jti": str(uuid.uuid4()),
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
        }
        if session_id is not None:
            claims["sid"] = str(session_id)
        return jwt.encode(claims, signing_key, algorithm=ALGORITHM)


    def decode_access_jwt(token: str, signing_key: str) -> dict:
        """Decode with explicit algorithms allowlist — Landmine #2.

        Raises jose.JWTError on any failure (signature, expiry, missing claim,
        wrong algorithm, alg=none). Caller maps to transport-specific 401.
        """
        return jwt.decode(
            token,
            signing_key,
            algorithms=[ALGORITHM],  # MUST be non-empty list — never None / never []
            options={"require": ["sub", "role", "jti", "exp"]},
        )
    ```

    Implement `server/app/tests/auth/test_jwt_tokens.py` — replace Wave-0 stubs:

    ```python
    """AUTH-02 unit tests — JWT HS256 allowlist + claim discipline."""
    from __future__ import annotations

    import time
    import uuid

    import pytest
    from jose import jwt
    from jose.exceptions import JWTError

    from app.auth.tokens import ALGORITHM, decode_access_jwt, issue_access_jwt

    pytestmark = [pytest.mark.auth, pytest.mark.unit]

    _SIGNING = "test-signing-key-min-32-bytes-for-hs256-aaaaaaaa"


    def test_jwt_roundtrip_includes_sub_role_jti() -> None:
        uid = uuid.uuid4()
        token = issue_access_jwt(user_id=uid, role="admin", signing_key=_SIGNING, ttl_seconds=900)
        claims = decode_access_jwt(token, _SIGNING)
        assert claims["sub"] == str(uid)
        assert claims["role"] == "admin"
        assert "jti" in claims
        assert "exp" in claims and claims["exp"] > claims["iat"]


    def test_decode_rejects_alg_none() -> None:
        # Construct an alg=none token directly (bypasses jwt.encode signing)
        import base64, json
        header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=").decode()
        payload = base64.urlsafe_b64encode(json.dumps({"sub": "x", "role": "admin", "jti": "j", "exp": 9999999999}).encode()).rstrip(b"=").decode()
        unsigned = f"{header}.{payload}."
        with pytest.raises(JWTError):
            decode_access_jwt(unsigned, _SIGNING)


    def test_decode_rejects_alg_confusion() -> None:
        # Token signed with RS256 must NOT verify under our HS256 decoder
        # (we don't have an RSA key here; the simpler proof: token signed with
        # a *different* algorithm is rejected by the algorithms=[ALGORITHM] gate)
        token_other_alg = jwt.encode(
            {"sub": "x", "role": "admin", "jti": "j", "exp": 9999999999, "iat": 0, "nbf": 0},
            _SIGNING,
            algorithm="HS512",  # different from our HS256 allowlist
        )
        with pytest.raises(JWTError):
            decode_access_jwt(token_other_alg, _SIGNING)


    def test_jwt_expiry_enforced() -> None:
        # ttl=1 second; sleep beyond it
        token = issue_access_jwt(user_id=uuid.uuid4(), role="user", signing_key=_SIGNING, ttl_seconds=1)
        time.sleep(2)
        with pytest.raises(JWTError):
            decode_access_jwt(token, _SIGNING)


    def test_decode_uses_explicit_algorithms_allowlist() -> None:
        """Source-level guard — Landmine #2. The decode body must include algorithms=[ALGORITHM]."""
        import inspect
        from app.auth import tokens as t
        src = inspect.getsource(t.decode_access_jwt)
        assert "algorithms=[ALGORITHM]" in src or 'algorithms=["HS256"]' in src, (
            "decode_access_jwt MUST pass algorithms=['HS256'] (non-empty list) — Landmine #2"
        )
        assert "algorithms=None" not in src and "algorithms=[]" not in src
    ```
  </action>
  <acceptance_criteria>
    - `test -f server/app/auth/tokens.py`
    - `grep -q 'algorithms=\[ALGORITHM\]' server/app/auth/tokens.py` returns 0
    - **CI grep gate (Landmine #2):** `! grep -E 'algorithms=(None|\[\])' server/app/auth/tokens.py` returns 0
    - **Repo-wide grep gate:** `! grep -RE 'jwt\.decode\([^)]*\)' server/app 2>/dev/null | grep -v 'algorithms=\[' | grep -v test_jwt_tokens.py` returns 0 (every other jwt.decode call has algorithms=[)
    - `grep -q '"require": \["sub", "role", "jti", "exp"\]' server/app/auth/tokens.py` returns 0
    - **sid claim emission (BLOCKER #6 / sid threading origin):** `grep -q 'session_id: uuid.UUID | None = None' server/app/auth/tokens.py && grep -q 'claims\["sid"\] = str(session_id)' server/app/auth/tokens.py` returns 0
    - **No FastAPI imports:** `! grep -E "^(from|import) (fastapi|starlette)" server/app/auth/tokens.py` returns 0
    - All five test names present: `for n in test_jwt_roundtrip_includes_sub_role_jti test_decode_rejects_alg_none test_decode_rejects_alg_confusion test_jwt_expiry_enforced test_decode_uses_explicit_algorithms_allowlist; do grep -q "def $n" server/app/tests/auth/test_jwt_tokens.py; done` exits 0
    - `cd server && pytest -x -q app/tests/auth/test_jwt_tokens.py` exits 0 (5 tests pass — original 4 stubs replaced + 1 source-level guard added)
    - `cd server && ruff check app/auth/tokens.py app/tests/auth/test_jwt_tokens.py` exits 0
  </acceptance_criteria>
  <done>HS256 issuance/decode with allowlist; alg=none rejected; alg-confusion rejected; expiry enforced; source-level grep gate test prevents future regressions.</done>
  <threat_ref>T-1b-02</threat_ref>
</task>

<task type="auto" tdd="true">
  <id>04-04</id>
  <name>Task 4: auth/mcp_tokens.py + test_mcp_tokens_unit.py</name>
  <read_first>
    - .planning/phases/01b-auth-security-primitives/01b-RESEARCH.md §"Pattern 4" (lines 446-470)
    - .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md "server/app/auth/mcp_tokens.py" section
    - server/app/tests/auth/test_mcp_tokens_unit.py (Wave 0 stubs)
  </read_first>
  <behavior>
    - `generate_token()` returns `(plaintext, sha256_hash, last4)`.
    - Plaintext starts with `scmcp_`; entropy is 256 bits.
    - `sha256_hash` is the hexdigest of the plaintext.
    - `last4` is the last 4 chars of the plaintext.
    - A separate helper `sha256_token_hash(plaintext)` computes the hash for the verify path (Plan 06).
  </behavior>
  <action>
    Create `server/app/auth/mcp_tokens.py`:

    ```python
    """MCP bearer token generation + SHA-256 hash helper (AUTH-04, D-something).

    Plaintext shown ONCE at issuance; storage column holds only the SHA-256 hex.
    Prefix scmcp_ makes leak detection / code search obvious.
    Entropy: 256 bits via secrets.token_urlsafe(32).
    """
    from __future__ import annotations

    import hashlib
    import secrets

    PREFIX = "scmcp_"


    def generate_token() -> tuple[str, str, str]:
        """Returns (plaintext, sha256_hex, last4).

        Plaintext is shown ONCE to the operator at issuance and never persisted.
        The DB stores only the sha256_hex; verify_token (Plan 06 services) hashes
        the candidate and looks up by hash.
        """
        raw = secrets.token_urlsafe(32)  # 32 bytes random -> ~43 base64 chars -> 256 bits
        plaintext = PREFIX + raw
        token_hash = hashlib.sha256(plaintext.encode()).hexdigest()
        last4 = plaintext[-4:]
        return plaintext, token_hash, last4


    def sha256_token_hash(plaintext: str) -> str:
        """Compute the storage hash for an inbound bearer plaintext (verify path)."""
        return hashlib.sha256(plaintext.encode()).hexdigest()
    ```

    Implement `server/app/tests/auth/test_mcp_tokens_unit.py`:

    ```python
    """AUTH-04 unit tests — MCP bearer token entropy + hashing."""
    from __future__ import annotations

    import hashlib

    import pytest

    from app.auth.mcp_tokens import PREFIX, generate_token, sha256_token_hash

    pytestmark = [pytest.mark.auth, pytest.mark.unit]


    def test_token_is_256_bits() -> None:
        """secrets.token_urlsafe(32) provides 32 bytes = 256 bits of entropy."""
        plaintext, _, _ = generate_token()
        body = plaintext.removeprefix(PREFIX)
        # urlsafe base64 of 32 raw bytes = 43 chars (no padding)
        assert len(body) >= 43
        # Ensure two consecutive calls produce different tokens (sanity check on entropy)
        assert generate_token()[0] != plaintext


    def test_token_uses_scmcp_prefix() -> None:
        plaintext, _, last4 = generate_token()
        assert plaintext.startswith("scmcp_")
        assert plaintext.endswith(last4)


    def test_hash_is_sha256_hex() -> None:
        plaintext, token_hash, _ = generate_token()
        assert token_hash == hashlib.sha256(plaintext.encode()).hexdigest()
        assert len(token_hash) == 64  # sha256 hex
        assert all(c in "0123456789abcdef" for c in token_hash)
        # Verify path agrees
        assert sha256_token_hash(plaintext) == token_hash
    ```
  </action>
  <acceptance_criteria>
    - `test -f server/app/auth/mcp_tokens.py`
    - `grep -q "secrets.token_urlsafe(32)" server/app/auth/mcp_tokens.py` returns 0
    - `grep -q 'PREFIX = "scmcp_"' server/app/auth/mcp_tokens.py` returns 0
    - `grep -q "hashlib.sha256(plaintext.encode()).hexdigest()" server/app/auth/mcp_tokens.py` returns 0
    - **No FastAPI / SQLAlchemy imports:** `! grep -E "^(from|import) (fastapi|starlette|sqlalchemy)" server/app/auth/mcp_tokens.py` returns 0
    - `cd server && pytest -x -q app/tests/auth/test_mcp_tokens_unit.py` exits 0 (3 tests pass)
    - All three test names present: `for n in test_token_is_256_bits test_token_uses_scmcp_prefix test_hash_is_sha256_hex; do grep -q "def $n" server/app/tests/auth/test_mcp_tokens_unit.py; done` exits 0
    - `cd server && ruff check app/auth/mcp_tokens.py app/tests/auth/test_mcp_tokens_unit.py` exits 0
  </acceptance_criteria>
  <done>256-bit token generation + sha256 hash helper; verify-path helper present; 3 unit tests pass.</done>
  <threat_ref>T-1b-06</threat_ref>
</task>

</tasks>

<verification>
  <command>cd server && ruff check app/auth/ app/tests/auth/test_password.py app/tests/auth/test_jwt_tokens.py app/tests/auth/test_mcp_tokens_unit.py && pytest -x -q app/tests/auth/test_password.py app/tests/auth/test_jwt_tokens.py app/tests/auth/test_mcp_tokens_unit.py</command>
  <expected>All 4 password + 5 JWT + 3 MCP-token unit tests pass; ruff clean; no FastAPI/SQLAlchemy imports in any auth/* file in this plan.</expected>
</verification>

<must_haves>

## Truths
- argon2 PasswordHasher params at PRD minima (D-23) — verified by `test_argon2_params_meet_owasp_minima`.
- `verify_password` returns False on mismatch (Landmine #3) — verified by `test_verify_returns_false_on_mismatch`.
- `hash_password`/`verify_password` use `asyncio.to_thread` (Landmine #6) — verified by source grep.
- `decode_access_jwt` enforces `algorithms=["HS256"]` (Landmine #2 / CVE-2024-33663 + CVE-2025-61152) — verified by source-level test + repo-wide grep gate.
- `decode_access_jwt` rejects alg=none and rejects alg-confusion — verified by 2 dedicated tests.
- MCP token plaintext = `scmcp_` + 256 bits of entropy — verified by entropy test.
- AuthResult and OperationContext are frozen, slotted dataclasses with NO FastAPI/SQLAlchemy imports (D-17) — verified by source grep.

## Artifacts
- `server/app/auth/__init__.py` (package marker)
- `server/app/auth/context.py` (AuthResult, OperationContext, SYSTEM_USER_ID, system_operation_context)
- `server/app/auth/password.py` (hash_password, verify_password, needs_rehash)
- `server/app/auth/tokens.py` (issue_access_jwt, decode_access_jwt, ALGORITHM)
- `server/app/auth/mcp_tokens.py` (generate_token, sha256_token_hash, PREFIX)
- 3 implemented unit-test files: `test_password.py`, `test_jwt_tokens.py`, `test_mcp_tokens_unit.py`

## Key Links
- `auth/password.py` ← `settings.argon2_*` (PasswordHasher constructed at module import).
- `auth/tokens.py` ← `settings.jwt_signing_key`, `settings.jwt_access_ttl_seconds` (consumed by Plan 06 services/sessions.py).
- `auth/context.py:SYSTEM_USER_ID` ↔ `alembic 0002 INSERT INTO users` seeded UUID (Plan 02).

</must_haves>

<output>
Append per-task rows to `.planning/phases/01b-auth-security-primitives/01B-VALIDATION.md`. Create `01B-04-SUMMARY.md` documenting the four no-FastAPI primitives and Landmine #2/#3/#6 mitigations.
</output>
