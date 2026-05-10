---
phase: 01a
plan: 04
type: execute
wave: 4
depends_on: [01a-01, 01a-02, 01a-03]
files_modified:
  - server/Dockerfile
  - server/supervisord.conf
  - server/scripts/wait-for-pg.sh
  - server/scripts/docker-entrypoint.sh
  - server/.dockerignore
  - server/app/mcp/__init__.py
  - server/app/mcp/server.py
  - server/app/scheduler/__init__.py
  - server/app/scheduler/run.py
  - server/app/vault/__init__.py
  - server/app/vault/watcher.py
autonomous: false
requirements: [INFRA-01, INFRA-02, INFRA-03, INFRA-08]
must_haves:
  truths:
    - "docker build -t smart-copilot:test server/ succeeds"
    - "docker run starts the container and supervisord reports 5 RUNNING programs within 30s"
    - "Inside the container, alembic upgrade head completes BEFORE uvicorn binds :8000"
    - "GET http://<container>:8000/health returns 200 {status: ok} after boot"
    - "Volumes /data, /vaults, /config are declared and writable when mounted"
    - "PostgreSQL initdb runs on first boot (when /data is empty); persistence works on subsequent boots"
    - "Logs from all 5 supervisord programs appear in docker logs"
    - "Container refuses no env (or runs with safe defaults — Fernet key check belongs to Phase 1b)"
  artifacts:
    - path: "server/Dockerfile"
      provides: "Monolithic production image: pgvector/pgvector:pg16 base + Python deps + supervisord PID 1"
    - path: "server/supervisord.conf"
      provides: "5 programs (postgresql=10, fastapi=20, mcp-http=30, apscheduler=40, watchdog=50) with /dev/fd/1 logging"
    - path: "server/scripts/wait-for-pg.sh"
      provides: "pg_isready loop -> alembic upgrade head -> uvicorn"
    - path: "server/scripts/docker-entrypoint.sh"
      provides: "First-boot initdb + DB user/password setup if /data is empty; idempotent on subsequent boots"
    - path: "server/app/mcp/server.py"
      provides: "MCP HTTP server stub (priority 30 program target — full implementation in Phase 1d)"
    - path: "server/app/scheduler/run.py"
      provides: "APScheduler standalone process stub (priority 40 program target — full implementation in Phase 4)"
    - path: "server/app/vault/watcher.py"
      provides: "watchdog process stub (priority 50 program target — full implementation in Phase 1c)"
  key_links:
    - from: "Dockerfile"
      to: "supervisord"
      via: "ENTRYPOINT/CMD"
      pattern: "supervisord"
    - from: "supervisord.conf [program:fastapi]"
      to: "wait-for-pg.sh"
      via: "command directive"
      pattern: "wait-for-pg.sh"
    - from: "wait-for-pg.sh"
      to: "alembic + uvicorn"
      via: "pg_isready -> alembic -> uvicorn"
      pattern: "alembic upgrade head"
    - from: "supervisord.conf log directives"
      to: "Docker stdout/stderr"
      via: "/dev/fd/1, /dev/fd/2"
      pattern: "/dev/fd/1"
---

<objective>
Build the monolithic production container per PRD §30I and CLAUDE.md. After this plan, `docker build -t smart-copilot:test server/ && docker run --rm smart-copilot:test` boots PostgreSQL 16 + pgvector under supervisord, runs Alembic migrations, then starts uvicorn (port 8000), the MCP HTTP stub (port 8787), the APScheduler stub, and the watchdog stub — all visible in `supervisorctl status` as RUNNING within 30 seconds.

The three "stub" processes (mcp-http, apscheduler, watchdog) intentionally do nothing useful in Phase 1a — they must simply start, log a banner, and stay running so supervisord reports RUNNING. Their real implementations land in Phases 1d, 4, and 1c respectively.

Purpose: Satisfy INFRA-01 (supervisord PID 1), INFRA-02 (5 programs), INFRA-03 (pgvector reachable), INFRA-08 (volumes /data /vaults /config). Establish the canonical Dockerfile + supervisord.conf + wait-for-pg.sh that every subsequent phase deploys against.

Output: server/Dockerfile, server/supervisord.conf, server/scripts/wait-for-pg.sh, server/scripts/docker-entrypoint.sh, server/.dockerignore, three stub process modules.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/REQUIREMENTS.md
@.planning/phases/01a-container-data-layer/01a-CONTEXT.md
@.planning/phases/01a-container-data-layer/01a-RESEARCH.md
@.planning/phases/01a-container-data-layer/01a-VALIDATION.md
@docs/product_requirements_document_v26.05.md

<interfaces>
Application contract from Plan 03 (do not re-derive):
- `app.main:app` is the FastAPI ASGI app; `/health` returns {"status": "ok"}.
- `alembic.ini` lives at `server/alembic.ini`; running `alembic upgrade head` from `server/` migrates the DB given env var `ALEMBIC_DATABASE_URL=postgresql+psycopg2://...`.
- `app.database` exposes `engine` and `async_session_factory`; settings in `app.settings`.

