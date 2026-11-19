"""remove backend menu storage and role-menu assignments

Revision ID: d5a7c912e441
Revises: c4a17e63d29b
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d5a7c912e441"
down_revision: str | Sequence[str] | None = "c4a17e63d29b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("role_menus", schema="public")
    op.drop_table("menus", schema="public")


def downgrade() -> None:
    op.create_table(
        "menus",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("menu_name", sa.String(length=100), nullable=False),
        sa.Column("menu_icon_svg", sa.Text(), nullable=False),
        sa.Column("seq_no", sa.Integer(), nullable=False),
        sa.CheckConstraint("seq_no >= 0", name=op.f("ck_menus_seq_no_nonnegative")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_menus")),
        sa.UniqueConstraint("menu_name", name="uq_menus_menu_name"),
        schema="public",
    )
    op.create_table(
        "role_menus",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("menu_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["role_id"], ["public.roles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["menu_id"], ["public.menus.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_role_menus")),
        sa.UniqueConstraint("role_id", "menu_id", name="uq_role_menus_role_menu"),
        schema="public",
    )
    op.create_index("ix_role_menus_menu_id", "role_menus", ["menu_id"], schema="public")
