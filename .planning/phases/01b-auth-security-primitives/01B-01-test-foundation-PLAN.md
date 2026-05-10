---
phase: 1b
plan: "01"
name: test-foundation
wave: 0
depends_on: []
requirements: [AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, AUTH-07, AUTH-08, AUTH-09, AUTH-10, TEST-02]
files_modified:
  - server/requirements.txt
  - server/.env.example
  - server/app/settings.py
  - server/app/logging/__init__.py
  - server/app/logging/redaction.py
  - server/app/tests/auth/__init__.py
  - server/app/tests/auth/conftest.py
  - server/app/tests/auth/test_password.py
  - server/app/tests/auth/test_jwt_tokens.py
  - server/app/tests/auth/test_mcp_tokens_unit.py
  - server/app/tests/auth/test_encryption.py
  - server/app/tests/auth/test_trusted_proxy_unit.py
  - server/app/tests/auth/test_login.py
  - server/app/tests/auth/test_mcp_tokens_integration.py
  - server/app/tests/auth/test_provider_keys.py
  - server/app/tests/auth/test_admin_reauth.py
  - server/app/tests/auth/test_audit_log.py
  - server/app/tests/auth/test_trusted_proxy.py
  - server/app/tests/auth/test_rls_isolation.py
  - server/app/tests/auth/test_redaction.py
  - server/app/tests/auth/test_scheduler_prune.py
  - server/pyproject.toml
autonomous: true
must_haves:
  truths:
    - "Wave 0 test stubs exist and FAIL/skip for the right reason (target module ImportError or assertion stub) before any Wave 1 work begins"
    - "structlog field redaction processor redacts password, password_hash, encrypted_key, token, token_hash, refresh_token, access_jwt before emitting events (D-27)"
    - "Settings exposes jwt_signing_key, jwt_access_ttl_seconds=900, jwt_refresh_ttl_seconds=2592000, argon2 knobs, login rate-limit knobs, admin_fresh_window_minutes=60, smartcopilot_trust_proxy, smartcopilot_trusted_proxy_cidrs"
    - "requirements.txt pins python-jose[cryptography]>=3.4 (NOT >=3.3) per RESEARCH Landmine #2"
  artifacts:
    - path: "server/app/tests/auth/conftest.py"
      provides: "seed_admin_user, seed_basic_user, seed_user_a_b, system_context, authenticated_client fixtures (function-scope) consuming session-scoped test_engine"
    - path: "server/app/tests/auth/test_rls_isolation.py"
      provides: "Headline TEST-02 test (5 cases per RESEARCH §Validation Architecture)"
    - path: "server/app/logging/redaction.py"
      provides: "structlog processor that redacts the 7 D-27 keys"
    - path: "server/app/settings.py"
      provides: "Phase 1b env vars added to existing Settings class (NOT a new class)"
  key_links:
    - from: "server/app/tests/auth/conftest.py"
      to: "server/app/tests/conftest.py"
      via: "fixture inheritance — reuses postgres_container, test_engine, db_session (session-scope) without rebuilding"
      pattern: "from app.tests.conftest"
    - from: "server/requirements.txt"
      to: "server/.env.example"
      via: "every new env var documented in .env.example must have backing Settings field"
      pattern: "SMARTCOPILOT_FERNET_KEY|JWT_SIGNING_KEY|SMARTCOPILOT_TRUST_PROXY|SMARTCOPILOT_TRUSTED_PROXY_CIDRS"
threat_refs: [T-1b-10]
---

<plan_objective>
Land the Phase 1b validation foundation: requirements.txt deltas (argon2-cffi, python-jose>=3.4, cryptography>=42, structlog>=24, freezegun for time-mocking), Settings extension, .env.example documentation of new env vars, structlog redaction processor (D-27), and the complete suite of Wave-0 test stubs (12 files) that subsequent waves implement against. The headline TEST-02 RLS isolation test stub MUST be authored here — every other auth task verifies against it.
</plan_objective>

<threat_model>

## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| structlog event_dict → log sink | Field-level redaction processor must scrub plaintext secrets before any sink (stdout, files, future Loki) sees them |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-1b-10 | I (Information Disclosure) | server/app/logging/redaction.py | mitigate | structlog processor redacts {password, password_hash, encrypted_key, token, token_hash, refresh_token, access_jwt} → "<redacted>" at every log level. CI grep gate (added in Plan 08) ensures no Fernet.decrypt call uses ttl= and no jwt.decode call omits algorithms=. |

