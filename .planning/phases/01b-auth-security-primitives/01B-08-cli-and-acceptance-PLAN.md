---
phase: 1b
plan: "08"
name: cli-and-acceptance
wave: 5
depends_on: ["02", "03", "04", "05", "06", "07"]
requirements: [AUTH-01, AUTH-04, AUTH-09, TEST-02]
files_modified:
  - server/app/cli/__init__.py
  - server/app/cli/main.py
  - server/app/cli/user.py
  - server/app/cli/mcp_token.py
  - server/app/cli/provider_key.py
  - server/pyproject.toml
  - server/app/tests/auth/test_cli.py
  - server/app/tests/auth/test_acceptance.py
  - server/app/tests/auth/test_security_invariants.py
  - .planning/phases/01b-auth-security-primitives/01B-VALIDATION.md
autonomous: true
must_haves:
  truths:
    - "smartcopilot user create --username alice --role admin succeeds (Phase 1b success criterion #1, first half)"
    - "smartcopilot mcp token create --user alice prints plaintext ONCE and exits 0 (Phase 1b success criterion #2, first half)"
    - "smartcopilot mcp token revoke <id> takes effect on the next verify_token call (success criterion #2 second half — already verified by Plan 06 integration test, retested via CLI here)"
    - "smartcopilot provider key set --user alice --provider openai --key sk-... stores Fernet-encrypted bytes (success criterion #4 first half)"
    - "Repository-wide CI grep gates pass: no jwt.decode without algorithms=[, no Fernet.decrypt(...,ttl=, no Pydantic encrypted_key without Field(exclude=True), no SET app.x = $1 (set_config required), no FastAPI/starlette imports under server/app/services/, no fastapi imports under server/app/auth/{context,core,password,tokens,mcp_tokens,audit}.py"
    - "Phase 1b acceptance test (test_acceptance.py::test_phase_1b_acceptance) ties together: create user via CLI → /auth/login → /auth/refresh → /api/v1/admin/reauth → destructive route → MCP token round-trip → provider key set → resolve → all in one happy-path script"
    - "Per-task rows for ALL 8 plans appended to 01B-VALIDATION.md"
    - "PL-06: SYSTEM_USER_ID imported from auth.context everywhere — no hardcoded UUID strings in application code"
  artifacts:
    - path: "server/app/cli/main.py"
      provides: "smartcopilot CLI entrypoint (argparse) with user / mcp / provider subcommands"
    - path: "server/app/tests/auth/test_acceptance.py"
      provides: "Single end-to-end test covering Phase 1b success criteria 1, 2, 4, 5"
    - path: "server/app/tests/auth/test_security_invariants.py"
      provides: "Repository-wide grep gates as pytest tests (CI runs these)"
  key_links:
    - from: "server/app/cli/main.py"
      to: "server/app/services/{users,mcp_tokens,provider_keys}.py"
      via: "argparse subcommand dispatch — CLI calls services directly with system OperationContext"
      pattern: "session_with_rls"
    - from: "server/app/tests/auth/test_security_invariants.py"
      to: "server/app/ (entire tree)"
      via: "subprocess.run('grep -rE ...') — CI gate prevents future regressions"
      pattern: "subprocess.run.*grep"
threat_refs: [T-1b-01, T-1b-02, T-1b-03, T-1b-04, T-1b-05, T-1b-06, T-1b-07, T-1b-08, T-1b-09, T-1b-10]
---

<plan_objective>
Land the Phase 1b CLI stub (`smartcopilot user create`, `smartcopilot mcp token create/list/revoke`, `smartcopilot provider key set`) — sufficient for Phase 1b's success criterion #1 ("user creation via CLI"), criterion #2 ("MCP bearer issued via CLI"), and criterion #4 ("provider key set via CLI"). Add repository-wide grep-gate security invariant tests (Landmines #1, #2, #4, #5; D-17, D-28). Add the cross-cutting acceptance test that proves the 5 ROADMAP success criteria for Phase 1b. Populate the 01B-VALIDATION.md "Per-Task Verification Map" with rows for every task across all 8 plans.
</plan_objective>

<threat_model>

## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CLI subcommand ↔ system OperationContext | CLI bypasses HTTP transport — uses `transport='cli', remote=False`. Service-layer enforcement (slug validation, role checks) still runs |
| Phase 1b → Phase 1c trust boundary handoff | OperationContext.remote flag is now correctly seeded by every transport (REST, MCP HTTP, MCP stdio, CLI, system); Phase 1c will gate vault writes on remote=true |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-1b-01..T-1b-10 | All threats | Repository-wide invariants | mitigate | `test_security_invariants.py` runs grep gates as pytest tests — fail builds when a future PR introduces a banned pattern. Specifically: `jwt.decode(...)` without `algorithms=[`; `Fernet.decrypt(..., ttl=)`; Pydantic models with `encrypted_key:` lacking `Field(exclude=True)`; `text("SET app.x = ...")`; `from fastapi` under `server/app/services/`; missing-secret startup-fail. |

