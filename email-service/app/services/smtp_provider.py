"""SMTP provider adapter. Keep provider-specific handling behind this class."""

import base64
import binascii
import smtplib
import ssl
import certifi
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from pathlib import PurePosixPath

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.schemas.email import AttachmentInput

ALLOWED_ATTACHMENT_TYPES = {
    "application/pdf": (b"%PDF-", ".pdf"),
    "image/jpeg": (b"\xff\xd8\xff", ".jpg"),
    "image/png": (b"\x89PNG\r\n\x1a\n", ".png"),
    "text/plain": (None, ".txt"),
}


def _decode_attachment(item: AttachmentInput) -> tuple[str, str, bytes]:
    settings = get_settings()
    allowed = ALLOWED_ATTACHMENT_TYPES.get(item.content_type)
    if allowed is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Attachment type is not allowed"
        )
    try:
        contents = base64.b64decode(item.content_base64, validate=True)
    except (ValueError, binascii.Error):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Attachment encoding is invalid"
        ) from None
    if not contents or len(contents) > settings.max_attachment_size_bytes:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            "Attachment exceeds the configured size limit",
        )
    signature, safe_suffix = allowed
    if signature and not contents.startswith(signature):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Attachment content does not match its type",
        )
    safe_name = PurePosixPath(item.filename.replace("\\", "/")).name[:255]
    if not safe_name or safe_name in {".", ".."}:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Attachment filename is invalid"
        )
    if not safe_name.lower().endswith(safe_suffix):
        safe_name += safe_suffix
    return safe_name, item.content_type, contents


def validate_attachments(items: list[AttachmentInput]) -> None:
    total_size = 0
    for item in items:
        _, _, contents = _decode_attachment(item)
        total_size += len(contents)
    if total_size > get_settings().max_total_attachment_size_bytes:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            "Total attachments exceed the configured size limit",
        )


def send_message(
    *,
    to: list[str],
    cc: list[str],
    bcc: list[str],
    subject: str,
    body_text: str | None,
    body_html: str | None,
    attachments: list[AttachmentInput],
) -> tuple[str, str]:
    """Send one email and return safe sender and Message-ID metadata."""
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_from_email:
        raise RuntimeError("SMTP provider is not configured")
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((settings.smtp_from_name, settings.smtp_from_email))
    message["To"] = ", ".join(to)
    if cc:
        message["Cc"] = ", ".join(cc)
    message_id = make_msgid(domain=settings.smtp_from_email.split("@")[-1])
    message["Message-ID"] = message_id
    message.set_content(
        body_text or "This message requires an HTML-capable email client."
    )
    if body_html:
        message.add_alternative(body_html, subtype="html")
    for item in attachments:
        filename, content_type, contents = _decode_attachment(item)
        major, minor = content_type.split("/", 1)
        message.add_attachment(
            contents, maintype=major, subtype=minor, filename=filename
        )

    recipients = to + cc + bcc
    context = ssl.create_default_context(cafile=certifi.where())
    if settings.smtp_use_ssl:
        with smtplib.SMTP_SSL(
            settings.smtp_host,
            settings.smtp_port,
            timeout=settings.smtp_timeout_seconds,
            context=context,
        ) as smtp:
            _authenticate(smtp, settings)
            refused = smtp.send_message(
                message, from_addr=settings.smtp_from_email, to_addrs=recipients
            )
    else:
        with smtplib.SMTP(
            settings.smtp_host,
            settings.smtp_port,
            timeout=settings.smtp_timeout_seconds,
        ) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls(context=context)
            _authenticate(smtp, settings)
            refused = smtp.send_message(
                message, from_addr=settings.smtp_from_email, to_addrs=recipients
            )
    if refused:
        raise RuntimeError("SMTP provider rejected one or more recipients")
    return settings.smtp_from_email, message_id


def _authenticate(smtp, settings) -> None:
    if settings.smtp_username:
        smtp.login(
            settings.smtp_username,
            settings.smtp_password.get_secret_value(),
        )
