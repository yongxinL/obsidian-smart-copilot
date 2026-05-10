---
phase: 01a-container-data-layer
reviewed: 2026-05-10T03:15:00Z
depth: standard
files_reviewed: 61
files_reviewed_list:
  - package.json
  - pnpm-workspace.yaml
  - .nvmrc
  - .gitignore
  - .env.example
  - .pre-commit-config.yaml
  - docker-compose.yml
  - server/pyproject.toml
  - server/.python-version
  - server/requirements.txt
  - server/requirements-dev.txt
  - server/Dockerfile
  - server/supervisord.conf
  - server/scripts/wait-for-pg.sh
  - server/scripts/docker-entrypoint.sh
  - server/.dockerignore
  - server/app/__init__.py
  - server/app/models/__init__.py
  - server/app/models/base.py
  - server/app/models/user.py
  - server/app/models/session.py
  - server/app/models/mcp_token.py
  - server/app/models/provider_key.py
  - server/app/models/vault.py
  - server/app/models/page.py
  - server/app/models/page_version.py
  - server/app/models/chunk.py
  - server/app/models/entity.py
  - server/app/models/link.py
  - server/app/models/timeline_event.py
  - server/app/models/tag.py
  - server/app/models/job.py
  - server/app/models/audit_log.py
  - server/app/models/skill.py
  - server/app/models/recipe.py
  - server/app/models/eval_candidate.py
  - server/app/models/conversation.py
  - server/app/models/memory.py
  - server/app/models/dream_audit_log.py
  - server/app/models/project.py
  - server/app/models/operation_log.py
  - server/app/models/llm_usage.py
  - server/app/models/index_event.py
  - server/app/models/user_settings.py
  - server/app/models/system_config.py
  - server/app/models/mcp_server.py
  - server/app/models/golden_eval.py
  - server/app/settings.py
  - server/app/database.py
  - server/app/dependencies.py
  - server/app/main.py
  - server/app/routes/__init__.py
  - server/app/routes/health.py
  - server/app/mcp/__init__.py
  - server/app/mcp/server.py
  - server/app/scheduler/__init__.py
  - server/app/scheduler/run.py
  - server/app/vault/__init__.py
  - server/app/vault/watcher.py
  - server/alembic.ini
  - server/alembic/env.py
  - server/alembic/script.py.mako
  - server/alembic/versions/0001_initial_schema.py
  - server/app/tests/__init__.py
  - server/app/tests/conftest.py
  - server/app/tests/integration/__init__.py
  - server/app/tests/integration/test_boot.py
findings:
  critical: 1
  warning: 2
  info: 0
  total: 3
status: fixed
---

# Phase 01a: Code Review Report

**Reviewed:** 2026-05-10T03:15:00Z
**Depth:** standard
**Files Reviewed:** 61
**Status:** issues_found

## Summary

Phase 01a implements the container and data layer foundation for Smart Copilot. The architecture is well-designed with proper separation of concerns: pgvector codec registration, async/sync engine separation, RLS preparation, and a clean monorepo structure. However, one critical security issue and two architectural warnings were identified.

## Critical Issues

### CR-01: SQL injection vulnerability in docker-entrypoint.sh

**File:** `server/scripts/docker-entrypoint.sh:31`
**Issue:** The PostgreSQL password from the environment variable is interpolated directly into a SQL statement without escaping. If the password contains a single quote (`'`), the SQL command will fail or potentially allow SQL injection in certain configurations.

```bash
su postgres -c "psql -v ON_ERROR_STOP=1 --command \"CREATE USER ${POSTGRES_USER} WITH SUPERUSER PASSWORD '${POSTGRES_PASSWORD}';\""
```

**Fix:** Use parameterized SQL via `-c` with proper escaping or heredoc syntax:

```bash
su postgres -c "psql -v ON_ERROR_STOP=1 --command \"CREATE USER $(printf '%s' "$POSTGRES_USER") WITH SUPERUSER PASSWORD '$(printf '%s' "$POSTGRES_PASSWORD" | sed "s/'/''/g')';\""
```

Or use psql's `--set` parameter with proper quoting.

## Warnings

### WR-01: Server defaults use SQL string literals instead of Python types

**File:** `server/app/models/user.py:32-37`
**Issue:** Server defaults are specified as SQL string literals (`"user"`, `"true"`) instead of proper Python types. While this works with PostgreSQL, it bypasses SQLAlchemy's type coercion and may cause subtle bugs if the column type handling changes.

```python
role: Mapped[str] = mapped_column(
    user_role_enum, nullable=False, server_default="user"  # String, not Enum
)
is_active: Mapped[bool] = mapped_column(
    Boolean, nullable=False, server_default="true"  # String "true", not bool True
)
```

**Fix:** Use proper Python values for server_default, or ensure the column type properly coerces strings to the correct database type:

```python
role: Mapped[str] = mapped_column(
    user_role_enum, nullable=False, server_default="user"
)
is_active: Mapped[bool] = mapped_column(
    Boolean, nullable=False, server_default=sa.true()  # or "true" with explicit cast
)
```

This pattern appears in multiple models: `page.py`, `chunk.py`, `memory.py`, `llm_usage.py`, etc. Consider auditing all model files for consistent server_default typing.

### WR-02: No validation for Fernet key in settings

**File:** `server/app/settings.py:24`
**Issue:** `smartcopilot_fernet_key` has an empty string default with no validation. If Phase 1b auth code attempts to use Fernet without this key set, encryption will fail silently or raise cryptic errors at runtime. There is no early warning.

**Fix:** Add validation in the Settings class:

```python
smartcopilot_fernet_key: str = Field(default="")

@field_validator("smartcopilot_fernet_key")
@classmethod
def validate_fernet_key(cls, v: str) -> str:
    if not v:
        warnings.warn(
            "smartcopilot_fernet_key is not set. Provider key encryption will fail.",
            UserWarning,
            stacklevel=2,
        )
    elif len(v) < 32:
        raise ValueError("smartcopilot_fernet_key must be at least 32 characters (44 base64 chars)")
    return v
```

---

## Positive Observations

The following patterns are correctly implemented and should be preserved:

1. **pgvector codec registration** (`server/app/database.py:27-37`): Uses `engine.sync_engine` event listener with `run_async()` - the correct pattern for async SQLAlchemy engines.

2. **RLS preparation** (`server/alembic/versions/0001_initial_schema.py:994-1020`): Correctly enables RLS with `FORCE` on all multi-tenant tables, preparing for Phase 1b policy creation.

3. **Alembic/async engine separation** (`server/alembic/env.py:3-9`): Alembic uses its own sync psycopg2 engine and never imports the async runtime - prevents connection pool conflicts.

4. **APScheduler table exclusion** (`server/alembic/env.py:37-41`): `include_object` filter correctly excludes `apscheduler_jobs` from autogenerate.

5. **Stub signal handling**: All stub processes (mcp/server.py, scheduler/run.py, vault/watcher.py) properly handle SIGTERM/SIGINT for graceful shutdown.

6. **Lifespan context manager** (`server/app/main.py:19-22`): Correctly disposes engine on shutdown.

7. **Test isolation** (`server/app/tests/conftest.py:88-108`): Rollback-per-test pattern with session-scoped engine and function-scoped sessions.

8. **Model organization**: One model class per file (per D-07 convention) with proper use of SQLAlchemy 2.0 `Mapped[]` syntax.

9. **Composite primary keys**: `PageTag` correctly uses composite PK without redundant id column.

10. **ON DELETE behaviors**: Proper use of CASCADE, SET NULL, and explicit FK constraints throughout.

---

_Reviewed: 2026-05-10T03:15:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_