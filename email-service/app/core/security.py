"""Service-to-service and administrative API-key checks."""

import hmac

from fastapi import HTTPException, Request, status

from app.core.config import get_settings


def _check_key(provided: str | None, expected, label: str) -> None:
    secret = expected.get_secret_value() if expected else ""
    if not secret:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"{label} is not configured",
        )
    if not provided or not hmac.compare_digest(provided, secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")


def require_service_key(request: Request) -> None:
    _check_key(
        request.headers.get("X-API-Key"),
        get_settings().email_service_api_key,
        "Email service API key",
    )


def require_admin_key(request: Request) -> None:
    _check_key(
        request.headers.get("X-Admin-API-Key"),
        get_settings().email_service_admin_api_key,
        "Email service admin API key",
    )