Process targets (full implementations in later phases — Phase 1a stubs only):
- `python -m app.mcp.server --http` — MCP Streamable HTTP server, port 8787 (Phase 1d).
- `python -m app.scheduler.run` — APScheduler standalone process (Phase 4).
- `python -m app.vault.watcher` — watchdog filesystem observer (Phase 1c).

Each Phase 1a stub MUST:
1. Be invokable as `python -m app.<pkg>.<module>` (script-style entry).
2. Log a single banner line on stderr ("[stub] mcp.server starting; full impl in 1d") via the standard `logging` module.
3. Block forever (so supervisord considers it RUNNING) — use `signal.pause()` or `time.sleep(1)` in a loop.
4. Exit cleanly on SIGTERM (so supervisord can stop the container).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create the three supervisord process stubs (mcp.server, scheduler.run, vault.watcher)</name>
  <files>server/app/mcp/__init__.py, server/app/mcp/server.py, server/app/scheduler/__init__.py, server/app/scheduler/run.py, server/app/vault/__init__.py, server/app/vault/watcher.py</files>
  <read_first>
    - .planning/phases/01a-container-data-layer/01a-RESEARCH.md (System Architecture Diagram — process responsibilities)
    - server/app/main.py (existing logging conventions, if any — Phase 1a there are none yet)
    - CLAUDE.md (priority order: mcp-http=30, apscheduler=40, watchdog=50)
  </read_first>
  <action>
Create three module-level scripts that supervisord will start. Each is a Phase 1a STUB — it must start, log, and block until SIGTERM. Real implementations land in Phases 1d (mcp), 4 (scheduler), 1c (watchdog).

1. `server/app/mcp/__init__.py`:
```python
"""MCP server package (full implementation in Phase 1d)."""
```

2. `server/app/mcp/server.py`:
```python
"""MCP HTTP server entry point.

Phase 1a: STUB — starts, logs a banner, blocks until SIGTERM. Real MCP
Streamable HTTP implementation lands in Phase 1d (REQ MCP-01..MCP-08).
Supervisord program priority 30 invokes this as: python -m app.mcp.server --http
"""
from __future__ import annotations

import argparse
import logging
import signal
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [mcp.server] %(message)s")
log = logging.getLogger("smart_copilot.mcp")

_running = True


def _handle_signal(signum, frame):  # noqa: ARG001
    global _running
    log.info("received signal %s; shutting down", signum)
    _running = False


def main() -> int:
    parser = argparse.ArgumentParser(description="Smart Copilot MCP server (Phase 1a stub)")
    parser.add_argument("--http", action="store_true", help="HTTP mode (Phase 1d)")
    parser.add_argument("--stdio", action="store_true", help="stdio mode (Phase 1d)")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    log.info("STUB starting (mode=%s, port=%d); real impl in Phase 1d", "http" if args.http else "stdio", args.port)
    while _running:
        time.sleep(1)
    log.info("STUB exiting cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

3. `server/app/scheduler/__init__.py`:
```python
"""APScheduler standalone process package (full implementation in Phase 4)."""
```

4. `server/app/scheduler/run.py`:
```python
"""APScheduler process entry point.

Phase 1a: STUB — starts, logs a banner, blocks until SIGTERM. Real APScheduler
3.x SQLAlchemyJobStore wiring lands in Phase 4. Supervisord program priority
40 invokes this as: python -m app.scheduler.run
"""
from __future__ import annotations

import logging
import signal
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [scheduler.run] %(message)s")
log = logging.getLogger("smart_copilot.scheduler")

_running = True


def _handle_signal(signum, frame):  # noqa: ARG001
    global _running
    log.info("received signal %s; shutting down", signum)
    _running = False


