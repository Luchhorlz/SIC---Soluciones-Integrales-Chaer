from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SIC API"
    app_env: str = "development"
    api_version: str = "0.1.0"
    database_url: str = "postgresql+asyncpg://sic:sic@127.0.0.1:5432/sic"
    internal_api_jwt_secret: str | None = None
    s3_endpoint: str = "http://127.0.0.1:9000"
    s3_presign_endpoint: str | None = None
    s3_region: str = "us-east-1"
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_bucket_private: str = "sic-private"
    document_download_ttl_seconds: int = 60
    document_max_bytes: int = 10 * 1024 * 1024
    clamav_host: str = "127.0.0.1"
    clamav_port: int = 3310
    clamav_timeout_seconds: float = 15.0
    mercadopago_access_token: str | None = None
    mercadopago_webhook_secret: str | None = None
    mercadopago_success_url: str | None = None
    mercadopago_api_base_url: str = "https://api.mercadopago.com"
    mercadopago_webhook_tolerance_seconds: int = 300
    booking_address_encryption_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