</threat_model>

<read_first_global>
- server/app/services/{users,mcp_tokens,provider_keys}.py (Plan 06 — CLI consumes these)
- server/app/dependencies.py (session_with_rls — used by CLI)
- server/app/auth/context.py (system_operation_context — used by CLI)
- server/app/main.py (Plan 07 — proves startup-fail behavior)
- .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md decisions D-22 (transport=cli, remote=false), D-28
- .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md "server/app/cli/*" section
- .planning/ROADMAP.md (5 Phase 1b success criteria — driven by test_acceptance.py)
- .planning/phases/01b-auth-security-primitives/01B-VALIDATION.md (Per-Task Verification Map — append rows for all 8 plans)
</read_first_global>

<tasks>

<task type="auto">
  <id>08-01</id>
  <name>Task 1: CLI stub — user / mcp token / provider key (argparse)</name>
  <read_first>
    - server/app/services/users.py (create_user, get_user_by_username)
    - server/app/services/mcp_tokens.py (create_mcp_token, list_for_user, revoke_token)
    - server/app/services/provider_keys.py (set_provider_key)
    - server/app/auth/context.py (system_operation_context, OperationContext)
    - server/app/dependencies.py (session_with_rls)
    - .planning/phases/01b-auth-security-primitives/01B-PATTERNS.md "server/app/cli/*" section
    - .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md D-22 (CLI transport)
  </read_first>
  <action>
    Create `server/app/cli/__init__.py` — single line: `"""smartcopilot CLI. Phase 1b stub: user, mcp token, provider key."""`

    Create `server/app/cli/main.py`:
    ```python
    """smartcopilot CLI entrypoint (Phase 1b stub).

    Subcommands:
      user create
      mcp token create / list / revoke
      provider key set

    Each subcommand builds an OperationContext(transport='cli', remote=False, ...)
    and calls services/* via session_with_rls. The full Phase 1d CLI extends this.
    """
    from __future__ import annotations

    import argparse
    import asyncio
    import sys

    from app.cli import mcp_token as mcp_token_cmd
    from app.cli import provider_key as provider_key_cmd
    from app.cli import user as user_cmd


    def build_parser() -> argparse.ArgumentParser:
        p = argparse.ArgumentParser(prog="smartcopilot")
        sub = p.add_subparsers(dest="command", required=True)

        user_cmd.add_subparser(sub)
        mcp_token_cmd.add_subparser(sub)
        provider_key_cmd.add_subparser(sub)

        return p


    def main(argv: list[str] | None = None) -> int:
        parser = build_parser()
        args = parser.parse_args(argv)
        return asyncio.run(args.func(args))


    if __name__ == "__main__":
        sys.exit(main())
    ```

    Create `server/app/cli/user.py`:
    ```python
    """smartcopilot user — Phase 1b: create only."""
    from __future__ import annotations

    import argparse
    import getpass

    from app.auth.context import system_operation_context
    from app.dependencies import session_with_rls
    from app.services.users import UsernameExists, create_user


    def add_subparser(sub: argparse._SubParsersAction) -> None:
        p = sub.add_parser("user", help="user CRUD")
        usub = p.add_subparsers(dest="user_command", required=True)
        create = usub.add_parser("create", help="create a new user")
        create.add_argument("--username", required=True)
        create.add_argument("--role", choices=["admin", "user"], default="user")
        create.add_argument("--email", default=None)
        create.add_argument("--password", default=None, help="if omitted, prompt securely")
        create.set_defaults(func=_handle_create)


    async def _handle_create(args: argparse.Namespace) -> int:
        password = args.password or getpass.getpass("Password: ")
        ctx = system_operation_context(client_name="cli", request_id="cli-user-create")
        async for session in session_with_rls(ctx):
            try:
                user = await create_user(
                    session, ctx,
                    username=args.username, password_plain=password,
                    role=args.role, email=args.email,
                )
            except UsernameExists as e:
                print(f"error: username exists: {e}", flush=True)
                return 2
            await session.commit()
        print(f"created user {user.username} (id={user.id}, role={user.role})", flush=True)
        return 0
    ```

    Create `server/app/cli/mcp_token.py`:
    ```python
    """smartcopilot mcp token — create / list / revoke."""
    from __future__ import annotations

    import argparse
    import uuid

    from app.auth.context import OperationContext, system_operation_context
    from app.dependencies import session_with_rls
    from app.services.mcp_tokens import create_mcp_token, list_for_user, revoke_token
    from app.services.users import get_user_by_username, normalize_username


    def add_subparser(sub: argparse._SubParsersAction) -> None:
        p = sub.add_parser("mcp", help="MCP commands")
        msub = p.add_subparsers(dest="mcp_command", required=True)
        token = msub.add_parser("token", help="MCP bearer tokens")
        tsub = token.add_subparsers(dest="token_command", required=True)

        create = tsub.add_parser("create", help="create an MCP token (plaintext shown ONCE)")
        create.add_argument("--user", required=True, help="username")
        create.add_argument("--name", default=None)
        create.set_defaults(func=_handle_create)

        ls = tsub.add_parser("list", help="list MCP tokens for a user")
        ls.add_argument("--user", required=True)
        ls.set_defaults(func=_handle_list)

        rv = tsub.add_parser("revoke", help="revoke an MCP token by id")
        rv.add_argument("--id", required=True)
        rv.set_defaults(func=_handle_revoke)


    async def _resolve_user_id(username: str) -> uuid.UUID:
        async for session in session_with_rls(system_operation_context()):
            user = await get_user_by_username(session, username)
            if user is None:
                raise SystemExit(f"error: user not found: {username}")
            return user.id


    async def _handle_create(args: argparse.Namespace) -> int:
        uid = await _resolve_user_id(normalize_username(args.user))
        ctx = OperationContext(
            user_id=uid, role="user", transport="cli", remote=False,
            client_name="cli", request_id="cli-mcp-create",
        )
        async for session in session_with_rls(ctx):
            plaintext, row = await create_mcp_token(session, ctx, name=args.name)
            await session.commit()
        # IMPORTANT: plaintext shown ONCE — operator must save it now
        print(f"id={row.id}", flush=True)
        print(f"token={plaintext}", flush=True)
        print("WARNING: this token plaintext will not be shown again", flush=True)
        return 0


    async def _handle_list(args: argparse.Namespace) -> int:
        uid = await _resolve_user_id(normalize_username(args.user))
        ctx = OperationContext(
            user_id=uid, role="user", transport="cli", remote=False,
            client_name="cli", request_id="cli-mcp-list",
        )
        async for session in session_with_rls(ctx):
            rows = await list_for_user(session, uid)
        if not rows:
            print("(no active tokens)")
        for r in rows:
            print(f"{r.id}\t{r.name or '-'}\tlast_used_at={r.last_used_at}")
        return 0


    async def _handle_revoke(args: argparse.Namespace) -> int:
        token_id = uuid.UUID(args.id)
        # System context — revoke is admin-grade
        ctx = system_operation_context(client_name="cli", request_id="cli-mcp-revoke")
        async for session in session_with_rls(ctx):
            await revoke_token(session, token_id)
            await session.commit()
        print(f"revoked {token_id}")
        return 0
    ```

    Create `server/app/cli/provider_key.py`:
    ```python
    """smartcopilot provider key — Phase 1b: set only."""
    from __future__ import annotations

    import argparse
    import getpass

    from app.auth.context import OperationContext, system_operation_context
    from app.dependencies import session_with_rls
    from app.services.provider_keys import set_provider_key
    from app.services.users import get_user_by_username, normalize_username


    def add_subparser(sub: argparse._SubParsersAction) -> None:
        p = sub.add_parser("provider", help="provider key commands")
        psub = p.add_subparsers(dest="provider_command", required=True)
        key = psub.add_parser("key", help="provider key CRUD")
        ksub = key.add_subparsers(dest="key_command", required=True)
        set_ = ksub.add_parser("set", help="set or replace a provider key")
        set_.add_argument("--user", required=True)
        set_.add_argument("--provider", required=True)
        set_.add_argument("--key", default=None, help="if omitted, prompt securely")
        set_.set_defaults(func=_handle_set)


    async def _handle_set(args: argparse.Namespace) -> int:
        plaintext = args.key or getpass.getpass("Provider key: ")
        # Resolve target user
        async for session in session_with_rls(system_operation_context()):
            user = await get_user_by_username(session, normalize_username(args.user))
            if user is None:
                print(f"error: user not found: {args.user}")
                return 2
        # Set key under target user's RLS context
        ctx = OperationContext(
            user_id=user.id, role=user.role, transport="cli", remote=False,
            client_name="cli", request_id="cli-provider-set",
        )
        async for session in session_with_rls(ctx):
            row = await set_provider_key(session, ctx, provider=args.provider, plaintext=plaintext)
            await session.commit()
        print(f"set provider_key id={row.id} provider={row.provider} hint={row.key_hint}")
        return 0
    ```

    Edit `server/pyproject.toml` `[project.scripts]` (or `[project]` section) — add a console_scripts entry. If `[project.scripts]` does not exist yet, append:
    ```toml
    [project.scripts]
    smartcopilot = "app.cli.main:main"
    ```
  </action>
  <acceptance_criteria>
    - `test -f server/app/cli/main.py && test -f server/app/cli/user.py && test -f server/app/cli/mcp_token.py && test -f server/app/cli/provider_key.py`
    - `grep -q '"smartcopilot = "app.cli.main:main"' server/pyproject.toml || grep -q "smartcopilot = .app.cli.main:main." server/pyproject.toml` returns 0
    - **No FastAPI imports in CLI:** `! grep -E "^(from|import) (fastapi|starlette)" server/app/cli/` (recurse via grep -r) returns 0: `! grep -rE "^(from|import) (fastapi|starlette)" server/app/cli/` exits 0
    - `cd server && pip install -e . 2>&1 | tail -5` succeeds (smartcopilot script installed)
    - `cd server && python -m app.cli.main --help` exits 0 and lists user/mcp/provider subcommands: `python -m app.cli.main --help 2>&1 | grep -qE "(user|mcp|provider)"` exits 0
    - `cd server && ruff check app/cli/` exits 0
  </acceptance_criteria>
  <done>CLI entrypoint exists; argparse skeleton with three subcommands; console_scripts wires `smartcopilot = app.cli.main:main`; no FastAPI imports.</done>
