"""Template rendering, idempotent delivery, logs, and safe administrator retries."""

import html
import json
import logging
import re
from datetime import UTC, datetime, timedelta
from string import Template
from urllib.parse import urlparse
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.email import EmailDeliveryAttempt, EmailLog, EmailTemplate
from app.schemas.email import AttachmentInput, SendEmailRequest
from app.services import smtp_provider

logger = logging.getLogger(__name__)
PLACEHOLDER = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")


def _payload_encryptor() -> Fernet:
    secret = get_settings().email_payload_encryption_key
    if not secret:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Email payload encryption is not configured",
        )
    try:
        return Fernet(secret.get_secret_value().encode("ascii"))
    except (ValueError, UnicodeEncodeError):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Email payload encryption is not configured correctly",
        ) from None


def _render(template: EmailTemplate, values: dict[str, str | int | float | bool]):
    keys = set(PLACEHOLDER.findall(template.subject))
    if template.body_html:
        keys.update(PLACEHOLDER.findall(template.body_html))
    if template.body_text:
        keys.update(PLACEHOLDER.findall(template.body_text))
    missing = (set(template.required_variables or []) | keys) - set(values)
    if missing:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Required template variables are missing",
        )
    text_values = {key: str(value) for key, value in values.items()}
    for key, value in text_values.items():
        if key.endswith("_link"):
            scheme = urlparse(value).scheme.lower()
            allowed = (
                {"https"}
                if get_settings().app_env.lower() in {"prod", "production"}
                else {"http", "https"}
            )
            if scheme not in allowed:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "Template links must use a secure web URL",
                )
    html_values = {
        key: html.escape(value, quote=True) for key, value in text_values.items()
    }
    try:
        subject = Template(template.subject).substitute(text_values)
        body_text = (
            Template(template.body_text).substitute(text_values)
            if template.body_text
            else None
        )
        body_html = (
            Template(template.body_html).substitute(html_values)
            if template.body_html
            else None
        )
    except (KeyError, ValueError):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Template rendering failed",
        ) from None
    return subject, body_text, body_html


def _serialized_payload(
    payload: SendEmailRequest,
    subject: str,
    body_text: str | None,
    body_html: str | None,
) -> str:
    value = {
        "to": [str(item) for item in payload.to],
        "cc": [str(item) for item in payload.cc],
        "bcc": [str(item) for item in payload.bcc],
        "subject": subject,
        "body_text": body_text,
        "body_html": body_html,
        "attachments": [item.model_dump(mode="json") for item in payload.attachments],
    }
    return (
        _payload_encryptor()
        .encrypt(json.dumps(value, separators=(",", ":")).encode("utf-8"))
        .decode("ascii")
    )


def _open_payload(email: EmailLog) -> dict:
    if not email.delivery_payload_encrypted:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Email payload is no longer available for retry"
        )
    try:
        raw = _payload_encryptor().decrypt(
            email.delivery_payload_encrypted.encode("ascii")
        )
        return json.loads(raw)
    except (InvalidToken, ValueError, UnicodeDecodeError):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Stored email payload could not be decrypted",
        ) from None


def _write_attempt_result(
    db: Session,
    email: EmailLog,
    attempt_number: int,
    *,
    status_value: str,
    provider_message_id: str | None = None,
    error_type: str | None = None,
) -> None:
    attempt = db.scalar(
        select(EmailDeliveryAttempt).where(
            EmailDeliveryAttempt.email_log_id == email.id,
            EmailDeliveryAttempt.attempt_number == attempt_number,
        )
    )
    if attempt:
        attempt.status = status_value
        if status_value == "SENT":
            attempt.provider_response = "Accepted by SMTP provider"
        else:
            attempt.provider_response = "SMTP delivery failed"
            attempt.error_message = error_type
    email.status = status_value
    email.error_message = error_type
    if provider_message_id:
        email.provider_message_id = provider_message_id
    if status_value == "SENT":
        email.sent_at = datetime.now(UTC)
        email.delivery_payload_encrypted = None


def _deliver(
    db: Session, email: EmailLog, payload: dict, *, is_retry: bool
) -> EmailLog:
    if is_retry:
        email.retry_count += 1
    attempt_number = email.retry_count + 1
    email.status = "PROCESSING"
    db.add(
        EmailDeliveryAttempt(
            email_log_id=email.id,
            attempt_number=attempt_number,
            status="PROCESSING",
        )
    )
    db.commit()
    db.refresh(email)
    try:
        sender, provider_id = smtp_provider.send_message(
            to=payload["to"],
            cc=payload["cc"],
            bcc=payload["bcc"],
            subject=payload["subject"],
            body_text=payload.get("body_text"),
            body_html=payload.get("body_html"),
            attachments=[
                AttachmentInput.model_validate(item)
                for item in payload.get("attachments", [])
            ],
        )
        email.sender_email = sender
        _write_attempt_result(
            db,
            email,
            attempt_number,
            status_value="SENT",
            provider_message_id=provider_id,
        )
    except Exception as exc:
        error_type = type(exc).__name__[:120]
        logger.warning(
            "Email provider delivery failed",
            extra={"email_id": str(email.id), "exception_type": type(exc).__name__},
        )
        _write_attempt_result(
            db,
            email,
            attempt_number,
            status_value="FAILED",
            error_type=error_type,
        )
    db.commit()
    db.refresh(email)
    return email


