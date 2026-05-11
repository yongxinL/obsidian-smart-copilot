"""Application settings loaded from environment + .env file (D-13)."""

from __future__ import annotations

import warnings

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str = Field(
        default="postgresql+asyncpg://smartcopilot:smartcopilot@localhost:5432/smartcopilot"
    )
    alembic_database_url: str = Field(
        default="postgresql+psycopg2://smartcopilot:smartcopilot@localhost:5432/smartcopilot"
    )
    test_database_url: str = Field(default="")
    smartcopilot_fernet_key: str = Field(default="")
    smartcopilot_host_url: str = Field(default="http://localhost:8000")
    debug: bool = Field(default=False)

    # JWT (D-01, D-02)
    jwt_signing_key: str = Field(default="")
    jwt_access_ttl_seconds: int = Field(default=900)
    jwt_refresh_ttl_seconds: int = Field(default=2592000)

    # Argon2 (D-23 — PRD minima)
    argon2_time_cost: int = Field(default=3)
    argon2_memory_cost: int = Field(default=64 * 1024)
    argon2_parallelism: int = Field(default=1)

    # Login rate limit (D-05–D-09)
    login_rate_limit_window_seconds: int = Field(default=900)
    login_rate_limit_max_failures: int = Field(default=10)
    login_attempts_retention_hours: int = Field(default=24)

    # Step-up fresh auth (D-11–D-16)
    admin_fresh_window_minutes: int = Field(default=60)

    # Trusted proxy (D-29)
    smartcopilot_trust_proxy: bool = Field(default=False)
    smartcopilot_trusted_proxy_cidrs: list[str] = Field(default_factory=list)

    # --- Phase 1c: Vault + Watchdog Indexer ---
    # Per-path debounce for filesystem watchdog (D-07, DEC-003 from CLAUDE.md)
    # Env var: VAULT_WATCH_DEBOUNCE_MS (pydantic-settings maps snake_case to env without prefix)
    # D-07 specifies SMARTCOPILOT_VAULT_WATCH_DEBOUNCE_MS — use validation_alias to match:
    vault_watch_debounce_ms: int = Field(
        default=750,
        validation_alias="VAULT_WATCH_DEBOUNCE_MS",
    )
    # Shared vault write policy (VAULT-03) — "admin_only" | "all_users"
    shared_vault_write_policy: str = Field(default="admin_only")

    # --- Phase 1d: WebSocket + LISTEN/NOTIFY ---
    notify_dsn_asyncpg: str = Field(
        default="",
        validation_alias="SMARTCOPILOT_NOTIFY_DSN",
    )
    ws_first_frame_timeout_seconds: float = Field(default=10.0)

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
            raise ValueError(
                "smartcopilot_fernet_key must be at least 32 characters (44 base64 chars)"
            )
        return v


settings = Settings()


def get_notify_dsn() -> str:
    """Return raw asyncpg DSN for LISTEN/NOTIFY connection.

    Prefers SMARTCOPILOT_NOTIFY_DSN if set; otherwise derives from settings.database_url
    by stripping the '+asyncpg' driver suffix (asyncpg.connect takes a bare DSN).
    """
    if settings.notify_dsn_asyncpg:
        return settings.notify_dsn_asyncpg
    url = settings.database_url
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)
