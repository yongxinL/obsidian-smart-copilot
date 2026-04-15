---
domain: enforcement
name: phase-1-rules
updated: 2026-04-15
confidence: 1.0
tags: [enforcement, phase-1, linting, patterns, naming]
---
# Phase 1 Enforcement Rules

## grep_must_not_exist

```yaml
- id: no-print-logging
  pattern: "print("
  scope: "server/app/**/*.py"
  exclude: ["**/test_*"]
  message: "Use stdlib logging module, not print()"

- id: no-raw-sql
  pattern: '(text\(|execute\(.*"(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP))'
  scope: "server/app/**/*.py"
  exclude: ["**/rag/queries.py", "**/dependencies.py"]
  message: "Raw SQL only in rag/queries.py and dependencies.py. Use SQLAlchemy ORM."

- id: no-plaintext-secrets
  pattern: "(ENCRYPTION_KEY|SECRET_KEY)\\s*="
  scope: "**/*.py"
  exclude: ["**/config.py", "**/test_*"]
  message: "Secrets must come from environment variables via pydantic-settings, never hardcoded."

- id: no-wildcard-imports
  pattern: "from .+ import \\*"
  scope: "server/**/*.py"
  message: "No wildcard imports. Import names explicitly."

- id: no-sync-sqlalchemy
  pattern: "(?<!await )session\\.(execute|scalar|scalars)\\("
  scope: "server/app/api/**/*.py"
  message: "Always await async SQLAlchemy calls in route handlers."

- id: no-set-local-rls
  pattern: "SET LOCAL app.current_user_id"
  scope: "server/**/*.py"
  message: "Use SET + RESET in finally block (Decision 23). Never SET LOCAL."
```

## grep_must_exist

```yaml
- id: rls-routes-use-get-db
  pattern: "Depends(get_db)"
  scope: "server/app/api/**/*.py"
  exclude: ["**/health.py"]
  message: "All RLS-protected route handlers must use Depends(get_db)."

- id: admin-routes-use-require-admin
  pattern: "Depends(require_admin)"
  scope: "server/app/api/admin.py"
  message: "All admin endpoints must use Depends(require_admin)."

- id: pydantic-from-attributes
  pattern: "from_attributes=True"
  scope: "server/app/schemas/**/*.py"
  message: "Response schemas must set model_config = ConfigDict(from_attributes=True)."

- id: rls-reset-in-finally
  pattern: "RESET app.current_user_id"
  scope: "server/app/dependencies.py"
  message: "get_db_session must RESET app.current_user_id in the finally block."

- id: explicit-tablename
  pattern: "__tablename__"
  scope: "server/app/models/**/*.py"
  message: "Every SQLAlchemy model must declare __tablename__ explicitly."

- id: wait-for-pg-check
  pattern: "pg_isready"
  scope: "server/scripts/wait-for-pg.sh"
  message: "wait-for-pg.sh must poll pg_isready before running Alembic and starting uvicorn."
```

## naming_pattern

```yaml
- id: python-snake-case-files
  pattern: "^[a-z][a-z0-9_]*\\.py$"
  scope: "server/app/**/*.py"
  message: "Python filenames must be snake_case."

- id: api-route-paths
  pattern: "^/api/v1/"
  scope: "server/app/api/**/*.py"
  check: "route path prefixes"
  message: "API routes must start with /api/v1/{resource}."

- id: model-class-names
  pattern: "^[A-Z][a-zA-Z]+$"
  scope: "server/app/models/**/*.py"
  check: "class names"
  message: "SQLAlchemy model class names must be PascalCase."

- id: schema-naming
  pattern: "(Create|Update|Response)$"
  scope: "server/app/schemas/**/*.py"
  check: "schema class suffixes"
  message: "Pydantic schemas: {Resource}Create, {Resource}Update, {Resource}Response."

- id: test-file-naming
  pattern: "^test_[a-z][a-z0-9_]*\\.py$"
  scope: "server/tests/**/*.py"
  message: "Test files must be named test_{module}.py."

- id: alembic-revision-naming
  pattern: "^[a-z]+_[a-z_]+$"
  scope: "alembic revision messages"
  message: "Alembic revision messages: {verb}_{noun} in snake_case."

- id: css-module-prefix
  pattern: "^\\.sc-"
  scope: "client/src/**/*.module.css"
  check: "class name selectors"
  message: "CSS module class names must use .sc- prefix."
```
