from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration, read from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Document Management API"
    database_url: str = "sqlite:///./app.db"
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 10
    processing_delay_seconds: float = 2.0
    processing_failure_rate: float = 0.0  # 0..1, lets you demo the 'failed' state

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
