"""merge employee edit reason and role menu migration heads

Revision ID: fbc93a10e662
Revises: c8e51a72d904, a91e7b2c4d60
"""

from typing import Sequence


revision: str = "fbc93a10e662"
down_revision: str | Sequence[str] | None = ("c8e51a72d904", "a91e7b2c4d60")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
