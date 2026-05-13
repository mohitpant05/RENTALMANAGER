from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://rentmanager:rentmanager_dev@localhost:5432/rentmanager"
    database_url_sync: str = "postgresql://rentmanager:rentmanager_dev@localhost:5432/rentmanager"
    redis_url: str = "redis://localhost:6379/0"
    meili_url: str = "http://localhost:7700"
    meili_master_key: str = "masterkey_dev"
    minio_endpoint: str = "localhost:9000"
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "minioadmin_dev"
    secret_key: str = "dev-secret-key-change-in-production"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    jwt_algorithm: str = "HS256"

    frontend_url: str = "http://localhost:3000"
    invite_token_expire_hours: int = 72

    email_provider: str = "console"
    email_from: str = "noreply@rentmanager.dev"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    mandrill_api_key: str = ""

    superadmin_secret_key: str = "change-me-in-production-min-32-chars!!"
    allowed_superadmin_ips: str = ""

    register_rate_limit: str = "30/minute"

    debug: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
