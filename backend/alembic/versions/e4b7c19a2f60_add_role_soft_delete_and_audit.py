"""add role soft-delete and audit fields

Revision ID: e4b7c19a2f60
Revises: d5a7c912e441
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e4b7c19a2f60"
down_revision: str | Sequence[str] | None = "d5a7c912e441"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "IF EXISTS (SELECT lower(role_name) FROM public.roles "
            "WHERE is_active IS TRUE GROUP BY lower(role_name) "
            "HAVING count(*) > 1) THEN "
            "RAISE EXCEPTION 'Cannot enforce unique active role names: duplicates exist'; "
            "END IF; END $$;"
        )
    )

    op.add_column(
        "roles", sa.Column("created_by", sa.Uuid(), nullable=True), schema="public"
    )
    op.create_foreign_key(
        "fk_roles_created_by_users",
        "roles",
        "users",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
        source_schema="public",
        referent_schema="public",
    )
    op.add_column(
        "roles", sa.Column("updated_by", sa.Uuid(), nullable=True), schema="public"
    )
    op.create_foreign_key(
        "fk_roles_updated_by_users",
        "roles",
        "users",
        ["updated_by"],
        ["id"],
        ondelete="SET NULL",
        source_schema="public",
        referent_schema="public",
    )
    op.add_column(
        "roles",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        schema="public",
    )
    op.create_index(
        "uq_roles_active_name_lower",
        "roles",
        [sa.text("lower(role_name)")],
        unique=True,
        schema="public",
        postgresql_where=sa.text("is_deleted IS false AND is_active IS true"),
    )


def downgrade() -> None:
    raise RuntimeError(
        "This migration is forward-only; downgrade would discard role audit state."
    )
