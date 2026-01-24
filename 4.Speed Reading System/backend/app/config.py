"""Application configuration settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite:///./data/deepread.db"

    # App
    app_name: str = "DeepRead"
    debug: bool = False

    # Limits
    max_document_words: int = 20_000
    chunk_size: int = 500
    session_expiry_days: int = 7

    # Future auth hook
    auth_enabled: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
