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
  su postgres -c "psql -v ON_ERROR_STOP=1 --command \"CREATE USER $(printf '%s' \"$POSTGRES_USER\") WITH SUPERUSER PASSWORD '$(printf '%s' \"$POSTGRES_PASSWORD\" | sed \"s/'/''/g\")';\""
  su postgres -c "psql -v ON_ERROR_STOP=1 --command \"CREATE DATABASE $(printf '%s' \"$POSTGRES_DB\") OWNER $(printf '%s' \"$POSTGRES_USER\");\""
  su postgres -c "psql -v ON_ERROR_STOP=1 --dbname=$(printf '%s' \"$POSTGRES_DB\") --command \"CREATE EXTENSION IF NOT EXISTS vector;\""
  su postgres -c "/usr/lib/postgresql/16/bin/pg_ctl -D $DATA_DIR -m fast -w stop"
  echo "[entrypoint] First-boot initialization complete."
else
  echo "[entrypoint] Existing data directory detected; skipping initdb."
fi

# Hand off to supervisord (PID 1).
exec /usr/bin/supervisord -c /etc/supervisord.conf