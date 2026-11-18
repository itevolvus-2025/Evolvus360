"""Persistent templates, dispatch logs, attempts and provider metadata."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.database.base import Base

JSON_VALUE = JSON().with_variant(JSONB(), "postgresql")


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


def _id() -> Mapped[UUID]:
    return mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)


class EmailTemplate(TimestampMixin, Base):
    __tablename__ = "email_templates"
    __table_args__ = (
        UniqueConstraint("template_key", name="uq_email_templates_template_key"),
        CheckConstraint(
            "body_html IS NOT NULL OR body_text IS NOT NULL",
            name="body_required",
        ),
        {"schema": None},
    )
    id: Mapped[UUID] = _id()
    template_key: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body_html: Mapped[str | None] = mapped_column(Text)
    body_text: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    required_variables: Mapped[list[str]] = mapped_column(
        JSON_VALUE, nullable=False, server_default=text("'[]'")
    )
    allow_custom_subject: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )


class EmailLog(TimestampMixin, Base):
    __tablename__ = "email_logs"
    __table_args__ = (
        UniqueConstraint(
            "application_name", "idempotency_key", name="uq_email_logs_app_idempotency"
        ),
        CheckConstraint(
            "status IN ('PENDING','PROCESSING','SENT','FAILED')", name="status_valid"
        ),
        CheckConstraint("retry_count >= 0", name="retry_nonnegative"),
        Index("ix_email_logs_created_at", "created_at"),
        Index(
            "ix_email_logs_app_status_created",
            "application_name",
            "status",
            "created_at",
        ),
        Index("ix_email_logs_template_key", "template_key"),
        {"schema": None},
    )
    id: Mapped[UUID] = _id()
    request_id: Mapped[str | None] = mapped_column(String(100))
    idempotency_key: Mapped[str | None] = mapped_column(String(150))
    application_name: Mapped[str] = mapped_column(String(100), nullable=False)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    to_addresses: Mapped[list[str]] = mapped_column(JSON_VALUE, nullable=False)
    cc_addresses: Mapped[list[str]] = mapped_column(JSON_VALUE, nullable=False)
    bcc_addresses: Mapped[list[str]] = mapped_column(JSON_VALUE, nullable=False)
    sender_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    template_key: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="PENDING"
    )
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    retry_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    error_message: Mapped[str | None] = mapped_column(String(120))
    delivery_payload_encrypted: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[list[EmailDeliveryAttempt]] = relationship(
        back_populates="email_log", cascade="all, delete-orphan"
    )


class EmailDeliveryAttempt(Base):
    __tablename__ = "email_delivery_attempts"
    __table_args__ = (
        UniqueConstraint(
            "email_log_id", "attempt_number", name="uq_email_attempt_number"
        ),
        CheckConstraint("attempt_number > 0", name="attempt_number_positive"),
        Index("ix_email_delivery_attempts_log", "email_log_id", "attempted_at"),
        {"schema": None},
    )
    id: Mapped[UUID] = _id()
    email_log_id: Mapped[UUID] = mapped_column(
        ForeignKey("email_logs.id", ondelete="CASCADE"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_response: Mapped[str | None] = mapped_column(String(255))
    error_message: Mapped[str | None] = mapped_column(String(120))
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    email_log: Mapped[EmailLog] = relationship(back_populates="attempts")


class EmailProviderSetting(TimestampMixin, Base):
    """Non-secret provider metadata; credentials stay in environment/secrets."""

    __tablename__ = "email_provider_settings"
    __table_args__ = (
        UniqueConstraint("provider_name", name="uq_email_provider_settings_name"),
        {"schema": None},
    )
    id: Mapped[UUID] = _id()
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    metadata_json: Mapped[dict] = mapped_column(
        JSON_VALUE, nullable=False, server_default=text("'{}'")
    )
