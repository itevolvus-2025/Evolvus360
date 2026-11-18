"""default menu UUIDs in the database

Revision ID: e72bf31a9910
Revises: c61d82f0a4b1
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e72bf31a9910"
down_revision: str | Sequence[str] | None = "c61d82f0a4b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "menus",
        "id",
        existing_type=sa.Uuid(),
        server_default=sa.text("gen_random_uuid()"),
        existing_nullable=False,
        schema="public",
    )


def downgrade() -> None:
    op.alter_column(
        "menus",
        "id",
        existing_type=sa.Uuid(),
        server_default=None,
        existing_nullable=False,
        schema="public",
    )
