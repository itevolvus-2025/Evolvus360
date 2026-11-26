"""Application settings loaded from environment variables and ``.env``."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Evolvus360 API"
    app_env: str = "development"
    debug: bool = False
    secret_key: SecretStr | None = None
    jwt_secret_key: SecretStr | None = None
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=15, gt=0)
    refresh_token_expire_days: int = Field(default=7, gt=0)
    password_reset_token_expire_minutes: int = Field(default=30, gt=0)
    dev_password_reset_token: str | None = None
    login_max_failed_attempts: int = Field(default=5, gt=0)
    login_lockout_minutes: int = Field(default=15, gt=0)
    email_service_base_url: str = "http://127.0.0.1:8001"
    email_service_api_key: SecretStr | None = None
    email_service_timeout_seconds: int = Field(default=10, ge=1, le=60)
    smtp_from_email: str | None = None
    frontend_reset_password_url: str = "http://localhost:4200/auth/reset-password"
    frontend_onboarding_url: str = "http://localhost:4200/onboarding"
    onboarding_invitation_expire_hours: int = Field(default=48, gt=0)
    temporary_password_expire_hours: int = Field(default=24, gt=0)
    frontend_login_url: str = "http://localhost:4200/auth/login"
    max_onboarding_file_size_bytes: int = Field(
        default=5 * 1024 * 1024, gt=0, le=5 * 1024 * 1024
    )
    private_upload_dir: str = "private_uploads"
    pii_encryption_key: SecretStr | None = None
    database_url: str | None = None
    db_pool_size: int = Field(default=10, ge=1)
    db_max_overflow: int = Field(default=20, ge=0)
    db_pool_timeout: int = Field(default=5, gt=0)
    db_pool_recycle: int = Field(default=1800, gt=0)
    db_pool_pre_ping: bool = True
    db_connect_timeout_seconds: int = Field(default=3, gt=0)
    db_readiness_timeout_seconds: int = Field(default=3, gt=0)
    frontend_url: str = "http://localhost:5173"
    log_level: str = "INFO"
    cors_allowed_origins: str | None = None
    cors_allowed_methods: str = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    cors_allowed_headers: str = "Authorization,Content-Type,Accept,X-Request-ID"
    cors_allow_credentials: bool = False
    enable_hsts: bool = False

    @property
    def cors_origins(self) -> list[str]:
        origins = self.cors_allowed_origins or self.frontend_url
        return [origin.strip() for origin in origins.split(",") if origin.strip()]

    @property
    def cors_methods(self) -> list[str]:
        return [
            method.strip()
            for method in self.cors_allowed_methods.split(",")
            if method.strip()
        ]

    @property
    def cors_headers(self) -> list[str]:
        return [
            header.strip()
            for header in self.cors_allowed_headers.split(",")
            if header.strip()
        ]

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        level = value.upper()
        if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("LOG_LEVEL must be a standard Python log level")
        return level

    @field_validator("jwt_algorithm")
    @classmethod
    def validate_jwt_algorithm(cls, value: str) -> str:
        algorithm = value.upper()
        if algorithm not in {"HS256", "HS384", "HS512"}:
            raise ValueError(
                "JWT_ALGORITHM must use a supported HMAC signing algorithm"
            )
        return algorithm

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_flag(cls, value: object) -> object:
        # Some deployment environments expose DEBUG with non-boolean labels.
        if isinstance(value, str) and value.lower() not in {
            "1",
            "0",
            "true",
            "false",
            "yes",
            "no",
            "on",
            "off",
        }:
            return False
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def empty_database_url_is_unset(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.cors_allow_credentials and "*" in self.cors_origins:
            raise ValueError("Wildcard CORS origins cannot be used with credentials")
        if self.app_env.lower() in {"prod", "production"}:
            secret = self.secret_key.get_secret_value() if self.secret_key else ""
            placeholder_terms = ("change-me", "replace", "example", "your-secret")
            if (
                len(secret) < 32
                or len(set(secret)) < 16
                or any(term in secret.lower() for term in placeholder_terms)
            ):
                raise ValueError(
                    "SECRET_KEY must be strong and non-placeholder, with at least "
                    "32 characters in production"
                )
            if self.debug:
                raise ValueError("DEBUG must be disabled in production")
            if not self.database_url:
                raise ValueError("DATABASE_URL is required in production")
            jwt_secret = (
                self.jwt_secret_key.get_secret_value() if self.jwt_secret_key else ""
            )
            if len(jwt_secret) < 32 or len(set(jwt_secret)) < 16:
                raise ValueError("JWT_SECRET_KEY must be strong in production")
            if not self.email_service_api_key:
                raise ValueError("EMAIL_SERVICE_API_KEY is required in production")
            if not self.email_service_base_url.lower().startswith("https://"):
                raise ValueError("EMAIL_SERVICE_BASE_URL must use HTTPS in production")
            if not self.pii_encryption_key:
                raise ValueError("PII_ENCRYPTION_KEY is required in production")
            if not self.frontend_onboarding_url.lower().startswith("https://"):
                raise ValueError("FRONTEND_ONBOARDING_URL must use HTTPS in production")
            if self.dev_password_reset_token:
                raise ValueError(
                    "DEV_PASSWORD_RESET_TOKEN is not allowed in production"
                )
        return self

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide immutable-by-convention settings instance."""
    return Settings()


settings = get_settings()