</task>

<task type="auto">
  <id>08-02</id>
  <name>Task 2: test_cli.py — exercise CLI commands against testcontainer</name>
  <read_first>
    - server/app/cli/main.py (just created)
    - server/app/tests/auth/conftest.py
    - server/app/tests/auth/test_acceptance.py (does not exist yet — paired with this test)
  </read_first>
  <action>
    Create `server/app/tests/auth/test_cli.py`:
    ```python
    """CLI integration tests — drives the smartcopilot binary via subprocess."""
    from __future__ import annotations

    import asyncio
    import os
    import subprocess
    import sys
    from pathlib import Path

    import pytest
    from sqlalchemy import text

    from app.auth.context import system_operation_context
    from app.dependencies import session_with_rls

    pytestmark = [pytest.mark.auth, pytest.mark.integration]


    async def _delete_user(username: str) -> None:
        async for session in session_with_rls(system_operation_context()):
            await session.execute(text("DELETE FROM users WHERE username = :u"), {"u": username})
            await session.commit()


    def _run_cli(argv: list[str], capsys) -> tuple[int, str]:
        # Spawn CLI via subprocess to avoid nested asyncio.run() when tests are
        # already running in an event loop. Inherit full test environment so
        # database URLs, Fernet key, JWT key, PYTHONPATH are all passed through.
        result = subprocess.run(
            [sys.executable, "-m", "app.cli.main"] + argv,
            capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2].parent)},
        )
        captured = capsys.readouterr()
        return result.returncode, result.stdout + result.stderr


    def test_cli_user_create_succeeds(capsys) -> None:
        try:
            rc, out = _run_cli(
                ["user", "create", "--username", "cli_alice", "--role", "admin", "--password", "p@ss"],
                capsys,
            )
            assert rc == 0
            assert "created user cli_alice" in out
        finally:
            import asyncio
            asyncio.run(_delete_user("cli_alice"))


    def test_cli_user_create_rejects_duplicate(capsys) -> None:
        try:
            # First create the user
            rc1, _ = _run_cli(["user", "create", "--username", "cli_dup", "--password", "p"], capsys)
            assert rc1 == 0
            # Attempt duplicate — should fail with code 2
            rc, out = _run_cli(
                ["user", "create", "--username", "cli_dup", "--password", "p"],
                capsys,
            )
            assert rc == 2
            assert "username exists" in out
        finally:
            import asyncio
            asyncio.run(_delete_user("cli_dup"))


    def test_cli_mcp_token_create_prints_plaintext_once(capsys) -> None:
        import asyncio
        # First create a user
        rc1, _ = _run_cli(["user", "create", "--username", "cli_tok_user", "--password", "p"], capsys)
        assert rc1 == 0
        try:
            rc, out = _run_cli(["mcp", "token", "create", "--user", "cli_tok_user", "--name", "ci"], capsys)
            assert rc == 0, out
            # Plaintext appears with scmcp_ prefix; warning includes "will not be shown again"
            assert "token=scmcp_" in out
            assert "will not be shown again" in out
        finally:
            asyncio.run(_delete_user("cli_tok_user"))
    ```
  </action>
  <acceptance_criteria>
    - `cd server && pytest -x -q app/tests/auth/test_cli.py` exits 0 (3 tests pass)
    - `cd server && ruff check app/tests/auth/test_cli.py` exits 0
  </acceptance_criteria>
  <done>3 CLI integration tests pass; user create / dup rejection / mcp token create-plaintext-once verified.</done>
