"""Application configuration loaded from environment variables / .env."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ directory (this file lives in backend/app/core/)
BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Subscription Management System API"
    app_env: Literal["development", "test", "production"] = "development"
    api_prefix: str = "/api"
    log_level: str = "INFO"

    # Database
    database_url: str = (
        "mysql+pymysql://odoo_prelims:CHANGE_ME@127.0.0.1:3306/odoo_prelims?charset=utf8mb4"
    )
    test_database_url: str | None = None

    # JWT / sessions
    jwt_secret_key: SecretStr = SecretStr("replace-with-at-least-64-random-characters")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    password_reset_token_expire_minutes: int = 30

    # Frontend / CORS
    frontend_url: str = "http://localhost:5173"
    cors_origins: str = "http://localhost:5173"
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cookie_domain: str | None = None

    # Email
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from_email: str | None = None
    smtp_tls: bool = True
    mail_dev_dir: str = "var/mail"

    # Bootstrap admin (CLI only)
    admin_full_name: str = "System Administrator"
    admin_email: str | None = None
    admin_password: SecretStr | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def mail_dev_path(self) -> Path:
        path = Path(self.mail_dev_dir)
        return path if path.is_absolute() else BASE_DIR / path

    @model_validator(mode="after")
    def _validate_production_settings(self) -> "Settings":
        if self.app_env != "production":
            return self

        secret = self.jwt_secret_key.get_secret_value()
        if secret.startswith("replace-with") or len(secret) < 32:
            raise ValueError("JWT_SECRET_KEY must be a strong, non-default value in production.")
        if not self.cookie_secure:
            raise ValueError("COOKIE_SECURE must be true in production.")
        if not self.smtp_host:
            raise ValueError("SMTP_HOST is required in production.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
