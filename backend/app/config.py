"""Central configuration for SentinelX backend, loaded from environment variables."""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "SentinelX"
    ENV: str = os.getenv("ENV", "development")

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "sqlite:///./sentinelx.db"
    )

    # Security
    API_KEY: str = os.getenv("API_KEY", "dev-local-key")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")

    # LLM
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    # If true (or no API key present), agents run on a deterministic
    # rule-based mock LLM so the whole pipeline is demoable with zero keys.
    USE_MOCK_LLM: bool = os.getenv("USE_MOCK_LLM", "").lower() in ("1", "true", "yes") or not os.getenv("OPENAI_API_KEY")

    # Observability
    LANGCHAIN_TRACING_V2: str = os.getenv("LANGCHAIN_TRACING_V2", "false")
    LANGCHAIN_API_KEY: str = os.getenv("LANGCHAIN_API_KEY", "")
    LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "sentinelx")

    # Tools
    SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")
    THREAT_INTEL_TIMEOUT: float = float(os.getenv("THREAT_INTEL_TIMEOUT", "3"))

    # Risk thresholds
    RISK_APPROVAL_THRESHOLD: int = int(os.getenv("RISK_APPROVAL_THRESHOLD", "60"))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# Wire LangSmith / LangChain tracing env vars (no-op if keys absent).
if settings.LANGCHAIN_TRACING_V2.lower() == "true" and settings.LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
