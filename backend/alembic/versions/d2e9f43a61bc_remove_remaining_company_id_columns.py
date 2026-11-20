"""Remove remaining company_id fields from HRMS records.

Revision ID: d2e9f43a61bc
Revises: c5a8d143e67b
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d2e9f43a61bc"
down_revision: str | Sequence[str] | None = "c5a8d143e67b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Some environments already removed departments.company_id manually.
    # DROP COLUMN removes only dependent indexes/constraints on that column;
    # unrelated records and HRMS tables remain untouched.
    for table_name in ("users", "departments", "employee_employment_details"):
        op.execute(
            sa.text(
                f"ALTER TABLE IF EXISTS public.{table_name} "
                "DROP COLUMN IF EXISTS company_id"
            )
        )
    for index_name, column_name in (
        ("ix_employee_employment_department", "department_name"),
        ("ix_employee_employment_department_id", "department_id"),
        ("ix_employee_employment_entity_id", "entity_id"),
        ("ix_employee_employment_profile_status", "profile_status"),
    ):
        op.execute(
            sa.text(
                f"CREATE INDEX IF NOT EXISTS {index_name} "
                "ON public.employee_employment_details "
                f"({column_name}) WHERE deleted_at IS NULL"
            )
        )


def downgrade() -> None:
    raise RuntimeError(
        "This migration removes obsolete company_id values and is forward-only."
    )