</threat_model>

<read_first_global>
- .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md (D-23, D-24, D-27, D-28)
- .planning/phases/01b-auth-security-primitives/01b-RESEARCH.md sections "Validation Architecture", "Wave 0 Gaps", "Pydantic v2 settings extension", "Standard Stack" (python-jose CVE), Landmine #2, Landmine #4
- .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md sections for `settings.py`, `logging/redaction.py`, `tests/auth/conftest.py`, `tests/test_rls_isolation.py`
- server/requirements.txt
- server/app/settings.py
- server/app/tests/conftest.py (session-scope fixtures to inherit)
- server/app/tests/integration/test_boot.py (test-file convention + rollback isolation analog)
- server/pyproject.toml (markers list)
</read_first_global>

<tasks>

<task type="auto">
  <id>01-01</id>
  <name>Task 1: Add Phase 1b Python deps + .env.example + pytest markers</name>
  <read_first>
    - server/requirements.txt
    - server/requirements-dev.txt
    - server/pyproject.toml (existing markers list)
    - .planning/phases/01b-auth-security-primitives/01b-RESEARCH.md §"Standard Stack" (especially Landmine #2 — python-jose >= 3.4 NOT 3.3)
    - .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md "server/requirements.txt (MODIFY)" section
  </read_first>
  <action>
    1. Append to `server/requirements.txt` (one package per line, `>=` floors only — match existing style):
       ```
       argon2-cffi>=23.1
       python-jose[cryptography]>=3.4   # NOT >=3.3 — CVE-2024-33663 + CVE-2025-61152 (Landmine #2)
       cryptography>=42
       structlog>=24
       ```
       Do NOT downgrade or modify the floor for any existing pin. The `>=3.4` floor on python-jose is LOAD-BEARING — overrides CLAUDE.md's stale `>=3.3` per RESEARCH.md Landmine #2.
    2. Append to `server/requirements-dev.txt`:
       ```
       freezegun>=1.5
       ```
       Used to mock `datetime.now()` in fresh-auth expiry tests (D-13). `testcontainers[postgres]` is already present from Phase 1a.
    3. Create `server/.env.example` (the project does not yet have one — create from scratch). Include with comments:
       ```
       # Phase 1a (already required)
       DATABASE_URL=postgresql+asyncpg://smartcopilot:smartcopilot@localhost:5432/smartcopilot
       ALEMBIC_DATABASE_URL=postgresql+psycopg2://smartcopilot:smartcopilot@localhost:5432/smartcopilot
       # Phase 1b — auth/security (REQUIRED — container fails to start if absent)
       SMARTCOPILOT_FERNET_KEY=                # 32 url-safe base64 bytes; generate via: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
       JWT_SIGNING_KEY=                        # 64+ url-safe bytes; generate via: python -c "import secrets; print(secrets.token_urlsafe(64))"
       # Phase 1b — auth tunables (defaults match D-01/D-02/D-23)
       JWT_ACCESS_TTL_SECONDS=900              # D-01
       JWT_REFRESH_TTL_SECONDS=2592000         # D-02 (30d)
       ARGON2_TIME_COST=3                      # D-23 PRD minima
       ARGON2_MEMORY_COST=65536                # 64 MiB (D-23)
       ARGON2_PARALLELISM=1                    # D-23 (override default 4)
       LOGIN_RATE_LIMIT_WINDOW_SECONDS=900     # D-07 (15 min)
       LOGIN_RATE_LIMIT_MAX_FAILURES=10        # D-07
       LOGIN_ATTEMPTS_RETENTION_HOURS=24       # D-09
       ADMIN_FRESH_WINDOW_MINUTES=60           # D-12
       # Trusted-proxy XFF (D-29)
       SMARTCOPILOT_TRUST_PROXY=false
       SMARTCOPILOT_TRUSTED_PROXY_CIDRS=        # comma-separated CIDRs e.g. 10.0.0.0/8,172.16.0.0/12
       ```
    4. Edit `server/pyproject.toml` `[tool.pytest.ini_options]` `markers = [...]` list — append (preserve existing `integration` marker):
       ```
       "unit: pure unit tests, no testcontainers required",
       "auth: Phase 1b auth + RLS tests (covers AUTH-01..10, TEST-02)",
       ```
       Do NOT change `asyncio_mode = "auto"` or `asyncio_default_*_loop_scope = "session"` lines (Phase 1a invariants).
  </action>
  <acceptance_criteria>
    - `grep -q "python-jose\[cryptography\]>=3.4" server/requirements.txt` returns 0
    - `grep -q "argon2-cffi>=23.1" server/requirements.txt` returns 0
    - `grep -q "structlog>=24" server/requirements.txt` returns 0
    - `! grep -q "python-jose>=3.3$" server/requirements.txt` (no bare 3.3 pin)
    - `grep -q "freezegun" server/requirements-dev.txt` returns 0
    - `grep -q "SMARTCOPILOT_FERNET_KEY=" server/.env.example` returns 0
    - `grep -q "JWT_SIGNING_KEY=" server/.env.example` returns 0
    - `grep -q "SMARTCOPILOT_TRUSTED_PROXY_CIDRS" server/.env.example` returns 0
    - `grep -q '"auth: Phase 1b' server/pyproject.toml` returns 0
    - `cd server && pip install -r requirements.txt -r requirements-dev.txt` succeeds (pinned versions resolve)
    - `cd server && python -c "import argon2, jose, cryptography, structlog, freezegun; print('ok')"` prints `ok`
  </acceptance_criteria>
  <done>Pinned dependencies install cleanly; env-var template documents every new secret; pytest markers `unit` and `auth` registered.</done>
</task>

<task type="auto">
  <id>01-02</id>
  <name>Task 2: Extend Settings class with Phase 1b fields</name>
  <read_first>
    - server/app/settings.py (current Phase 1a shape — fields will be appended INTO this class)
    - .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md decisions D-01, D-02, D-12, D-23, D-29
    - .planning/phases/01b-auth-security-primitives/01b-RESEARCH.md §"Pydantic v2 settings extension" (lines 1033-1056)
    - .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md "server/app/settings.py (MODIFY)" section
  </read_first>
  <action>
    Edit `server/app/settings.py`. Add fields INSIDE the existing `class Settings(BaseSettings):` block, immediately AFTER the existing `debug: bool = Field(default=False)` line. Do NOT create a new BaseSettings subclass. Use `Field(default=...)` exclusively (existing convention) except for `list[str]` which requires `Field(default_factory=list)`.

    Append exactly these fields (preserve `Field(default=...)` style + comments referencing decision IDs):
    ```python
    # --- Phase 1b: Auth + Security Primitives ---
    # JWT (D-01, D-02, D-04)
    jwt_signing_key: str = Field(default="")  # fail-fast in main.py if empty
    jwt_access_ttl_seconds: int = Field(default=900)        # D-01: 15 minutes
    jwt_refresh_ttl_seconds: int = Field(default=2592000)   # D-02: 30 days

    # Argon2 (D-23 — PRD §8 minima)
    argon2_time_cost: int = Field(default=3)
    argon2_memory_cost: int = Field(default=64 * 1024)      # 64 MiB
    argon2_parallelism: int = Field(default=1)              # override library default 4 (homelab CPU)

    # Login rate limit (D-05, D-07, D-09)
    login_rate_limit_window_seconds: int = Field(default=900)
    login_rate_limit_max_failures: int = Field(default=10)
    login_attempts_retention_hours: int = Field(default=24)

    # Step-up fresh auth (D-12)
    admin_fresh_window_minutes: int = Field(default=60)

    # Trusted proxy XFF (D-29)
    smartcopilot_trust_proxy: bool = Field(default=False)
    smartcopilot_trusted_proxy_cidrs: list[str] = Field(default_factory=list)
    ```

    The existing `extra="ignore"` and `case_sensitive=False` in `model_config` mean `JWT_SIGNING_KEY` (env upper) maps to `jwt_signing_key` (field lower). For `smartcopilot_trusted_proxy_cidrs`, pydantic-settings parses comma-separated `SMARTCOPILOT_TRUSTED_PROXY_CIDRS=10.0.0.0/8,172.16.0.0/12` as `list[str]` automatically (verify in test 01-04).
  </action>
  <acceptance_criteria>
    - `grep -q "jwt_signing_key:" server/app/settings.py` returns 0
    - `grep -q "argon2_time_cost: int = Field(default=3)" server/app/settings.py` returns 0
    - `grep -q "argon2_memory_cost: int = Field(default=64 \* 1024)" server/app/settings.py` returns 0
    - `grep -q "argon2_parallelism: int = Field(default=1)" server/app/settings.py` returns 0
    - `grep -q "login_rate_limit_max_failures: int = Field(default=10)" server/app/settings.py` returns 0
    - `grep -q "admin_fresh_window_minutes: int = Field(default=60)" server/app/settings.py` returns 0
    - `grep -q "smartcopilot_trust_proxy: bool" server/app/settings.py` returns 0
    - `grep -q "smartcopilot_trusted_proxy_cidrs: list\[str\] = Field(default_factory=list)" server/app/settings.py` returns 0
    - Only ONE class named `Settings` in the file: `grep -c "^class Settings" server/app/settings.py` returns `1`
    - `cd server && python -c "from app.settings import settings; assert settings.jwt_access_ttl_seconds == 900; assert settings.argon2_memory_cost == 65536; assert settings.smartcopilot_trusted_proxy_cidrs == []; print('ok')"` prints `ok`
  </acceptance_criteria>
  <done>Settings class exposes all Phase 1b fields with documented defaults matching D-01/D-02/D-12/D-23.</done>
</task>

<task type="auto">
  <id>01-03</id>
  <name>Task 3: structlog redaction processor (D-27)</name>
  <read_first>
    - .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md D-27 (the 7 keys to redact)
    - .planning/phases/01b-auth-security-primitives/01b-RESEARCH.md §"Project Constraints" item 11 (structlog redaction)
    - .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md "server/app/logging/redaction.py" section (no analog — establishes convention)
    - server/app/database.py (module-docstring + lazy-init style to mirror)
  </read_first>
  <action>
    Create directory + files:

    `server/app/logging/__init__.py` — single line:
    ```python
    """Structured logging with field redaction. Phase 1b establishes the skeleton."""
    ```

    `server/app/logging/redaction.py` — minimal structlog processor + `configure_logging()`:
    ```python
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

    REDACTED_KEYS: frozenset[str] = frozenset({
        "password",
        "password_hash",
        "encrypted_key",
        "token",
        "token_hash",
        "refresh_token",
        "access_jwt",
    })
    REDACTED_PLACEHOLDER = "<redacted>"


    def _redact(value: Any) -> Any:
        if isinstance(value, dict):
            return {k: (REDACTED_PLACEHOLDER if k in REDACTED_KEYS else _redact(v)) for k, v in value.items()}
        if isinstance(value, list):
            return [_redact(item) for item in value]
        return value


    def redact_processor(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:  # noqa: ARG001
        """structlog processor: redact D-27 keys at every nesting level."""
        for key in list(event_dict.keys()):
            if key in REDACTED_KEYS:
                event_dict[key] = REDACTED_PLACEHOLDER
            else:
                event_dict[key] = _redact(event_dict[key])
        return event_dict


    def configure_logging() -> None:
        """Idempotent structlog configuration. Phase 1b minimal: redact + JSON renderer."""
        structlog.configure(
            processors=[
                redact_processor,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
            cache_logger_on_first_use=True,
        )
    ```

    Do NOT call `configure_logging()` at module-import time — wiring into `main.py` lifespan happens in Plan 07.
  </action>
  <acceptance_criteria>
    - `test -f server/app/logging/__init__.py && test -f server/app/logging/redaction.py`
    - `grep -q "REDACTED_KEYS: frozenset\[str\]" server/app/logging/redaction.py` returns 0
    - All 7 D-27 keys present: `python3 -c "import re,sys; t=open('server/app/logging/redaction.py').read(); keys=['password','password_hash','encrypted_key','token','token_hash','refresh_token','access_jwt']; missing=[k for k in keys if f'\"{k}\"' not in t]; sys.exit(0 if not missing else (print(missing) or 1))"` exits 0
    - Module imports cleanly: `cd server && python -c "from app.logging.redaction import redact_processor, configure_logging, REDACTED_KEYS; assert len(REDACTED_KEYS) == 7; print('ok')"` prints `ok`
    - `cd server && ruff check app/logging/` exits 0
    - Smoke unit invocation: `cd server && python -c "from app.logging.redaction import redact_processor; out = redact_processor(None, 'info', {'msg':'login','password':'p@ss','user_id':'u1','nested':{'token':'abc','ok':1}}); assert out['password']=='<redacted>'; assert out['nested']['token']=='<redacted>'; assert out['user_id']=='u1'; assert out['nested']['ok']==1; print('ok')"` prints `ok`
  </acceptance_criteria>
  <done>Redaction processor and configure_logging() exist and are import-safe; nested dicts redacted; non-secret keys preserved.</done>
</task>

<task type="auto">
  <id>01-04</id>
  <name>Task 4: Wave-0 test stubs — auth conftest + 12 test files (RED phase)</name>
  <read_first>
    - .planning/phases/01b-auth-security-primitives/01b-RESEARCH.md §"Validation Architecture" (Phase Requirements → Test Map: 40 rows)
    - .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md D-30 (RLS isolation test contract)
    - .planning/phases/01b-auth-security-primitives/01B-VALIDATION.md (Wave 0 Requirements list)
    - .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md sections for tests/auth/conftest.py and tests/test_rls_isolation.py
    - server/app/tests/conftest.py (session-scoped fixtures to inherit from)
    - server/app/tests/integration/test_boot.py (test-file convention to mirror)
  </read_first>
  <action>
    Create `server/app/tests/auth/__init__.py` with single-line docstring `"""Phase 1b auth tests (AUTH-01..AUTH-10, TEST-02)."""`.

    Create `server/app/tests/auth/conftest.py` with FUNCTION-scoped fixtures (do NOT override session-scoped fixtures from parent conftest):
    ```python
    """Function-scoped auth fixtures consuming session-scope test_engine.

    Reuses postgres_container, test_engine, db_session from server/app/tests/conftest.py.
    Adds: seed_user_a, seed_user_b, seed_admin_user, seed_basic_user, system_context.
    Every fixture takes test_engine (session-scope) and uses async_sessionmaker.
    """
    from __future__ import annotations

    import uuid
    from collections.abc import AsyncIterator

    import pytest_asyncio
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


    async def _seed_user(
        engine: AsyncEngine, *, username: str, role: str, password_hash: str = "$argon2id$v=19$m=65536,t=3,p=1$placeholder"
    ) -> uuid.UUID:
        uid = uuid.uuid4()
        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with factory() as session:
            await session.execute(
                text(
                    "INSERT INTO users (id, username, role, password_hash, is_active, created_at, updated_at) "
                    "VALUES (:id, :u, :r, :ph, true, now(), now())"
                ),
                {"id": uid, "u": username, "r": role, "ph": password_hash},
            )
            await session.commit()
        return uid


    @pytest_asyncio.fixture(loop_scope="session")
    async def seed_user_a(test_engine) -> AsyncIterator[uuid.UUID]:
        """User A — fixed username 'alice'. Caller is responsible for cleanup or relying on rollback."""
        uid = await _seed_user(test_engine, username="alice", role="user")
        yield uid
        # cleanup — RLS-bypassed via system context (we DELETE by id; CASCADE handles refs)
        factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
        async with factory() as session:
            await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": uid})
            await session.commit()


    @pytest_asyncio.fixture(loop_scope="session")
    async def seed_user_b(test_engine) -> AsyncIterator[uuid.UUID]:
        uid = await _seed_user(test_engine, username="bob", role="user")
        yield uid
        factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
        async with factory() as session:
            await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": uid})
            await session.commit()


    @pytest_asyncio.fixture(loop_scope="session")
    async def seed_admin_user(test_engine) -> AsyncIterator[uuid.UUID]:
        uid = await _seed_user(test_engine, username="admin", role="admin")
        yield uid
        factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
        async with factory() as session:
            await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": uid})
            await session.commit()


    @pytest_asyncio.fixture(loop_scope="session")
    async def seed_basic_user(test_engine) -> AsyncIterator[uuid.UUID]:
        uid = await _seed_user(test_engine, username="basic", role="user")
        yield uid
        factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
        async with factory() as session:
            await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": uid})
            await session.commit()
    ```

    Create the 12 test files listed below. Each file MUST start with:
    ```python
    """<one-line description> — <REQ-IDs>."""
    from __future__ import annotations

    import pytest

    pytestmark = [pytest.mark.auth]
    ```
    Add `pytest.mark.integration` to integration tests, none for pure unit. Each test function name MUST match the canonical names in 01b-RESEARCH.md "Phase Requirements → Test Map" so PATTERNS map to acceptance commands. Each test body is a STUB:
    ```python
    pytest.skip("Wave 0 stub — implemented in Plan <NN>")
    ```
    Where `<NN>` is the implementing plan ID for that REQ:

    Files (each with the test functions named below, all stub-skipped):

    1. `tests/auth/test_password.py` (Plan 04, AUTH-01, marker: unit):
       - `test_hash_verify_roundtrip`
       - `test_argon2_params_meet_owasp_minima`
       - `test_verify_returns_false_on_mismatch`
       - `test_check_needs_rehash_after_param_change`

    2. `tests/auth/test_jwt_tokens.py` (Plan 04, AUTH-02, unit):
       - `test_jwt_roundtrip_includes_sub_role_jti`
       - `test_decode_rejects_alg_none`
       - `test_decode_rejects_alg_confusion`
       - `test_jwt_expiry_enforced`

    3. `tests/auth/test_mcp_tokens_unit.py` (Plan 04, AUTH-04, unit):
       - `test_token_is_256_bits`
       - `test_token_uses_scmcp_prefix`
       - `test_hash_is_sha256_hex`

    4. `tests/auth/test_encryption.py` (Plan 03, AUTH-09, unit):
       - `test_fernet_roundtrip`
       - `test_missing_fernet_key_raises_FernetKeyMissing`
       - `test_decrypt_does_not_use_ttl`
       - `test_multifernet_decrypts_with_secondary_key`

    5. `tests/auth/test_trusted_proxy_unit.py` (Plan 07, AUTH-08, unit):
       - `test_leftmost_xff_chosen`
       - `test_xff_ignored_when_trust_disabled`
       - `test_xff_ignored_when_peer_not_in_allowlist`

    6. `tests/auth/test_login.py` (Plan 07, AUTH-02/03, integration):
       - `test_login_returns_jwt_pair`
       - `test_login_invalid_credentials_returns_401`
       - `test_refresh_token_stored_as_hash`
       - `test_refresh_rotation_revokes_old`
       - `test_old_refresh_replay_rejected`
       - `test_rate_limit_after_10_failures`
       - `test_rate_limit_response_envelope`
       - `test_successful_login_wipes_attempts`
       - `test_sliding_window_ages_out`

    7. `tests/auth/test_mcp_tokens_integration.py` (Plan 06, AUTH-04/05, integration):
       - `test_token_plaintext_shown_once`
       - `test_token_stored_as_hash`
       - `test_revocation_within_5_seconds`
       - `test_last_used_at_updates_on_verify`

    8. `tests/auth/test_provider_keys.py` (Plan 06, AUTH-09/10, integration):
       - `test_encrypted_key_excluded_from_responses`
       - `test_user_key_takes_precedence_over_shared`
       - `test_shared_key_fallback_when_no_user_key`
       - `test_missing_provider_key_error`

    9. `tests/auth/test_admin_reauth.py` (Plan 07, AUTH-06/07, integration):
       - `test_role_enum_is_admin_or_user`
       - `test_non_admin_forbidden_from_admin_route`
       - `test_reauth_sets_admin_fresh_until`
       - `test_destructive_route_403_without_fresh_auth`
       - `test_admin_reauth_required_envelope_shape`
       - `test_fresh_auth_expires_after_60_minutes` (uses freezegun)
       - `test_reauth_unsupported_factor_returns_not_implemented`

    10. `tests/auth/test_audit_log.py` (Plan 05/07, AUTH-06, integration):
        - `test_admin_op_writes_audit_log`
        - `test_admin_reauth_success_writes_audit_log`
        - `test_admin_reauth_failure_writes_audit_log_with_reason`
        - `test_refresh_rotation_audit_logged`

    11. `tests/auth/test_trusted_proxy.py` (Plan 07, AUTH-08, integration):
        - `test_xff_used_when_peer_trusted`
        - `test_xff_ignored_when_untrusted_peer`
        - `test_rate_limit_keys_on_xff_when_trusted`

    12. `tests/auth/test_rls_isolation.py` (Plan 05+08, TEST-02, integration) — **HEADLINE TEST**:
        - `test_no_guc_leak_after_request`
        - `test_user_b_sees_empty_guc`
        - `test_cross_user_read_blocked`
        - `test_system_context_bypass`
        - `test_pool_reset_scrubs_guc`

    13. `tests/auth/test_redaction.py` (Plan 01, D-27, unit):
        - `test_redaction_replaces_all_seven_keys`
        - `test_redaction_recurses_into_nested_dicts`
        - `test_non_secret_keys_preserved`
        - **Implement these THREE tests fully** (not stubs) — they validate Task 01-03 in this same plan. Use `from app.logging.redaction import redact_processor, REDACTED_KEYS, REDACTED_PLACEHOLDER`.

    14. `tests/auth/test_scheduler_prune.py` (Plan 07, AUTH-03 D-09, integration):
        - `test_prune_login_attempts_deletes_old_rows`
        - `test_prune_login_attempts_keeps_recent_rows`

    All test files use `from __future__ import annotations`. Use `from app.tests.conftest import *` is NOT necessary — pytest auto-discovers parent conftest fixtures. Verify by importing `db_session`, `test_engine` directly in fixture signatures.
  </action>
  <acceptance_criteria>
    - All 14 test files exist: `for f in test_password test_jwt_tokens test_mcp_tokens_unit test_encryption test_trusted_proxy_unit test_login test_mcp_tokens_integration test_provider_keys test_admin_reauth test_audit_log test_trusted_proxy test_rls_isolation test_redaction test_scheduler_prune; do test -f server/app/tests/auth/$f.py || { echo "missing $f"; exit 1; }; done` exits 0
    - `test -f server/app/tests/auth/__init__.py && test -f server/app/tests/auth/conftest.py`
    - Headline TEST-02 test functions exist by name: `grep -q "def test_no_guc_leak_after_request" server/app/tests/auth/test_rls_isolation.py && grep -q "def test_cross_user_read_blocked" server/app/tests/auth/test_rls_isolation.py && grep -q "def test_pool_reset_scrubs_guc" server/app/tests/auth/test_rls_isolation.py` returns 0
    - All test files have `pytestmark` set: `! grep -L "pytestmark" server/app/tests/auth/test_*.py` returns no missing files
    - Test discovery succeeds with collection-only (no run): `cd server && pytest --collect-only -q app/tests/auth/ 2>&1 | tail -5` reports `>= 60 tests collected`
    - Redaction tests (test_redaction.py) PASS (they are implemented, not stubbed): `cd server && pytest -x -q app/tests/auth/test_redaction.py` exits 0
    - All other auth tests SKIP for `Wave 0 stub` reason: `cd server && pytest -q app/tests/auth/ 2>&1 | grep -E "skipped|passed" | grep -E "skipped"` reports skipped count >= 50
    - `cd server && ruff check app/tests/auth/` exits 0
  </acceptance_criteria>
  <done>14 test stub files + conftest collected by pytest; redaction tests pass; all other tests skip with explicit "Wave 0 stub" reason; conftest fixtures inherit session-scoped fixtures from parent conftest.</done>
  <threat_ref>T-1b-10</threat_ref>
</task>

</tasks>

<verification>
  <command>cd server && pip install -r requirements.txt -r requirements-dev.txt && ruff check app/ && pytest -q app/tests/ -x</command>
  <expected>All Phase 1a tests still pass (7 boot tests). Phase 1b auth tests collected and either skip (Wave 0 stubs) or pass (redaction tests). Total skipped >= 50, total failed = 0.</expected>
</verification>

<must_haves>

## Truths
- Wave 0 test stubs exist and either skip or fail with explicit "Wave 0 stub" reason — every later task knows where to write its assertions.
- structlog redaction processor scrubs the 7 D-27 keys at every nesting level; redaction tests PASS in this plan.
- Settings exposes all Phase 1b knobs with defaults matching D-01/D-02/D-12/D-23.
- python-jose floor is `>=3.4` (Landmine #2 closed).

## Artifacts
- `server/app/tests/auth/conftest.py` with fixtures: `seed_user_a`, `seed_user_b`, `seed_admin_user`, `seed_basic_user`.
- `server/app/tests/auth/test_rls_isolation.py` — headline TEST-02 with 5 test stubs.
- `server/app/logging/redaction.py` — structlog processor.

## Key Links
- `tests/auth/conftest.py` ← inherits `test_engine`, `db_session` from `tests/conftest.py` (session-scope, NOT overridden).
- `requirements.txt` ↔ `.env.example` ↔ `settings.py` — every new env var has a backing field; every new field has a `.env.example` line.

</must_haves>

<output>
After completion, create `.planning/phases/01b-auth-security-primitives/01B-01-SUMMARY.md` documenting:
- Total stubs created: 14 files + conftest
- Headline TEST-02 stub names (5 functions)
- python-jose pin override rationale (CVE-2024-33663 + CVE-2025-61152)
- structlog redaction processor key list (7 D-27 keys)
- Append per-task rows to `01B-VALIDATION.md` "Per-Task Verification Map" — see frontmatter table.
</output>
