"""Central configuration for SentinelX backend, loaded from environment variables."""

import os
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


# Project root:
# sentinelx/
# ├── .env
# └── backend/
#     └── app/
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "SentinelX"
    ENV: str = "development"

    # Database
    DATABASE_URL: str = "sqlite:///./sentinelx.db"

    # Security
    API_KEY: str = "dev-local-key"
    CORS_ORIGINS: str = "*"

    # LLM
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Observability
    LANGCHAIN_TRACING_V2: str = "false"
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "sentinelx"

    # Tools
    SLACK_WEBHOOK_URL: str = ""
    THREAT_INTEL_TIMEOUT: float = 3.0

    # Risk thresholds
    RISK_APPROVAL_THRESHOLD: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


# Wire LangSmith / LangChain tracing env vars
# only when tracing is enabled.
if settings.LANGCHAIN_TRACING_V2.lower() == "true" and settings.LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT