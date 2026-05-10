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
