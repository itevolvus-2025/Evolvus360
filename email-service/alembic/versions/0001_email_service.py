"""initial email service schema

Revision ID: 0001_email_service
Revises:
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_email_service"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON_VALUE = sa.JSON().with_variant(
    postgresql.JSONB(astext_type=sa.Text()), "postgresql"
)


def upgrade() -> None:
    op.create_table(
        "email_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("template_key", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("required_variables", JSON_VALUE, server_default=sa.text("'[]'"), nullable=False),
        sa.Column("allow_custom_subject", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("body_html IS NOT NULL OR body_text IS NOT NULL", name=op.f("ck_email_templates_body_required")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_email_templates")),
        sa.UniqueConstraint("template_key", name="uq_email_templates_template_key"),
        schema="public",
    )
    op.create_table(
        "email_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.String(length=100), nullable=True),
        sa.Column("idempotency_key", sa.String(length=150), nullable=True),
        sa.Column("application_name", sa.String(length=100), nullable=False),
        sa.Column("recipient_email", sa.String(length=255), nullable=False),
        sa.Column("to_addresses", JSON_VALUE, nullable=False),
        sa.Column("cc_addresses", JSON_VALUE, nullable=False),
        sa.Column("bcc_addresses", JSON_VALUE, nullable=False),
        sa.Column("sender_email", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("template_key", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="PENDING", nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.String(length=120), nullable=True),
        sa.Column("delivery_payload_encrypted", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('PENDING','PROCESSING','SENT','FAILED')", name=op.f("ck_email_logs_status_valid")),
        sa.CheckConstraint("retry_count >= 0", name=op.f("ck_email_logs_retry_nonnegative")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_email_logs")),
        sa.UniqueConstraint("application_name", "idempotency_key", name="uq_email_logs_app_idempotency"),
        schema="public",
    )
    op.create_index("ix_email_logs_created_at", "email_logs", ["created_at"], schema="public")
    op.create_index("ix_email_logs_app_status_created", "email_logs", ["application_name", "status", "created_at"], schema="public")
    op.create_index("ix_email_logs_template_key", "email_logs", ["template_key"], schema="public")
    op.create_table(
        "email_delivery_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email_log_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("provider_response", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.String(length=120), nullable=True),
        sa.Column("attempted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["email_log_id"], ["public.email_logs.id"], ondelete="CASCADE"),
        sa.CheckConstraint("attempt_number > 0", name=op.f("ck_email_delivery_attempts_attempt_number_positive")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_email_delivery_attempts")),
        sa.UniqueConstraint("email_log_id", "attempt_number", name="uq_email_attempt_number"),
        schema="public",
    )
    op.create_index("ix_email_delivery_attempts_log", "email_delivery_attempts", ["email_log_id", "attempted_at"], schema="public")
    op.create_table(
        "email_provider_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider_name", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("metadata_json", JSON_VALUE, server_default=sa.text("'{}'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_email_provider_settings")),
        sa.UniqueConstraint("provider_name", name="uq_email_provider_settings_name"),
        schema="public",
    )


def downgrade() -> None:
    op.drop_table("email_provider_settings", schema="public")
    op.drop_index("ix_email_delivery_attempts_log", table_name="email_delivery_attempts", schema="public")
    op.drop_table("email_delivery_attempts", schema="public")
    op.drop_index("ix_email_logs_template_key", table_name="email_logs", schema="public")
    op.drop_index("ix_email_logs_app_status_created", table_name="email_logs", schema="public")
    op.drop_index("ix_email_logs_created_at", table_name="email_logs", schema="public")
    op.drop_table("email_logs", schema="public")
    op.drop_table("email_templates", schema="public")
