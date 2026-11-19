"""Remove the company registry and its foreign keys.

Revision ID: b8f3c14e6a29
Revises: a7d9c2e84b16
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b8f3c14e6a29"
down_revision: str | Sequence[str] | None = "a7d9c2e84b16"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Keep company_id values as opaque tenant grouping UUIDs. Drop every
    # foreign key that targets the registry, then drop the registry itself
    # without CASCADE so unknown dependencies stop the migration safely.
    op.execute(sa.text("""
        DO $$
        DECLARE
            dependency RECORD;
        BEGIN
            IF to_regclass('public.companies') IS NOT NULL THEN
                FOR dependency IN
                    SELECT ns.nspname AS schema_name,
                           tbl.relname AS table_name,
                           con.conname AS constraint_name
                    FROM pg_constraint con
                    JOIN pg_class tbl ON tbl.oid = con.conrelid
                    JOIN pg_namespace ns ON ns.oid = tbl.relnamespace
                    WHERE con.contype = 'f'
                      AND con.confrelid = 'public.companies'::regclass
                LOOP
                    EXECUTE format(
                        'ALTER TABLE %I.%I DROP CONSTRAINT %I',
                        dependency.schema_name,
                        dependency.table_name,
                        dependency.constraint_name
                    );
                END LOOP;

                EXECUTE 'DROP TABLE public.companies';
            END IF;
        END $$;
    """))


def downgrade() -> None:
    raise RuntimeError(
        "This migration removes company registry data and is forward-only."
    )