def send_email(
    db: Session,
    payload: SendEmailRequest,
    *,
    idempotency_key: str | None,
    request_id: str | None,
) -> tuple[EmailLog, bool]:
    if idempotency_key:
        existing = db.scalar(
            select(EmailLog).where(
                EmailLog.application_name == payload.application_name,
                EmailLog.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            return existing, True
    recipients = [
        str(value).casefold() for value in payload.to + payload.cc + payload.bcc
    ]
    if len(recipients) != len(set(recipients)):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "An address cannot appear in multiple recipient lists",
        )
    if payload.template_key:
        template = db.scalar(
            select(EmailTemplate).where(
                EmailTemplate.template_key == payload.template_key,
                EmailTemplate.is_active.is_(True),
            )
        )
        if template is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "Active email template was not found"
            )
        if payload.subject and not template.allow_custom_subject:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "This template does not allow a custom subject",
            )
        subject, body_text, body_html = _render(template, payload.variables)
        if payload.subject:
            subject = payload.subject
        stored_template_key = payload.template_key
    else:
        subject = payload.subject or ""
        body_text = payload.body
        body_html = None
        stored_template_key = "DIRECT"
    if len(subject) > 255:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Rendered subject exceeds the maximum length",
        )
    smtp_provider.validate_attachments(payload.attachments)
    encrypted_payload = _serialized_payload(payload, subject, body_text, body_html)
    email = EmailLog(
        request_id=request_id,
        idempotency_key=idempotency_key,
        application_name=payload.application_name,
        recipient_email=str(payload.to[0]),
        to_addresses=[str(value) for value in payload.to],
        cc_addresses=[str(value) for value in payload.cc],
        bcc_addresses=[str(value) for value in payload.bcc],
        sender_email=get_settings().smtp_from_email or "unconfigured",
        subject=subject,
        template_key=stored_template_key,
        status="PENDING",
        delivery_payload_encrypted=encrypted_payload,
    )
    db.add(email)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        if idempotency_key:
            existing = db.scalar(
                select(EmailLog).where(
                    EmailLog.application_name == payload.application_name,
                    EmailLog.idempotency_key == idempotency_key,
                )
            )
            if existing is not None:
                return existing, True
        raise
    result = _deliver(db, email, _open_payload(email), is_retry=False)
    return result, False


def retry_email(db: Session, email_id: UUID) -> EmailLog:
    email = db.scalar(select(EmailLog).where(EmailLog.id == email_id).with_for_update())
    if email is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Email was not found")
    if email.status == "PROCESSING" and email.updated_at < datetime.now(
        UTC
    ) - timedelta(minutes=5):
        email.status = "FAILED"
        email.error_message = "DeliveryInterrupted"
        db.commit()
    if email.status != "FAILED":
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Only failed emails can be retried"
        )
    if email.retry_count >= get_settings().max_retries:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email retry limit reached")
    payload = _open_payload(email)
    return _deliver(db, email, payload, is_retry=True)


def email_status(email: EmailLog) -> dict:
    local, sep, domain = email.recipient_email.partition("@")
    masked = (local[:1] + "***" if local else "***") + sep + domain
    return {
        "id": email.id,
        "application_name": email.application_name,
        "recipient": masked,
        "template_key": email.template_key,
        "status": email.status,
        "created_at": email.created_at,
        "sent_at": email.sent_at,
        "retry_count": email.retry_count,
    }


def email_log_item(email: EmailLog) -> dict:
    return {
        **email_status(email),
        "subject": email.subject,
        "error_message": email.error_message,
    }


def list_email_logs(
    db: Session,
    *,
    application_name: str | None,
    recipient: str | None,
    status_value: str | None,
    template_key: str | None,
    from_date: datetime | None,
    to_date: datetime | None,
    page: int,
    page_size: int,
) -> dict:
    query = select(EmailLog)
    filters = []
    if application_name:
        filters.append(EmailLog.application_name == application_name)
    if recipient:
        filters.append(EmailLog.recipient_email.ilike(recipient.strip()))
    if status_value:
        filters.append(EmailLog.status == status_value.upper())
    if template_key:
        filters.append(EmailLog.template_key == template_key.upper())
    if from_date:
        filters.append(EmailLog.created_at >= from_date)
    if to_date:
        filters.append(EmailLog.created_at <= to_date)
    if filters:
        query = query.where(*filters)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(EmailLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [email_log_item(row) for row in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
    }
