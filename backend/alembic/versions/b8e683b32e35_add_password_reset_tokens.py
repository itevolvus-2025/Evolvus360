"""add password reset tokens

Revision ID: b8e683b32e35
Revises: fd4eaf21f8f6
Create Date: 2026-11-17 15:12:58.395102

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b8e683b32e35"
down_revision: str | Sequence[str] | None = "fd4eaf21f8f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Only the new password-reset table is needed; existing foreign keys stay intact.
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["public.users.id"],
            name="fk_password_reset_tokens_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_password_reset_tokens"),
        sa.UniqueConstraint("token_hash", name="uq_password_reset_tokens_token_hash"),
        schema="public",
    )
    op.create_index(
        "ix_password_reset_tokens_user_active",
        "password_reset_tokens",
        ["user_id", "expires_at"],
        unique=False,
        schema="public",
        postgresql_where=sa.text("used_at IS NULL AND revoked_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_password_reset_tokens_user_active",
        table_name="password_reset_tokens",
        schema="public",
    )
    op.drop_table("password_reset_tokens", schema="public")
