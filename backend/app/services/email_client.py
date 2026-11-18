"""HTTP-only client for the independent centralized email service."""

import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def send_email(
    *, template_key: str, recipient: str, variables: dict, idempotency_key: str
) -> bool:
    settings = get_settings()
    api_key = (
        settings.email_service_api_key.get_secret_value()
        if settings.email_service_api_key
        else ""
    )
    if not api_key:
        raise RuntimeError("Central email service API key is not configured")
    timeout = httpx.Timeout(
        settings.email_service_timeout_seconds,
        connect=min(3, settings.email_service_timeout_seconds),
    )
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                f"{settings.email_service_base_url.rstrip('/')}/api/v1/emails/send",
                headers={"X-API-Key": api_key, "Idempotency-Key": idempotency_key},
                json={
                    "application_name": "EVOLVUS_HRMS",
                    "to": [recipient],
                    "template_key": template_key,
                    "variables": variables,
                },
            )
        response.raise_for_status()
        payload = response.json().get("data") or {}
        return payload.get("status") == "SENT"
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "Central email service request failed",
            extra={"exception_type": type(exc).__name__},
        )
        raise RuntimeError("Central email service request failed") from None
