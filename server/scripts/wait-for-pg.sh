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