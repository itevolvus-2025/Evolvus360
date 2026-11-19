"""remove rejected audit columns from email service tables

Revision ID: 0003_email_audit_cleanup
Revises: 0002_email_service_audit
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_email_audit_cleanup"
down_revision: str | Sequence[str] | None = "0002_email_service_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "email_templates",
    "email_logs",
    "email_delivery_attempts",
    "email_provider_settings",
)


def upgrade() -> None:
    bind = op.get_bind()
    for table in TABLES:
        populated = bind.execute(
            sa.text(
                f'SELECT count(*) FROM public."{table}" '
                "WHERE created_by IS NOT NULL OR updated_by IS NOT NULL "
                "OR is_deleted IS TRUE"
            )
        ).scalar_one()
        if populated:
            raise RuntimeError(
                f"Refusing to remove non-empty audit values from {table}"
            )

    for table in reversed(TABLES):
        op.drop_column(table, "is_deleted", schema="public")
        op.drop_column(table, "updated_by", schema="public")
        op.drop_column(table, "created_by", schema="public")


def downgrade() -> None:
    for table in TABLES:
        op.add_column(
            table, sa.Column("created_by", sa.Uuid(), nullable=True), schema="public"
        )
        op.add_column(
            table, sa.Column("updated_by", sa.Uuid(), nullable=True), schema="public"
        )
        op.add_column(
            table,
            sa.Column(
                "is_deleted",
                sa.Boolean(),
                server_default=sa.text("false"),
                nullable=False,
            ),
            schema="public",
        )
