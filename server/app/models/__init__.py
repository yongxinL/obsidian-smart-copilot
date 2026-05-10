"""Domain models package — aggregate import for Alembic autogenerate.

Per D-05/D-06: every domain model defined up-front; single 0001_initial_schema.py
migration. Importing this package MUST cause every table to be registered with
Base.metadata so that alembic/env.py sees the complete schema.

Per D-07: one file per domain. The `tag` and `conversation` and `golden_eval`
modules each define multiple closely-related tables (page_tags join, messages,
golden_query_*); this is allowed under D-07.
"""

# Auth + identity
# Vault + content
# Background jobs + audit
# Skills, recipes, eval
# Agent: conversations, memories, dream
# Projects + operation log
# Observability
# Configuration
# Golden eval (Phase 2b)
from app.models import (
    audit_log,  # noqa: F401
    chunk,  # noqa: F401
    conversation,  # noqa: F401
    dream_audit_log,  # noqa: F401
    entity,  # noqa: F401
    eval_candidate,  # noqa: F401
    golden_eval,  # noqa: F401
    index_event,  # noqa: F401
    job,  # noqa: F401
    link,  # noqa: F401
    llm_usage,  # noqa: F401
    login_attempt,  # noqa: F401
    mcp_server,  # noqa: F401
    mcp_token,  # noqa: F401
    memory,  # noqa: F401
    operation_log,  # noqa: F401
    page,  # noqa: F401
    page_version,  # noqa: F401
    project,  # noqa: F401
    provider_key,  # noqa: F401
    recipe,  # noqa: F401
    session,  # noqa: F401
    skill,  # noqa: F401
    system_config,  # noqa: F401
    tag,  # noqa: F401
    timeline_event,  # noqa: F401
    user,  # noqa: F401
    user_settings,  # noqa: F401
    vault,  # noqa: F401
)
from app.models.base import Base, TimestampMixin

__all__ = ["Base", "TimestampMixin"]
