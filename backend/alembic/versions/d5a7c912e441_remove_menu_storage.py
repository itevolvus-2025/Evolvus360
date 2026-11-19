"""retain relational menu records while restoring the HRMS schema

Revision ID: d5a7c912e441
Revises: c4a17e63d29b
"""

from collections.abc import Sequence

revision: str = "d5a7c912e441"
down_revision: str | Sequence[str] | None = "c4a17e63d29b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # These tables can contain rows copied from the pre-consolidation schema.
    # Keep them; dropping them here would silently discard menu assignments.
    pass


def downgrade() -> None:
    raise RuntimeError("This schema preservation migration is forward-only.")
