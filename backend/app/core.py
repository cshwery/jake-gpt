from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "JakeGPT"
    database_url: str = "postgresql+psycopg://jakegpt:jakegpt@localhost:5432/jakegpt"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "change-me-in-local-env"
    access_token_minutes: int = 60 * 12
    cors_origins: str = "http://localhost:3000"
    geocoder_api_key: str | None = None
    mapbox_access_token: str | None = None
    geocoder_provider: str = "mock"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
