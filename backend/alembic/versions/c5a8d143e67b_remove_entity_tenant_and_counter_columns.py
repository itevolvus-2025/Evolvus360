"""Remove tenant and sequence columns from entities.

Revision ID: c5a8d143e67b
Revises: b8f3c14e6a29
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c5a8d143e67b"
down_revision: str | Sequence[str] | None = "b8f3c14e6a29"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # These columns may already have been manually removed in some databases.
    # Keep the migration idempotent while removing their old constraints and
    # index in databases that still have them.
    op.execute(sa.text("""
        DO $$ BEGIN
            IF to_regclass('public.entities') IS NOT NULL THEN
                ALTER TABLE public.entities
                    DROP CONSTRAINT IF EXISTS uq_entities_company_code;
                ALTER TABLE public.entities
                    DROP CONSTRAINT IF EXISTS ck_entities_sequence_nonnegative;
                ALTER TABLE public.entities
                    DROP CONSTRAINT IF EXISTS sequence_nonnegative;
                DROP INDEX IF EXISTS public.ix_entities_company_active;
                ALTER TABLE public.entities
                    DROP COLUMN IF EXISTS company_id;
                ALTER TABLE public.entities
                    DROP COLUMN IF EXISTS next_employee_sequence;
            END IF;
        END $$;
    """))


def downgrade() -> None:
    raise RuntimeError(
        "This migration removes manually deleted entity fields and is forward-only."
    )