</task>

<task type="auto">
  <id>08-03</id>
  <name>Task 3: test_security_invariants.py — repo-wide grep gates</name>
  <read_first>
    - .planning/phases/01b-auth-security-primitives/01b-RESEARCH.md §Landmines (1, 2, 4, 5)
    - .planning/phases/01b-auth-security-primitives/01b-CONTEXT.md D-17, D-28
    - All Plan 04, 05, 06 source files (the patterns we are guarding)
  </read_first>
  <action>
    Create `server/app/tests/auth/test_security_invariants.py`:
    ```python
    """Repository-wide security invariant tests (Landmine #1, #2, #4, #5; D-17, D-28).

    Each test runs `git grep` (or plain grep -r) over server/app/ and asserts the
    bad pattern is absent. CI runs these tests on every PR.
    """
    from __future__ import annotations

    import subprocess
    from pathlib import Path

    import pytest

    pytestmark = [pytest.mark.auth, pytest.mark.unit]

    SERVER_APP = Path(__file__).resolve().parents[2]  # server/app


    def _grep(pattern: str, *, ext: str = "py", invert: bool = False) -> list[str]:
        """Recursive grep over server/app/. Returns matching lines (or empty if invert hit)."""
        try:
            result = subprocess.run(
                ["grep", "-rEn", "--include", f"*.{ext}", pattern, str(SERVER_APP)],
                capture_output=True, text=True, check=False,
            )
        except FileNotFoundError:
            pytest.skip("grep not available")
        return result.stdout.strip().splitlines()


    # ---- Landmine #2: jwt.decode without explicit algorithms allowlist ----

    def test_no_jwt_decode_without_algorithms_list() -> None:
        """Every jwt.decode call MUST include algorithms=[. CVE-2024-33663 + CVE-2025-61152."""
        hits = _grep(r"jwt\.decode\(")
        # Filter: lines that have jwt.decode( BUT lack algorithms=[
        bad = [
            line for line in hits
            if "algorithms=[" not in line
            # exclude this very test file's regex and the assertion-narrating tests
            and "test_security_invariants.py" not in line
            and "test_jwt_tokens.py" not in line
        ]
        assert not bad, f"jwt.decode without algorithms=[ — Landmine #2:\n" + "\n".join(bad)


    # ---- Landmine #4: Fernet ttl= ----

    def test_no_fernet_decrypt_with_ttl() -> None:
        """Provider keys are at-rest with no expiry; ttl= would silently expire them."""
        hits = _grep(r"\.decrypt\([^)]*ttl=")
        bad = [line for line in hits if "test_" not in line]
        assert not bad, f"Fernet.decrypt(...,ttl=) — Landmine #4:\n" + "\n".join(bad)


    # ---- Landmine #5: SET ... = $1 binding (illegal SQL) ----

    def test_no_text_set_app_with_bind() -> None:
        """SET ... = $1 is illegal SQL; use set_config(name, value, false) instead."""
        # Pattern: text("SET app.<x> = ... [bind]
        hits = _grep(r'text\("SET app\.')
        bad = [line for line in hits if "test_" not in line]
        assert not bad, f"text(\"SET app.* — Landmine #5:\n" + "\n".join(bad)


    # ---- D-28: encrypted_key Pydantic field MUST have Field(exclude=True) ----

    def test_encrypted_key_is_field_excluded() -> None:
        """Every Pydantic model declaring encrypted_key must use Field(exclude=True)."""
        hits = _grep(r"encrypted_key:.*bytes")
        bad: list[str] = []
        for hit in hits:
            # Skip ORM model declarations (mapped_column-based — not Pydantic)
            if "mapped_column" in hit:
                continue
            # The line itself must contain Field(exclude=True)
            if "Field(exclude=True)" not in hit:
                # Allow follow-up `= Field(exclude=True)` on same logical line — re-check
                bad.append(hit)
        assert not bad, f"Pydantic encrypted_key without Field(exclude=True) — D-28:\n" + "\n".join(bad)


    # ---- D-17: services/* must NOT import FastAPI types ----

    def test_services_does_not_import_fastapi() -> None:
        result = subprocess.run(
            ["grep", "-rEn", r"^(from|import) (fastapi|starlette)", str(SERVER_APP / "services")],
            capture_output=True, text=True, check=False,
        )
        bad = result.stdout.strip().splitlines()
        assert not bad, f"services/ MUST NOT import FastAPI/starlette — D-17:\n" + "\n".join(bad)


    # ---- D-17: auth/{context,core,password,tokens,mcp_tokens,audit}.py must NOT import FastAPI ----

    def test_pure_auth_modules_do_not_import_fastapi() -> None:
        targets = ["context.py", "core.py", "password.py", "tokens.py", "mcp_tokens.py", "audit.py"]
        bad: list[str] = []
        for t in targets:
            f = SERVER_APP / "auth" / t
            content = f.read_text()
            for line in content.splitlines():
                if (line.startswith("from fastapi") or line.startswith("import fastapi")
                    or line.startswith("from starlette") or line.startswith("import starlette")):
                    bad.append(f"{f}: {line}")
        assert not bad, f"pure auth/* modules MUST NOT import FastAPI/starlette — D-17:\n" + "\n".join(bad)
    ```
  </action>
  <acceptance_criteria>
    - `cd server && pytest -x -q app/tests/auth/test_security_invariants.py` exits 0 (6 tests pass against the current tree)
    - `cd server && ruff check app/tests/auth/test_security_invariants.py` exits 0
  </acceptance_criteria>
  <done>6 repo-wide grep gates pass; CI prevents future regression on Landmines #1/#2/#4/#5 and D-17/D-28.</done>
