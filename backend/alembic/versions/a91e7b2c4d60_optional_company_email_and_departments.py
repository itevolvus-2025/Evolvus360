"""Allow optional company email and seed fixed departments."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a91e7b2c4d60"
down_revision: str | Sequence[str] | None = "f42d89c3a710"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "employee_employment_details",
        "company_email",
        existing_type=sa.String(length=255),
        nullable=True,
        schema="public",
    )
    op.execute(sa.text("""
        INSERT INTO public.departments (id, name, code, is_active, created_at, updated_at)
        SELECT gen_random_uuid(), seed.name, seed.code, true, now(), now()
        FROM (VALUES
            ('IT', 'IT'),
            ('Chemistry', 'CHEMISTRY'),
            ('Biology', 'BIOLOGY'),
            ('HR', 'HR')
        ) AS seed(name, code)
        WHERE NOT EXISTS (
            SELECT 1 FROM public.departments d
            WHERE lower(d.name) = lower(seed.name)
               OR lower(d.code) = lower(seed.code)
        )
    """))


def downgrade() -> None:
    raise RuntimeError("This migration is forward-only.")
