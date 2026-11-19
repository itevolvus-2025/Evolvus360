"""add standard audit fields to email service tables

Revision ID: 0002_email_service_audit
Revises: 0001_email_service
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_email_service_audit"
down_revision: str | Sequence[str] | None = "0001_email_service"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "email_templates",
    "email_logs",
    "email_delivery_attempts",
    "email_provider_settings",
)


def upgrade() -> None:
    for table in TABLES:
        op.add_column(table, sa.Column("created_by", sa.Uuid(), nullable=True), schema="public")
        op.add_column(table, sa.Column("updated_by", sa.Uuid(), nullable=True), schema="public")
        op.add_column(
            table,
            sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
            schema="public",
        )


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_column(table, "is_deleted", schema="public")
        op.drop_column(table, "updated_by", schema="public")
        op.drop_column(table, "created_by", schema="public")
