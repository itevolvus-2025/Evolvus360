"""HRMS dispatch outbox helpers; delivery always crosses the HTTP boundary."""

import json
import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.session import SessionLocal
from app.models.hrms import EmailDispatchOutbox
from app.services.email_client import send_email

logger = logging.getLogger(__name__)


def enqueue(
    db: Session,
    *,
    entity_type: str,
    entity_id: UUID,
    recipient: str,
    template_key: str,
    variables: dict,
) -> EmailDispatchOutbox:
    key = get_settings().pii_encryption_key
    if not key:
        raise RuntimeError("PII_ENCRYPTION_KEY is required for secure email retry")
    encrypted = (
        Fernet(key.get_secret_value().encode())
        .encrypt(json.dumps(variables).encode())
        .decode()
    )
    row = EmailDispatchOutbox(
        entity_type=entity_type,
        entity_id=entity_id,
        recipient_email=recipient,
        template_key=template_key,
        idempotency_key=f"hrms-{entity_type.lower()}-{uuid4()}",
        encrypted_payload=encrypted,
    )
    db.add(row)
    db.flush()
    return row


def dispatch(dispatch_id: UUID) -> bool:
    """Call central service, then persist outcome in its own DB transaction."""
    db = SessionLocal()
    try:
        row = db.scalar(
            select(EmailDispatchOutbox).where(EmailDispatchOutbox.id == dispatch_id)
        )
        if row is None or row.status == "DISPATCHED":
            return bool(row and row.status == "DISPATCHED")
        key = get_settings().pii_encryption_key
        try:
            variables = json.loads(
                Fernet(key.get_secret_value().encode()).decrypt(
                    row.encrypted_payload.encode()
                )
            )
            delivered = send_email(
                template_key=row.template_key,
                recipient=row.recipient_email,
                variables=variables,
                idempotency_key=row.idempotency_key,
            )
            row.status = "DISPATCHED" if delivered else "FAILED"
            row.last_error = None if delivered else "CentralServiceDeliveryFailed"
            if delivered:
                row.dispatched_at = datetime.now(UTC)
                row.encrypted_payload = ""
            else:
                row.retry_count += 1
                row.last_error = "CentralServiceDeliveryFailed"
        except Exception as exc:
            row.status = "FAILED"
            row.retry_count += 1
            row.last_error = type(exc).__name__[:120]
            logger.warning(
                "Email dispatch failed",
                extra={
                    "dispatch_id": str(dispatch_id),
                    "exception_type": type(exc).__name__,
                },
            )
        db.commit()
        return row.status == "DISPATCHED"
    finally:
        db.close()


def retry(dispatch_id: UUID, *, entity_type: str, entity_id: UUID) -> bool:
    db = SessionLocal()
    try:
        row = db.scalar(
            select(EmailDispatchOutbox).where(
                EmailDispatchOutbox.id == dispatch_id,
                EmailDispatchOutbox.entity_type == entity_type,
                EmailDispatchOutbox.entity_id == entity_id,
            )
        )
        if row is None or row.status == "DISPATCHED":
            return False
        row.status = "PENDING"
        db.commit()
    finally:
        db.close()
    return dispatch(dispatch_id)
