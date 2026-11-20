"""Add employee approval audit and temporary credential state.

Revision ID: e31c4f9a20b7
Revises: d2e9f43a61bc
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e31c4f9a20b7"
down_revision: str | Sequence[str] | None = "d2e9f43a61bc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        schema="public",
    )
    op.add_column(
        "users",
        sa.Column(
            "temporary_password_expires_at", sa.DateTime(timezone=True), nullable=True
        ),
        schema="public",
    )
    op.add_column(
        "users",
        sa.Column(
            "temporary_password_used_at", sa.DateTime(timezone=True), nullable=True
        ),
        schema="public",
    )
    op.add_column(
        "employee_employment_details",
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        schema="public",
    )
    op.drop_constraint(
        op.f("chk_employee_onboarding_status"),
        "employee_employment_details",
        type_="check",
        schema="public",
    )
    op.create_check_constraint(
        op.f("chk_employee_onboarding_status"),
        "employee_employment_details",
        "onboarding_status IN ('INVITED','ONBOARDING','DRAFT_SAVED','SUBMITTED',"
        "'PENDING_APPROVAL','CHANGES_REQUESTED','APPROVED','REJECTED')",
        schema="public",
    )
    op.drop_constraint(
        op.f("ck_employee_employment_details_ck_employee_employment_d_6157"),
        "employee_employment_details",
        type_="check",
        schema="public",
    )
    op.create_check_constraint(
        op.f("ck_employee_employment_details_profile_status_valid"),
        "employee_employment_details",
        "profile_status IN ('PENDING','SUBMITTED','PENDING_APPROVAL',"
        "'APPROVED','REJECTED')",
        schema="public",
    )
    op.create_table(
        "employee_approval_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("snapshot_encrypted", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "action IN ('APPROVED','REJECTED','RESUBMITTED')",
            name="action_valid",
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["public.employee_employment_details.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["public.users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index(
        "ix_employee_approval_decisions_employee",
        "employee_approval_decisions",
        ["employee_id", "created_at"],
        schema="public",
    )


def downgrade() -> None:
    raise RuntimeError("Employee approval workflow migration is forward-only.")
