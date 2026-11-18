"""Independent email-service settings."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str | None = None
    email_service_api_key: SecretStr | None = None
    email_service_admin_api_key: SecretStr | None = None
    email_payload_encryption_key: SecretStr | None = None
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, gt=0, le=65535)
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from_email: str | None = None
    smtp_from_name: str = "Evolvus360"
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    smtp_timeout_seconds: int = Field(default=10, ge=1, le=60)
    max_attachment_size_bytes: int = Field(default=5 * 1024 * 1024, gt=0)
    max_total_attachment_size_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    max_retries: int = Field(default=3, ge=1, le=10)
    rate_limit_per_minute: int = Field(default=60, ge=1)
    log_level: str = "INFO"

    @model_validator(mode="after")
    def validate_settings(self) -> "Settings":
        if not self.smtp_use_ssl and not self.smtp_use_tls and self.smtp_port == 465:
            raise ValueError("SMTP port 465 requires SMTP_USE_SSL")
        if self.smtp_use_ssl and self.smtp_use_tls:
            raise ValueError("SMTP_USE_SSL and SMTP_USE_TLS cannot both be enabled")
        if bool(self.smtp_username) != bool(self.smtp_password):
            raise ValueError(
                "SMTP_USERNAME and SMTP_PASSWORD must be configured together"
            )
        if self.app_env.lower() in {"prod", "production"}:
            if not self.database_url:
                raise ValueError("DATABASE_URL is required in production")
            for secret_name, secret in (
                ("EMAIL_SERVICE_API_KEY", self.email_service_api_key),
                ("EMAIL_SERVICE_ADMIN_API_KEY", self.email_service_admin_api_key),
                ("EMAIL_PAYLOAD_ENCRYPTION_KEY", self.email_payload_encryption_key),
            ):
                raw = secret.get_secret_value() if secret else ""
                if len(raw) < 32 or len(set(raw)) < 16:
                    raise ValueError(
                        f"{secret_name} must be a strong secret in production"
                    )
            if not self.smtp_host or not self.smtp_from_email:
                raise ValueError(
                    "SMTP_HOST and SMTP_FROM_EMAIL are required in production"
                )
            if not (self.smtp_use_tls or self.smtp_use_ssl):
                raise ValueError("SMTP encryption is required in production")
        return self

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
