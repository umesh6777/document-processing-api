from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration, read from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Document Management API"
    database_url: str = "sqlite:///./app.db"
    upload_dir: str = "uploads"
    max_upload_size_mb: int = Field(default=10, gt=0)
    processing_delay_seconds: float = Field(default=2.0, ge=0)
    # Share of uploads (0..1) that fail on purpose, to demo the 'failed' state.
    processing_failure_rate: float = Field(default=0.0, ge=0, le=1)

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
