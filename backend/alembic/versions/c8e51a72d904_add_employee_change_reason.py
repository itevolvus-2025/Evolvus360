"""store the latest employee edit reason

Revision ID: c8e51a72d904
Revises: 08d85d1bcd4c
"""

from alembic import op
import sqlalchemy as sa


revision = "c8e51a72d904"
down_revision = "08d85d1bcd4c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "employee_employment_details",
        sa.Column("last_change_reason", sa.Text(), nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column(
        "employee_employment_details", "last_change_reason", schema="public"
    )
