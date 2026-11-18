"""Register all email-service models with its isolated metadata."""

from app.models.email import (
    EmailDeliveryAttempt,
    EmailLog,
    EmailProviderSetting,
    EmailTemplate,
)

__all__ = ["EmailDeliveryAttempt", "EmailLog", "EmailProviderSetting", "EmailTemplate"]
