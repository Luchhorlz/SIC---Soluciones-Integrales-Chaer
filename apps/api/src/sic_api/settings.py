from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SIC API"
    app_env: str = "development"
    api_version: str = "0.1.0"
    database_url: str = "postgresql+asyncpg://sic:sic@127.0.0.1:5432/sic"
    internal_api_jwt_secret: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
