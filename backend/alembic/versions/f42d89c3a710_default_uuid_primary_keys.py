"""Add PostgreSQL-generated UUID defaults to HRMS primary keys.

Revision ID: f42d89c3a710
Revises: e31c4f9a20b7
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f42d89c3a710"
down_revision: str | Sequence[str] | None = "e31c4f9a20b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "email_dispatch_outbox",
    "employee_approval_decisions",
    "menus",
    "onboarding_invitations",
    "password_reset_tokens",
    "refresh_token_sessions",
    "role_menus",
    "role_permissions",
    "user_roles",
    "users",
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
