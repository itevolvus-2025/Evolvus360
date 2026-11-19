"""add standard audit fields to existing HRMS tables

Revision ID: 3f62a1b9c804
Revises: 9d44f2c0a731
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "3f62a1b9c804"
down_revision: str | Sequence[str] | None = "9d44f2c0a731"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "users",
    "companies",
    "roles",
    "menus",
    "role_menus",
    "permissions",
    "user_roles",
    "role_permissions",
    "refresh_token_sessions",
    "password_reset_tokens",
    "departments",
    "entities",
    "employee_employment_details",
    "employee_personal_details",
    "employee_contact_details",
    "employee_bank_details",
    "employee_documents",
    "employee_skills_and_interests",
    "onboarding_invitations",
    "email_dispatch_outbox",
)


def upgrade() -> None:
    for table in TABLES:
        for column in ("created_by", "updated_by"):
            op.add_column(
                table,
                sa.Column(column, sa.Uuid(), nullable=True),
                schema="public",
            )
            op.create_foreign_key(
                f"fk_{table}_{column}_users",
                table,
                "users",
                [column],
                ["id"],
                ondelete="SET NULL",
                source_schema="public",
                referent_schema="public",
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

    # Preserve the meaning of existing timestamp soft-deletion state.
    for table in ("users", "companies", "employee_employment_details"):
        op.execute(
            sa.text(
                f'UPDATE public."{table}" SET is_deleted = (deleted_at IS NOT NULL)'
            )
        )


def downgrade() -> None:
    raise RuntimeError(
        "This audit migration is forward-only; reverting it would discard audit data."
    )
