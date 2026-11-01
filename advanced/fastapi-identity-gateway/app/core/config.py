from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment configuration. Copy `.env.example` and change names per project."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Identity Gateway API"
    app_version: str = "1.0.0"
    environment: str = "local"
    debug: bool = False
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    database_url: str = "sqlite+aiosqlite:///./identity_gateway.db"
    admin_api_key: str = "dev-admin-key-change-me"
    secret_key: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14
    client_secret_pepper: str = "dev-client-pepper-change-me"
    token_issuer: str = "http://127.0.0.1:8000"
    token_audience: str = "identity-gateway"
    authorization_code_ttl_minutes: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
