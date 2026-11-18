"""use timezone aware auth timestamps

Revision ID: 485f3b6c7a06
Revises: b8e683b32e35
Create Date: 2026-11-17 15:53:17.637186

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "485f3b6c7a06"
down_revision: str | Sequence[str] | None = "b8e683b32e35"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIMESTAMP_COLUMNS = (
    ("refresh_token_sessions", "expires_at", False),
    ("refresh_token_sessions", "revoked_at", True),
    ("refresh_token_sessions", "created_at", False),
    ("refresh_token_sessions", "last_used_at", True),
    ("users", "email_verified_at", True),
    ("users", "last_login_at", True),
    ("users", "locked_until", True),
)


def upgrade() -> None:
    # Existing naive timestamps represent UTC, so make that interpretation explicit.
    for table, column, nullable in TIMESTAMP_COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=postgresql.TIMESTAMP(),
            type_=sa.DateTime(timezone=True),
            existing_nullable=nullable,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    # Convert values back to UTC-naive timestamps without shifting their wall time.
    for table, column, nullable in reversed(TIMESTAMP_COLUMNS):
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(timezone=True),
            type_=postgresql.TIMESTAMP(),
            existing_nullable=nullable,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )
