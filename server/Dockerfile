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