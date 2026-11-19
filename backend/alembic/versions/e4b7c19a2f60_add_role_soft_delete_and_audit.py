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
            "WHERE is_active IS TRUE AND is_deleted IS FALSE "
            "GROUP BY lower(role_name) "
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
    op.execute(sa.text("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'roles'
                  AND column_name = 'is_deleted'
            ) THEN
                ALTER TABLE public.roles
                    ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT false;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'public' AND tablename = 'roles'
                  AND indexname = 'uq_roles_active_name_lower'
            ) THEN
                CREATE UNIQUE INDEX uq_roles_active_name_lower
                    ON public.roles (lower(role_name))
                    WHERE is_deleted IS false AND is_active IS true;
            END IF;
        END $$;
    """))


def downgrade() -> None:
    raise RuntimeError(
        "This migration is forward-only; downgrade would discard role audit state."
    )
