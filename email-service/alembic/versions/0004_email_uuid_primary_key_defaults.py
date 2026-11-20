"""Add PostgreSQL-generated UUID defaults to Email Service primary keys.

Revision ID: 0004_uuid_pk_defaults
Revises: 0003_email_audit_cleanup
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_uuid_pk_defaults"
down_revision: str | Sequence[str] | None = "0003_email_audit_cleanup"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "email_delivery_attempts",
    "email_logs",
    "email_provider_settings",
    "email_templates",
)


def upgrade() -> None:
    for table in TABLES:
        op.alter_column(
            table,
            "id",
            existing_type=sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            existing_nullable=False,
            schema="public",
        )


def downgrade() -> None:
    for table in reversed(TABLES):
        op.alter_column(
            table,
            "id",
            existing_type=sa.Uuid(),
            server_default=None,
            existing_nullable=False,
            schema="public",
        )
