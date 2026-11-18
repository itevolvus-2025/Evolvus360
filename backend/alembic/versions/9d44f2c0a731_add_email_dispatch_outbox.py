"""add encrypted centralized email dispatch outbox"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9d44f2c0a731"
down_revision: str | Sequence[str] | None = "f81a3d2c9b40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "email_dispatch_outbox",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_email", sa.String(255), nullable=False),
        sa.Column("template_key", sa.String(100), nullable=False),
        sa.Column("idempotency_key", sa.String(150), nullable=False),
        sa.Column("encrypted_payload", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), server_default="PENDING", nullable=False),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.String(120), nullable=True),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('PENDING','FAILED','DISPATCHED')", name="status_valid"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_email_dispatch_outbox_idempotency"),
    )
    op.create_index("ix_email_dispatch_outbox_entity", "email_dispatch_outbox", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_index("ix_email_dispatch_outbox_entity", table_name="email_dispatch_outbox")
    op.drop_table("email_dispatch_outbox")