def main() -> int:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    log.info("STUB starting; real APScheduler 3.x impl in Phase 4")
    while _running:
        time.sleep(1)
    log.info("STUB exiting cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

5. `server/app/vault/__init__.py`:
```python
"""Vault filesystem observer package (full implementation in Phase 1c)."""
```

6. `server/app/vault/watcher.py`:
```python
"""Vault watchdog process entry point.

Phase 1a: STUB — starts, logs a banner, blocks until SIGTERM. Real watchdog
inotify -> asyncio handoff lands in Phase 1c (REQ VAULT-09 / IDX-01).
Supervisord program priority 50 invokes this as: python -m app.vault.watcher
"""
from __future__ import annotations

import logging
import signal
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [vault.watcher] %(message)s")
log = logging.getLogger("smart_copilot.vault")

_running = True


def _handle_signal(signum, frame):  # noqa: ARG001
    global _running
    log.info("received signal %s; shutting down", signum)
    _running = False


def main() -> int:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    log.info("STUB starting; real watchdog impl in Phase 1c")
    while _running:
        time.sleep(1)
    log.info("STUB exiting cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

After writing, smoke test each stub on the host: `cd server && timeout 2 python -m app.mcp.server --http; echo $?` should exit non-zero (timeout — process was running). Same for scheduler.run and vault.watcher.
  </action>
  <verify>
    <automated>for f in mcp/server scheduler/run vault/watcher; do test -f "server/app/$f.py" || { echo "missing $f"; exit 1; }; done && (cd server && ruff check app/mcp app/scheduler app/vault) && (cd server && timeout 2 python -m app.mcp.server --http; rc=$?; test $rc -ne 0 || (echo "stub exited too early"; exit 1)) && (cd server && timeout 2 python -m app.scheduler.run; rc=$?; test $rc -ne 0 || exit 1) && (cd server && timeout 2 python -m app.vault.watcher; rc=$?; test $rc -ne 0 || exit 1)</automated>
  </verify>
  <acceptance_criteria>
    - All 6 files exist
    - Each stub has a `main()` function that calls `signal.signal(signal.SIGTERM, ...)` and blocks in a `while _running` loop
    - Each stub uses the standard `logging` module to emit a startup banner
    - `cd server && timeout 2 python -m app.mcp.server --http` is killed by timeout (exit code != 0) — confirms it would block forever
    - Same for `app.scheduler.run` and `app.vault.watcher`
    - `cd server && ruff check app/mcp app/scheduler app/vault` exits 0
  </acceptance_criteria>
  <done>3 process stubs in place; each runs as `python -m app.<pkg>.<module>` and blocks until SIGTERM; ruff clean.</done>
</task>

<task type="auto">
  <name>Task 2: Author supervisord.conf, wait-for-pg.sh, docker-entrypoint.sh, .dockerignore</name>
  <files>server/supervisord.conf, server/scripts/wait-for-pg.sh, server/scripts/docker-entrypoint.sh, server/.dockerignore</files>
  <read_first>
    - .planning/phases/01a-container-data-layer/01a-RESEARCH.md (Pattern 1: canonical supervisord.conf; Pattern 2: wait-for-pg.sh; Pitfall 1: pgvector:pg16 image initdb behavior)
    - .planning/phases/01a-container-data-layer/01a-CONTEXT.md (D-09 alembic uses psycopg2; PRD §30I priority order)
    - CLAUDE.md (Process Management: nodaemon=true; priorities 10/20/30/40/50; logs to /dev/fd/1 and /dev/fd/2; never log to files)
    - docs/product_requirements_document_v26.05.md §30I (canonical Dockerfile, supervisord.conf, wait-for-pg.sh)
  </read_first>
  <action>
Author the runtime/init scripts. Every value is concrete — no placeholders.

1. `server/supervisord.conf`:

```ini
; Smart Copilot — supervisord PID 1 configuration (CLAUDE.md / PRD §30I.2).
; Priority order: postgresql(10) -> fastapi(20) -> mcp-http(30) -> apscheduler(40) -> watchdog(50).
; All log output routes to /dev/fd/1 and /dev/fd/2 so `docker logs` captures it (CLAUDE.md).

[supervisord]
nodaemon=true
user=root
logfile=/dev/null
logfile_maxbytes=0
pidfile=/tmp/supervisord.pid

[unix_http_server]
file=/tmp/supervisor.sock
chmod=0700

[supervisorctl]
serverurl=unix:///tmp/supervisor.sock

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[program:postgresql]
command=/usr/lib/postgresql/16/bin/postgres -D /data/postgresql -c config_file=/etc/postgresql/postgresql.conf
user=postgres
autostart=true
autorestart=true
priority=10
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
stderr_logfile=/dev/fd/2
stderr_logfile_maxbytes=0

[program:fastapi]
command=/app/scripts/wait-for-pg.sh
directory=/app
autostart=true
autorestart=true
priority=20
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
stderr_logfile=/dev/fd/2
stderr_logfile_maxbytes=0

[program:mcp-http]
command=python3 -m app.mcp.server --http --port 8787
directory=/app
autostart=true
autorestart=true
priority=30
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
stderr_logfile=/dev/fd/2
stderr_logfile_maxbytes=0

[program:apscheduler]
command=python3 -m app.scheduler.run
directory=/app
autostart=true
autorestart=true
priority=40
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
stderr_logfile=/dev/fd/2
stderr_logfile_maxbytes=0

[program:watchdog]
command=python3 -m app.vault.watcher
directory=/app
autostart=true
autorestart=true
priority=50
stdout_logfile=/dev/fd/1
stdout_logfile_maxbytes=0
stderr_logfile=/dev/fd/2
stderr_logfile_maxbytes=0
```

2. `server/scripts/wait-for-pg.sh` (must be `chmod +x`):

```bash
#!/bin/bash
# Smart Copilot — wait for PostgreSQL, run Alembic migrations, then start uvicorn.
# Source: PRD §30I.3 + CLAUDE.md (asyncpg runtime, psycopg2 Alembic).
set -e

echo "[wait-for-pg] Waiting for PostgreSQL..."
until pg_isready -h localhost -p 5432 -U "${POSTGRES_USER:-smartcopilot}" -q; do
  sleep 1
done
echo "[wait-for-pg] PostgreSQL is ready."

echo "[wait-for-pg] Running alembic upgrade head..."
cd /app
python3 -m alembic upgrade head
echo "[wait-for-pg] Alembic migrations complete."

echo "[wait-for-pg] Starting uvicorn (workers=2)..."
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

3. `server/scripts/docker-entrypoint.sh` (must be `chmod +x`):

This handles Pitfall 1 — when supervisord replaces the postgres image's default entrypoint, `initdb` no longer runs. We must run it ourselves on first boot.

```bash
#!/bin/bash
# Smart Copilot — first-boot initialization (Pitfall 1 / RESEARCH.md).
# When supervisord replaces the postgres image entrypoint, initdb does NOT run
# automatically. This script handles first-boot initialization idempotently.
set -e

DATA_DIR=/data/postgresql
POSTGRES_USER=${POSTGRES_USER:-smartcopilot}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-smartcopilot}
POSTGRES_DB=${POSTGRES_DB:-smartcopilot}

# Ensure the volume root exists with correct ownership.
mkdir -p /data/postgresql /vaults /config
chown -R postgres:postgres /data/postgresql

# First-boot initdb if the data directory is empty.
if [ -z "$(ls -A "$DATA_DIR" 2>/dev/null)" ]; then
  echo "[entrypoint] Empty data dir detected; running initdb as user=postgres..."
  # Do NOT override --auth-* flags — preserve the pgvector image's pg_hba.conf.
  # The pgvector/pgvector:pg16 image ships with peer auth for local and md5 for host.
  # Initdb creates a fresh pg_hba.conf; we configure it for md5 auth on both local
  # and host connections so our smartcopilot superuser can connect with a password.
  su postgres -c "/usr/lib/postgresql/16/bin/initdb -D $DATA_DIR --username=postgres"
  # Append md5 auth rules to pg_hba.conf (appended after initdb's defaults so
  # later rules take precedence). This works regardless of the image's pg_hba.conf
  # because we're replacing the trust rules with password auth.
  printf "local all all md5\nhost all all 127.0.0.1/32 md5\nhost all all ::1/128 md5\n" >> "$DATA_DIR/pg_hba.conf"

  echo "[entrypoint] Starting postgres temporarily to create role/db..."
  su postgres -c "/usr/lib/postgresql/16/bin/pg_ctl -D $DATA_DIR -o '-c config_file=/etc/postgresql/postgresql.conf' -w start"
  su postgres -c "psql -v ON_ERROR_STOP=1 --command \"CREATE USER ${POSTGRES_USER} WITH SUPERUSER PASSWORD '${POSTGRES_PASSWORD}';\""
  su postgres -c "psql -v ON_ERROR_STOP=1 --command \"CREATE DATABASE ${POSTGRES_DB} OWNER ${POSTGRES_USER};\""
  su postgres -c "psql -v ON_ERROR_STOP=1 --dbname ${POSTGRES_DB} --command \"CREATE EXTENSION IF NOT EXISTS vector;\""
  su postgres -c "/usr/lib/postgresql/16/bin/pg_ctl -D $DATA_DIR -m fast -w stop"
  echo "[entrypoint] First-boot initialization complete."
else
  echo "[entrypoint] Existing data directory detected; skipping initdb."
fi

# Hand off to supervisord (PID 1).
exec /usr/bin/supervisord -c /etc/supervisord.conf
```

4. `server/.dockerignore`:

```
# Smart Copilot — Docker build context excludes
.git
.gitignore
.env
.env.local
.env.*.local
__pycache__
*.pyc
*.pyo
.pytest_cache
.ruff_cache
*.egg-info
.venv
venv
node_modules
.pnpm-store
docker-compose.yml
.planning
docs
clients
```

After writing, run `chmod +x server/scripts/wait-for-pg.sh server/scripts/docker-entrypoint.sh` and `bash -n server/scripts/wait-for-pg.sh server/scripts/docker-entrypoint.sh` (syntax check).
  </action>
  <verify>
    <automated>test -f server/supervisord.conf && test -f server/scripts/wait-for-pg.sh && test -f server/scripts/docker-entrypoint.sh && test -f server/.dockerignore && test -x server/scripts/wait-for-pg.sh && test -x server/scripts/docker-entrypoint.sh && grep -q '^nodaemon=true' server/supervisord.conf && grep -q '^priority=10' server/supervisord.conf && grep -q '^priority=20' server/supervisord.conf && grep -q '^priority=30' server/supervisord.conf && grep -q '^priority=40' server/supervisord.conf && grep -q '^priority=50' server/supervisord.conf && [ "$(grep -c '^stdout_logfile=/dev/fd/1' server/supervisord.conf)" -ge 5 ] && [ "$(grep -c '^stderr_logfile=/dev/fd/2' server/supervisord.conf)" -ge 5 ] && grep -q 'wait-for-pg.sh' server/supervisord.conf && grep -q 'app.mcp.server' server/supervisord.conf && grep -q 'app.scheduler.run' server/supervisord.conf && grep -q 'app.vault.watcher' server/supervisord.conf && grep -q 'pg_isready' server/scripts/wait-for-pg.sh && grep -q 'alembic upgrade head' server/scripts/wait-for-pg.sh && grep -q 'uvicorn' server/scripts/wait-for-pg.sh && grep -q 'initdb' server/scripts/docker-entrypoint.sh && grep -q 'CREATE EXTENSION IF NOT EXISTS vector' server/scripts/docker-entrypoint.sh && grep -q '^.env$' server/.dockerignore && bash -n server/scripts/wait-for-pg.sh && bash -n server/scripts/docker-entrypoint.sh</automated>
  </verify>
  <acceptance_criteria>
    - `server/supervisord.conf` contains exact substring `nodaemon=true` (CLAUDE.md INFRA-01)
    - `server/supervisord.conf` defines exactly 5 `[program:*]` sections: postgresql, fastapi, mcp-http, apscheduler, watchdog
    - `server/supervisord.conf` defines all 5 priorities: 10, 20, 30, 40, 50 (each as its own line `priority=N`)
    - `server/supervisord.conf` has at least 5 lines `stdout_logfile=/dev/fd/1` and 5 lines `stderr_logfile=/dev/fd/2` (one per program — CLAUDE.md)
    - `server/supervisord.conf` does NOT reference any log file path under `/var/log` or `/app/logs` (CLAUDE.md: never log to files)
    - `server/scripts/wait-for-pg.sh` is executable (`test -x` returns 0) and contains `pg_isready`, `alembic upgrade head`, `uvicorn`
    - `server/scripts/docker-entrypoint.sh` is executable, contains `initdb`, `CREATE EXTENSION IF NOT EXISTS vector`, and `exec /usr/bin/supervisord`
    - `server/scripts/docker-entrypoint.sh` is idempotent (guards initdb behind empty-dir check)
    - `server/.dockerignore` excludes `.env`, `.git`, `.planning`, `__pycache__`, `node_modules`
    - `bash -n` passes on both shell scripts (syntax valid)
  </acceptance_criteria>
  <done>supervisord.conf + wait-for-pg.sh + docker-entrypoint.sh + .dockerignore committed; all 5 priorities present; logs route to /dev/fd/1+2; first-boot initdb idempotent; ready for Dockerfile.</done>
</task>

<task type="auto">
  <name>Task 3: Author production Dockerfile (FROM pgvector/pgvector:pg16) — multi-stage Python 3.12</name>
  <files>server/Dockerfile</files>
  <read_first>
    - .planning/phases/01a-container-data-layer/01a-RESEARCH.md (System Architecture Diagram — volumes, ports; Standard Stack — version pins)
    - .planning/phases/01a-container-data-layer/01a-CONTEXT.md (D-10/D-11: monolithic image for prod)
    - server/requirements.txt (runtime deps to install)
    - server/supervisord.conf (Task 2 — entrypoint target)
    - server/scripts/wait-for-pg.sh + server/scripts/docker-entrypoint.sh (Task 2 outputs)
    - CLAUDE.md (base image MUST be pgvector/pgvector:pg16; volumes /data /vaults /config; INFRA-08)
  </read_first>
  <action>
Create `server/Dockerfile`. The base image `pgvector/pgvector:pg16` ships PostgreSQL + the pgvector extension pre-built (avoids compile). We use a multi-stage build: stage 1 pulls Python 3.12 from the official `python:3.12-slim` image, stage 2 layers `python3.12` onto the pgvector base alongside supervisord, our application, and our scripts. This avoids the slow source compile (W3) and keeps build time under 2 minutes.

```dockerfile
# syntax=docker/dockerfile:1.6
# Smart Copilot — monolithic production container (multi-stage).
# CLAUDE.md: base MUST be pgvector/pgvector:pg16; supervisord PID 1; volumes /data /vaults /config.

# Stage 1 — provide a Python 3.12 install we can copy into the runtime image.
FROM python:3.12-slim AS pybase

# Stage 2 — runtime image: pgvector + postgres + supervisord + python3.12.
FROM pgvector/pgvector:pg16

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/python3.12/bin:${PATH}"

# Copy the entire Python 3.12 install from the slim image into /opt/python3.12.
# python:3.12-slim installs Python under /usr/local; copy it as a self-contained tree.
COPY --from=pybase /usr/local /opt/python3.12

# System deps: supervisord, postgres client (for pg_isready in wait-for-pg.sh), build basics
# for any wheels that need a compiler (asyncpg/psycopg2 ship manylinux wheels — usually none needed).
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        supervisor \
        postgresql-client-16 \
        libpq5 \
 && ln -sf /opt/python3.12/bin/python3.12 /usr/local/bin/python3 \
 && ln -sf /opt/python3.12/bin/python3.12 /usr/local/bin/python \
 && ln -sf /opt/python3.12/bin/pip3.12 /usr/local/bin/pip3 \
 && ln -sf /opt/python3.12/bin/pip3.12 /usr/local/bin/pip \
 && python3 --version | grep '3.12' \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# Application directory.
WORKDIR /app

# Install Python deps first for layer caching.
COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt

# Copy application sources.
COPY app /app/app
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini
COPY scripts /app/scripts

# Copy supervisord.conf to canonical location.
COPY supervisord.conf /etc/supervisord.conf

# A minimal postgresql.conf (PRD §30I). Allow connections from localhost only;
# data dir is /data/postgresql. listen_addresses must include localhost so pg_isready works.
RUN mkdir -p /etc/postgresql /data/postgresql /vaults /config \
 && printf 'listen_addresses = '"'"'localhost'"'"'\nport = 5432\nmax_connections = 100\nshared_buffers = 128MB\nlog_destination = '"'"'stderr'"'"'\nlogging_collector = off\n' > /etc/postgresql/postgresql.conf \
 && chmod +x /app/scripts/wait-for-pg.sh /app/scripts/docker-entrypoint.sh

# INFRA-08: Volumes /data (PostgreSQL), /vaults (markdown), /config.
VOLUME ["/data", "/vaults", "/config"]

# Ports: 8000 (FastAPI), 8787 (MCP HTTP).
EXPOSE 8000 8787

# Healthcheck — calls /health (FastAPI) once available.
HEALTHCHECK --interval=15s --timeout=5s --retries=10 --start-period=45s \
  CMD curl -fsSL http://localhost:8000/health || exit 1

# Entrypoint runs first-boot initdb then exec's supervisord (PID 1).
ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
```

NOTE on multi-stage build: `python:3.12-slim` ships Python 3.12 under `/usr/local`; copying `/usr/local` from that image into `/opt/python3.12` yields a fully self-contained Python install. Build time drops from ~10 minutes (source compile) to under 2 minutes.

After writing the Dockerfile, the executor MUST run the live build + boot smoke sequence (this lives outside `<verify>` because docker build can take minutes — verify is static-only):

Smoke test sequence (executor runs this manually after writing the file; do NOT put it in `<verify>`):
```bash
# Build
docker build -t smart-copilot:test server/

# Run with all volumes (INFRA-08)
docker run -d --name sc-smoke \
  -v sc_data:/data -v sc_vaults:/vaults -v sc_config:/config \
  -p 18000:8000 -p 18787:8787 \
  -e SMARTCOPILOT_FERNET_KEY=dummy_phase1a \
  -e DATABASE_URL=postgresql+asyncpg://smartcopilot:smartcopilot@localhost:5432/smartcopilot \
  -e ALEMBIC_DATABASE_URL=postgresql+psycopg2://smartcopilot:smartcopilot@localhost:5432/smartcopilot \
  smart-copilot:test

# Wait for boot (INFRA-02: 30s)
sleep 35

# All 5 programs RUNNING?
docker exec sc-smoke supervisorctl status | tee /tmp/sc-status.txt
test "$(grep -c RUNNING /tmp/sc-status.txt)" -eq 5

# /health returns 200?
curl -fsSL http://localhost:18000/health | grep -q '"status":"ok"'

# pgvector extension present?
docker exec sc-smoke su postgres -c 'psql -d smartcopilot -c "SELECT extname FROM pg_extension WHERE extname='\''vector'\'';"' | grep vector

# Cleanup
docker rm -f sc-smoke
docker volume rm sc_data sc_vaults sc_config
```

If any step fails, dump `docker logs sc-smoke`, fix the Dockerfile, rebuild. The Dockerfile MUST allow this smoke sequence to pass on a clean machine. Live boot verification is also performed by the human checkpoint Task 4.
  </action>
  <verify>
    <automated>test -f server/Dockerfile && grep -q '^FROM pgvector/pgvector:pg16' server/Dockerfile && grep -q 'FROM python:3.12-slim AS pybase' server/Dockerfile && grep -q 'COPY --from=pybase /usr/local /opt/python3.12' server/Dockerfile && grep -q '^VOLUME \["/data", "/vaults", "/config"\]' server/Dockerfile && grep -q '^EXPOSE 8000 8787' server/Dockerfile && grep -q 'ENTRYPOINT.*docker-entrypoint.sh' server/Dockerfile && grep -q 'HEALTHCHECK' server/Dockerfile && grep -q 'supervisor' server/Dockerfile && grep -q 'postgresql-client-16' server/Dockerfile && grep -q "python3 --version | grep '3.12'" server/Dockerfile && grep -q 'pip3 install --no-cache-dir -r /app/requirements.txt' server/Dockerfile</automated>
  </verify>
  <acceptance_criteria>
    - `server/Dockerfile` declares the pybase stage `FROM python:3.12-slim AS pybase`
    - `server/Dockerfile` runtime stage line is `FROM pgvector/pgvector:pg16` (CLAUDE.md base image mandate)
    - `server/Dockerfile` copies the python install with `COPY --from=pybase /usr/local /opt/python3.12`
    - `server/Dockerfile` declares `VOLUME ["/data", "/vaults", "/config"]` (INFRA-08 — exact paths)
    - `server/Dockerfile` declares `EXPOSE 8000 8787` (REST + MCP HTTP)
    - `server/Dockerfile` `ENTRYPOINT` references `docker-entrypoint.sh`
    - `server/Dockerfile` installs supervisord via apt
    - `server/Dockerfile` has a `python3 --version | grep '3.12'` build assertion
    - `server/Dockerfile` runs `pip3 install -r requirements.txt`
    - `server/Dockerfile` defines a HEALTHCHECK calling `/health`
    - Executor MANUALLY confirms (outside verify): `docker build -t smart-copilot:plan04-test server/` succeeds; `docker run` then 40s sleep yields ≥5 RUNNING programs; `curl /health` returns `{"status":"ok"}`; `vector` extension reachable; smoke container/volumes cleaned up afterward
  </acceptance_criteria>
  <done>Production Dockerfile committed (multi-stage, Python 3.12 from python:3.12-slim, ~2min build). Static structure verified by automated grep gate. Live boot verified by executor smoke run + human checkpoint Task 4.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 4: Human-verify the live container boot meets the 3 manual-only success criteria</name>
  <files>(no files modified — verification-only checkpoint)</files>
  <read_first>
    - .planning/ROADMAP.md (Phase 1a Success Criteria 1-3)
    - .planning/phases/01a-container-data-layer/01a-VALIDATION.md (Manual-Only Verifications table)
  </read_first>
  <action>This is a human-verify checkpoint. Claude does NOT implement anything in this task. The user (developer) must execute the verification steps in the `<how-to-verify>` block below on their local machine and report back via the `<resume-signal>` mechanism. Claude waits for explicit "approved" before considering Phase 1a complete.

This checkpoint covers ONLY the criteria that require live container observation. pytest (criterion 4) and Ruff/pre-commit (criterion 5) are already automated by Plans 01 and 03 — those do not need re-verification here.</action>
  <acceptance_criteria>
    - Developer reports CRITERION 1 passing: `supervisorctl status` shows 5 RUNNING lines within 30 seconds of `docker run`
    - Developer reports CRITERION 2 passing: `CREATE EXTENSION IF NOT EXISTS vector` and `SELECT extname FROM pg_extension WHERE extname='vector'` both succeed inside the container
    - Developer reports CRITERION 3 passing: `curl http://localhost:8000/health` returns 200 with body `{"status":"ok"}`; container logs show Alembic completion before uvicorn startup
    - Developer issues "approved" signal (or specific failure description for remediation)
  </acceptance_criteria>
  <what-built>
The full Phase 1a stack:
- `docker build -t smart-copilot:test server/` produces the monolithic image
- supervisord runs as PID 1 with 5 programs (postgresql, fastapi, mcp-http, apscheduler, watchdog) at priorities 10/20/30/40/50
- PostgreSQL 16 + pgvector boots; Alembic upgrades the schema; uvicorn binds :8000
- /health returns {"status": "ok"} after the boot sequence completes
- Volumes /data /vaults /config persist across container restarts

Note: pytest test suite and Ruff/pre-commit gates are validated automatically by Plans 01 and 03 — they are not in this checkpoint's scope.
  </what-built>
  <how-to-verify>
On the developer machine, run the following sequence and confirm each numbered check matches the Phase 1a success criteria from ROADMAP.md.

1. Build:
   ```bash
   docker build -t smart-copilot:phase1a server/
   ```
   Expect: build succeeds.

2. Boot:
   ```bash
   docker run -d --name sc-phase1a \
     -v sc_data:/data -v sc_vaults:/vaults -v sc_config:/config \
     -p 8000:8000 -p 8787:8787 \
     -e SMARTCOPILOT_FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())") \
     -e DATABASE_URL=postgresql+asyncpg://smartcopilot:smartcopilot@localhost:5432/smartcopilot \
     -e ALEMBIC_DATABASE_URL=postgresql+psycopg2://smartcopilot:smartcopilot@localhost:5432/smartcopilot \
     smart-copilot:phase1a
   sleep 35
   ```

3. CRITERION 1 — supervisord 5 programs RUNNING within 30s:
   ```bash
   docker exec sc-phase1a supervisorctl status
   ```
   Expect: 5 lines, every line ending in `RUNNING`.

4. CRITERION 2 — pgvector extension reachable:
   ```bash
   docker exec sc-phase1a su postgres -c 'psql -d smartcopilot -c "CREATE EXTENSION IF NOT EXISTS vector;"'
   docker exec sc-phase1a su postgres -c 'psql -d smartcopilot -c "SELECT extname FROM pg_extension WHERE extname='\''vector'\'';"'
   ```
   Expect: command succeeds, query returns one row showing `vector`.

5. CRITERION 3 — Alembic ran before uvicorn; /health returns 200:
   ```bash
   curl -i http://localhost:8000/health
   docker logs sc-phase1a 2>&1 | grep -E "alembic|Application startup"
   ```
   Expect: HTTP 200 with body `{"status":"ok"}`. In logs, "Alembic migrations complete" appears BEFORE "Application startup complete" (or equivalent uvicorn ready line).

6. Cleanup:
   ```bash
   docker rm -f sc-phase1a
   docker volume rm sc_data sc_vaults sc_config
   ```
  </how-to-verify>
  <resume-signal>Type "approved" if all 3 criteria pass, or describe which criterion failed and what you observed in `docker logs sc-phase1a`.</resume-signal>
  <verify>
    <automated>echo "checkpoint:human-verify — automated portion runs in Tasks 1-3 of this plan; this task is gated on developer approval"</automated>
  </verify>
  <done>Developer issues "approved" after all 3 live-container criteria from ROADMAP.md are observed passing on their machine.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| host -> container | Volumes `/data`, `/vaults`, `/config` cross this boundary; container UID matters for write access |
| supervisord -> child processes | postgres runs as `user=postgres`; other processes run as root (Phase 1a constraint) |
| container -> external network | Only ports 8000 (REST) and 8787 (MCP HTTP) exposed; postgres :5432 is internal only (`listen_addresses = 'localhost'`) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-1a-01 | Information Disclosure | `SMARTCOPILOT_FERNET_KEY` env var | mitigate | Documented in `.env.example` (Plan 01) with placeholder only; never logged by application code in Phase 1a (defensive logging redaction lands in Phase 6 / structlog). Container runtime accepts the key via `-e` env var; absent value = boot continues but Phase 1b will refuse to boot when crypto is wired in (CLAUDE.md constraint) |
| T-1a-03 | Elevation of Privilege | postgres process running with appropriate user | mitigate | `[program:postgresql]` uses `user=postgres` per CLAUDE.md / PRD §30I.2 — verifiable in supervisord.conf and acceptance criterion |
| T-1a-12 | Denial of Service | postgres listening on all interfaces | mitigate | postgresql.conf in Dockerfile sets `listen_addresses = 'localhost'`; only fastapi/mcp inside the container connect; external network can only reach :8000 and :8787 |
| T-1a-13 | Tampering | Volume escape via mount paths | accept (Phase 1c) | Path validation for `/vaults` is a Phase 1c concern (REQ VAULT-04, VAULT-09). Phase 1a only declares the volume; tenant-scoped path validation lands when watchdog/page CRUD layer is built |
| T-1a-14 | Information Disclosure | docker logs leaking secrets | accept | Phase 1a app code does not log `SMARTCOPILOT_FERNET_KEY` or any other secret. supervisord logs go to /dev/fd/1 + /dev/fd/2 (CLAUDE.md). Field-level redaction belongs to Phase 6 structlog config |
</threat_model>

<verification>
- `docker build -t smart-copilot:test server/` exits 0
- `docker run -d ...` produces a container that, after 30-40s, has 5 supervisord programs RUNNING
- `curl http://localhost:8000/health` returns `{"status": "ok"}` with HTTP 200
- `psql -d smartcopilot -c "SELECT extname FROM pg_extension WHERE extname='vector';"` inside container returns one row
- Volumes `/data`, `/vaults`, `/config` declared in Dockerfile (`docker inspect` confirms)
- supervisord.conf priorities are exactly 10/20/30/40/50; logs route to /dev/fd/1 and /dev/fd/2 only
- Phase 1a success criteria 1, 2, 3 satisfied (criteria 4, 5 satisfied by Plan 01 + Plan 03)
</verification>

<success_criteria>
- INFRA-01: supervisord nodaemon=true is PID 1 in the production container
- INFRA-02: 5 programs (postgresql, fastapi, mcp-http, apscheduler, watchdog) declared at priorities 10/20/30/40/50, all reach RUNNING within 30 seconds of boot
- INFRA-03: pgvector extension available in container; CREATE EXTENSION IF NOT EXISTS vector succeeds inside the container
- INFRA-08: Volumes /data, /vaults, /config declared in Dockerfile and writable when mounted
- Phase 1a success criterion 1 (supervisord 5 RUNNING in 30s) — VERIFIED by Task 4 checkpoint
- Phase 1a success criterion 2 (pgvector reachable inside container) — VERIFIED by Task 4 checkpoint
- Phase 1a success criterion 3 (Alembic before uvicorn; /health 200) — VERIFIED by Task 4 checkpoint
- Logs route to /dev/fd/1 and /dev/fd/2 only (CLAUDE.md anti-pattern: never log to files inside the container)
</success_criteria>

<output>
After completion, create `.planning/phases/01a-container-data-layer/01a-04-SUMMARY.md` with:
- Files created
- Image build duration (multi-stage build typically 1-2 min; document the actual time)
- supervisorctl status output (the 5 RUNNING lines)
- /health response body and headers
- pg_extension query result
- Any deviations
- Confirmation that Task 4 human checkpoint was approved
</output>
</content>
</invoke>