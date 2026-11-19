"""store permission keys on roles as JSONB

Revision ID: f731c2d89a04
Revises: e4b7c19a2f60
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f731c2d89a04"
down_revision: str | Sequence[str] | None = "e4b7c19a2f60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "roles",
        sa.Column(
            "permissions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        schema="public",
    )


def downgrade() -> None:
    raise RuntimeError(
        "This migration is forward-only; downgrade would discard role permissions."
    )
