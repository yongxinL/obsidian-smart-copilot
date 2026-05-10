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