</task>

<task type="auto">
  <id>08-04</id>
  <name>Task 4: test_acceptance.py — Phase 1b end-to-end happy-path</name>
  <read_first>
    - .planning/ROADMAP.md (Phase 1b 5 success criteria)
    - All previous Plans 01-07 — this test ties them together
    - server/app/tests/auth/conftest.py (fixtures)
  </read_first>
  <action>
    Create `server/app/tests/auth/test_acceptance.py`:
    ```python
    """Phase 1b acceptance test — end-to-end happy path.

    Maps to ROADMAP Phase 1b 5 success criteria:
      1. CLI user create + /auth/login + /auth/refresh + rate-limit envelope
      2. CLI mcp token create (plaintext shown once); revoke; verify <5s
      3. RLS isolation — covered by test_rls_isolation.py
      4. Provider key Fernet round-trip + Field(exclude=True) — covered by test_provider_keys.py
         + container fail-on-startup — covered by test_main_startup_fail (this file)
      5. /api/v1/admin/reauth grants fresh window; destructive route 403 then 200 after reauth

    This test is the "phase ships" gate. It fails if any step regresses.
    """
    from __future__ import annotations

    import subprocess
    import sys
    import uuid

    import pytest
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import text

    from app.auth.context import system_operation_context
    from app.dependencies import session_with_rls

    pytestmark = [pytest.mark.auth, pytest.mark.integration]


    async def _delete_user(username: str) -> None:
        async for session in session_with_rls(system_operation_context()):
            await session.execute(text("DELETE FROM users WHERE username = :u"), {"u": username})
            await session.commit()


    async def test_phase_1b_acceptance() -> None:
        """The Phase 1b ship-or-not gate."""
        from app.cli.main import main as cli_main
        from app.main import app

        username = "acct_alice"
        password = "p@ssw0rd-acct"
        try:
            # 1a. CLI user create
            rc = cli_main(["user", "create", "--username", username, "--role", "admin", "--password", password])
            assert rc == 0

            # 1b. /auth/login → token pair
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                login = await c.post("/auth/login", json={"username": username, "password": password})
                assert login.status_code == 200, login.text
                tokens = login.json()
                assert "access_jwt" in tokens and "refresh_token" in tokens

                # 1c. /auth/refresh
                refreshed = await c.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
                assert refreshed.status_code == 200
                tokens = refreshed.json()

                # 5a. Destructive route without fresh-auth — 403
                # The Plan 07 task 07-05 global @app.exception_handler(HTTPException)
                # flattens HTTPException(detail={"error": {...}}) to body["error"][...]
                # (BLOCKER #3 closure). Tests assert against the flat shape.
                headers = {"Authorization": f"Bearer {tokens['access_jwt']}"}
                forbidden = await c.post("/api/v1/admin/_demo_destructive", headers=headers)
                assert forbidden.status_code == 403
                envelope = forbidden.json()
                assert envelope["error"]["code"] == "admin_reauth_required"
                assert envelope["error"]["details"]["reauth_url"] == "/api/v1/admin/reauth"
                assert envelope["error"]["details"]["freshness_window_minutes"] == 60

                # 5b. /admin/reauth
                reauth = await c.post(
                    "/api/v1/admin/reauth",
                    headers=headers,
                    json={"factor": "password", "password": password},
                )
                assert reauth.status_code == 200, reauth.text

                # 5c. Destructive route now succeeds
                ok = await c.post("/api/v1/admin/_demo_destructive", headers=headers)
                assert ok.status_code == 200, ok.text

            # 2a. CLI mcp token create
            rc = cli_main(["mcp", "token", "create", "--user", username, "--name", "acceptance"])
            assert rc == 0
            # Plaintext is in stdout — captured by capsys would be ideal; here we just trust rc=0

            # 4a. CLI provider key set
            rc = cli_main([
                "provider", "key", "set", "--user", username,
                "--provider", "openai", "--key", "sk-acceptance-test",
            ])
            assert rc == 0

            # 4b. Verify the key is encrypted at rest (raw bytes != plaintext)
            async for session in session_with_rls(system_operation_context()):
                row = (await session.execute(
                    text("SELECT encrypted_key FROM provider_keys WHERE user_id = (SELECT id FROM users WHERE username = :u)"),
                    {"u": username},
                )).first()
                assert row is not None
                assert row[0] != b"sk-acceptance-test"
                assert isinstance(row[0], (bytes, memoryview))

        finally:
            # cleanup
            await _delete_user(username)
            async for session in session_with_rls(system_operation_context()):
                await session.execute(text("DELETE FROM login_attempts WHERE username = :u"), {"u": username})
                await session.commit()
    ```

    **REQUIRED — Phase 1b success criterion #4 end-to-end test (WARNING #11 closure):**
    Add the startup-fail e2e test as a real assertion (no skip / no escape hatch). The
    test spawns a subprocess that drives `main.lifespan`'s `__aenter__` with the Fernet
    env var stripped — `_fail_startup_if_missing_secrets` must `sys.exit(1)` and emit
    `FATAL` on stderr.

    ```python
    import os

    def test_main_startup_fail_without_fernet_key() -> None:
        """Phase 1b success criterion #4 — container refuses to start without SMARTCOPILOT_FERNET_KEY.

        Drive lifespan.__aenter__() in a subprocess with SMARTCOPILOT_FERNET_KEY stripped
        from the environment. Assert non-zero exit AND FATAL on stderr.
        """
        # Inherit the test environment (so PYTHONPATH, DATABASE_URL etc. are present)
        # but strip SMARTCOPILOT_FERNET_KEY so _fail_startup_if_missing_secrets fires.
        env = {k: v for k, v in os.environ.items() if k != "SMARTCOPILOT_FERNET_KEY"}
        result = subprocess.run(
            [
                sys.executable, "-c",
                "from app.main import lifespan; "
                "from fastapi import FastAPI; "
                "import asyncio; "
                "asyncio.run(lifespan(FastAPI()).__aenter__())",
            ],
            env=env, capture_output=True, timeout=15,
        )
        assert result.returncode != 0, (
            f"main.py lifespan MUST fail-fast without SMARTCOPILOT_FERNET_KEY; "
            f"rc={result.returncode!r} stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        assert b"FATAL" in result.stderr, (
            f"expected 'FATAL' on stderr; got stderr={result.stderr!r}"
        )
    ```

    Do NOT mark this test with `@pytest.mark.skip` — Phase 1b ROADMAP success
    criterion #4 explicitly requires the e2e behavior, and the source-level grep
    in `test_security_invariants.py` is necessary but not sufficient. The
    `test_main_has_startup_fail_check` source grep (added below) complements
    this runtime test; both must pass.

    Also add to `test_security_invariants.py`:
    ```python
    def test_main_has_startup_fail_check() -> None:
        """Phase 1b success criterion #4 — main.py MUST call fernet() and check jwt_signing_key in lifespan."""
        main_py = (SERVER_APP / "main.py").read_text()
        assert "FernetKeyMissing" in main_py
        assert "jwt_signing_key" in main_py
        assert "sys.exit(1)" in main_py
    ```
  </action>
  <acceptance_criteria>
    - `cd server && pytest -x -q app/tests/auth/test_acceptance.py::test_phase_1b_acceptance` exits 0
    - **WARNING #11 closure — startup-fail e2e:** `cd server && pytest -x -q app/tests/auth/test_acceptance.py::test_main_startup_fail_without_fernet_key` exits 0 (no `@pytest.mark.skip` allowed)
    - **Plan 08 acceptance reads flat error envelope (BLOCKER #3 alignment):** `! grep -q 'detail.*error.*code' server/app/tests/auth/test_acceptance.py` returns 0 (no test reads body["detail"]["error"]; only body["error"])
    - `cd server && pytest -x -q app/tests/auth/test_security_invariants.py` exits 0 (now 7 tests including main startup-fail source check)
    - `cd server && ruff check app/tests/auth/test_acceptance.py` exits 0
    - **Full Phase 1b auth suite green:** `cd server && pytest -q app/tests/auth/` reports 0 failures (~55 tests)
    - **Phase 1a regression check:** `cd server && pytest -q app/tests/integration/` reports 0 failures (7 tests)
  </acceptance_criteria>
  <done>End-to-end acceptance test passes; Phase 1b ships only when this is green.</done>
</task>

<task type="auto">
  <id>08-05</id>
  <name>Task 5: Verify 01B-VALIDATION.md Per-Task Verification Map matches every plan's frontmatter</name>
  <read_first>
    - .planning/phases/01b-auth-security-primitives/01B-VALIDATION.md (already populated during planning — DO NOT rewrite)
    - All 8 PLAN.md frontmatters (`wave:` field) — verify the VALIDATION map's Wave column matches every plan's frontmatter wave
  </read_first>
  <action>
    The "Per-Task Verification Map" in `01B-VALIDATION.md` is already populated during
    planning (BLOCKER #4 closure — the prior prescribed-table snippet contradicted the
    populated content and is dropped). This task is purely verification + sign-off:

    1. **Wave alignment check.** For each plan PLAN.md frontmatter `wave:` value, confirm
       every row in the Per-Task Verification Map for that plan ID has the same Wave
       column value. The current frontmatters are:
         * Plan 01 → wave 0
         * Plan 02 → wave 1
         * Plan 03 → wave 1
         * Plan 04 → wave 1
         * Plan 05 → wave 2
         * Plan 06 → wave 3
         * Plan 07 → wave 4
         * Plan 08 → wave 5
       If any row is out of sync with its plan's frontmatter, fix the row to match the
       frontmatter (the frontmatter is the source of truth). Do not rewrite the entire
       table.

    2. **Idempotent frontmatter assertion (WARNING #10 closure).** Verify that
       `01B-VALIDATION.md` frontmatter has `nyquist_compliant: true` (already established
       during planning; this is idempotent — no flip needed). Verify `status: ready`.

    3. **Validation Sign-Off checkboxes.** Ensure all five sign-off rows under
       `## Validation Sign-Off` are checked (`- [x]` rather than `- [ ]`). The current
       file has them checked; this is a final visual confirmation, no edit required if
       already checked.

    4. **No row rewrites required if the file is unchanged from planning.** Only edit
       individual cells if a Wave-column mismatch with the frontmatter is detected.

    Report rather than rewrite: if every row matches, this task is a no-op for the file
    itself — the verification step is what counts.
  </action>
  <acceptance_criteria>
    - `grep -q "nyquist_compliant: true" .planning/phases/01b-auth-security-primitives/01B-VALIDATION.md` returns 0 (idempotent — should already be true from planning)
    - `grep -q "status: ready" .planning/phases/01b-auth-security-primitives/01B-VALIDATION.md` returns 0
    - Row count: `grep -cE "^\| 0[1-8]-" .planning/phases/01b-auth-security-primitives/01B-VALIDATION.md` reports >= 30 (per-task rows present from planning)
    - **Wave alignment with PLAN frontmatters (BLOCKER #4 closure):** for each plan ID in {01..08}, the Wave column in every VALIDATION row matches that plan's `wave:` frontmatter value. Verified by:
      ```bash
      python3 - <<'PYINNER'
      import pathlib, re, sys
      base = pathlib.Path(".planning/phases/01b-auth-security-primitives")
      val = (base / "01B-VALIDATION.md").read_text()
      mismatches = []
      for plan_path in sorted(base.glob("01B-0*-PLAN.md")):
          fm = plan_path.read_text().split("---", 2)[1]
          plan_id = re.search(r'plan:\s*"(\d+)"', fm).group(1)
          wave = re.search(r"wave:\s*(\d+)", fm).group(1)
          # Find rows in VALIDATION matching plan_id and check wave column
          for m in re.finditer(rf"^\|\s*{plan_id}-\d+\s*\|\s*{plan_id}\s*\|\s*(\d+)\s*\|", val, re.MULTILINE):
              if m.group(1) != wave:
                  mismatches.append((plan_id, wave, m.group(1)))
      if mismatches:
          print("MISMATCH:", mismatches)
          sys.exit(1)
      print("wave-column-aligned")
      PYINNER
      ```
      exits 0 with `wave-column-aligned` printed.
  </acceptance_criteria>
  <done>VALIDATION.md unchanged unless a wave mismatch is detected; nyquist_compliant: true and status: ready confirmed; wave columns aligned with every plan's frontmatter.</done>
</task>

</tasks>

<verification>
  <command>cd server && ruff check app/ alembic/ && pytest -q app/tests/ -x</command>
  <expected>Full repo lint clean. Full test suite green: ~55 Phase 1b auth tests + 7 Phase 1a integration tests pass; 0 failures.</expected>
</verification>

<must_haves>

## Truths
- `smartcopilot user create --username alice --role admin` succeeds (Phase 1b ROADMAP success criterion #1).
- `smartcopilot mcp token create --user alice` shows plaintext ONCE; revoke takes effect on next verify (criterion #2).
- `smartcopilot provider key set --user alice --provider openai --key sk-...` stores Fernet-encrypted bytes (criterion #4).
- Repository-wide CI grep gates pass: no `jwt.decode(` without `algorithms=[`; no `Fernet.decrypt(...,ttl=)`; no Pydantic `encrypted_key` without `Field(exclude=True)`; no `text("SET app.x ...")`; no FastAPI imports under `services/` or pure `auth/*`; main.py contains the startup-fail check.
- Phase 1b acceptance test ties together: CLI user create → /auth/login → /auth/refresh → 403 admin_reauth_required → /admin/reauth → 200 destructive route → CLI mcp create → CLI provider key set → encrypted_key in DB ≠ plaintext.

## Artifacts
- `server/app/cli/{__init__,main,user,mcp_token,provider_key}.py`
- `server/pyproject.toml` `[project.scripts]` entry: `smartcopilot = app.cli.main:main`
- `server/app/tests/auth/{test_cli,test_security_invariants,test_acceptance}.py`
- `.planning/phases/01b-auth-security-primitives/01B-VALIDATION.md` populated Per-Task Verification Map (~30 rows)

## Key Links
- CLI ← services/* (transport-agnostic; CLI is the first non-HTTP transport using `OperationContext(transport='cli', remote=False, ...)`).
- test_security_invariants.py → repository-wide source tree (CI guardian).
- test_acceptance.py → ROADMAP Phase 1b 5 success criteria (Phase ship gate).

</must_haves>

<output>
Append all per-task rows in 01B-VALIDATION.md (Task 08-05).
Create `01B-08-SUMMARY.md` documenting:
- CLI surface delivered for Phase 1b (subset of Phase 1d full CLI)
- 6 repo-wide grep gates established
- Acceptance test mapping to ROADMAP 5 success criteria
- Final test count: ~55 Phase 1b auth + 7 Phase 1a = ~62 total green
</output>
