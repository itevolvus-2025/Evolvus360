"""Initial migration baseline; HRMS tables will be introduced in later revisions."""

revision = "0001_initial_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Establish the initial revision without creating business tables."""


def downgrade() -> None:
    """Revert the initial empty schema baseline."""
