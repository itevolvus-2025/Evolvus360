"""Preserve the original relational menu and role-menu tables.

Revision ID: a7d9c2e84b16
Revises: f731c2d89a04
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a7d9c2e84b16"
down_revision: str | Sequence[str] | None = "f731c2d89a04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Older branches removed these tables after consolidating them into
    # master_data. Restore their original relational form without overwriting
    # tables or rows that survived from an earlier revision.
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS public.menus (
            id UUID NOT NULL,
            menu_name VARCHAR(100) NOT NULL,
            menu_icon_svg TEXT NOT NULL,
            seq_no INTEGER NOT NULL,
            CONSTRAINT pk_menus PRIMARY KEY (id),
            CONSTRAINT ck_menus_seq_no_nonnegative CHECK (seq_no >= 0),
            CONSTRAINT uq_menus_menu_name UNIQUE (menu_name)
        );
    """))
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS public.role_menus (
            id UUID NOT NULL,
            role_id UUID NOT NULL,
            menu_id UUID NOT NULL,
            CONSTRAINT pk_role_menus PRIMARY KEY (id),
            CONSTRAINT fk_role_menus_role_id_roles
                FOREIGN KEY (role_id) REFERENCES public.roles (id) ON DELETE CASCADE,
            CONSTRAINT fk_role_menus_menu_id_menus
                FOREIGN KEY (menu_id) REFERENCES public.menus (id) ON DELETE RESTRICT,
            CONSTRAINT uq_role_menus_role_menu UNIQUE (role_id, menu_id)
        );
    """))
    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_role_menus_menu_id
            ON public.role_menus (menu_id);
    """))


def downgrade() -> None:
    raise RuntimeError(
        "This migration preserves relational menu data and is forward-only."
    )
