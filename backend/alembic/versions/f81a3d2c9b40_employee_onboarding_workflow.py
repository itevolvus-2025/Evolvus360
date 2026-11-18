"""add tenant masters and employee onboarding workflow fields

Revision ID: f81a3d2c9b40
Revises: e72bf31a9910
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f81a3d2c9b40"
down_revision: str | Sequence[str] | None = "e72bf31a9910"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for column, nullable in (
        ("sent_at", False),
        ("expires_at", False),
        ("submitted_at", True),
    ):
        op.alter_column(
            "onboarding_invitations",
            column,
            existing_type=sa.DateTime(),
            type_=sa.DateTime(timezone=True),
            existing_nullable=nullable,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
            schema="public",
        )

    op.create_table(
        "departments",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["public.companies.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_departments")),
        sa.UniqueConstraint("company_id", "name", name="uq_departments_company_name"),
        sa.UniqueConstraint("company_id", "code", name="uq_departments_company_code"),
        schema="public",
    )
    op.create_index(
        "ix_departments_company_active",
        "departments",
        ["company_id", "is_active"],
        schema="public",
    )
    op.create_table(
        "entities",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "next_employee_sequence", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "next_employee_sequence >= 0", name=op.f("ck_entities_sequence_nonnegative")
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["public.companies.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_entities")),
        sa.UniqueConstraint("company_id", "code", name="uq_entities_company_code"),
        schema="public",
    )
    op.create_index(
        "ix_entities_company_active",
        "entities",
        ["company_id", "is_active"],
        schema="public",
    )

    op.add_column(
        "employee_employment_details",
        sa.Column("department_id", sa.Uuid(), nullable=True),
        schema="public",
    )
    op.add_column(
        "employee_employment_details",
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        schema="public",
    )
    op.add_column(
        "employee_employment_details",
        sa.Column(
            "profile_status",
            sa.String(length=20),
            server_default="PENDING",
            nullable=False,
        ),
        schema="public",
    )
    op.add_column(
        "employee_employment_details",
        sa.Column("approved_by_user_id", sa.Uuid(), nullable=True),
        schema="public",
    )
    op.add_column(
        "employee_employment_details",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )
    op.drop_constraint(
        op.f("uq_employee_employment_company_code"),
        "employee_employment_details",
        type_="unique",
        schema="public",
    )
    op.create_unique_constraint(
        "uq_employee_employment_company_entity_code",
        "employee_employment_details",
        ["company_id", "entity_id", "employee_code"],
        schema="public",
    )
    op.create_foreign_key(
        "fk_employee_employment_details_department_id_departments",
        "employee_employment_details",
        "departments",
        ["department_id"],
        ["id"],
        source_schema="public",
        referent_schema="public",
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_employee_employment_details_entity_id_entities",
        "employee_employment_details",
        "entities",
        ["entity_id"],
        ["id"],
        source_schema="public",
        referent_schema="public",
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_employee_employment_details_approved_by_user_id_users",
        "employee_employment_details",
        "users",
        ["approved_by_user_id"],
        ["id"],
        source_schema="public",
        referent_schema="public",
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "profile_status_valid",
        "employee_employment_details",
        "profile_status IN ('PENDING','SUBMITTED','APPROVED')",
        schema="public",
    )
    op.alter_column(
        "onboarding_invitations",
        "invitation_status",
        existing_type=sa.String(length=30),
        server_default="PENDING",
        existing_nullable=False,
        schema="public",
    )
    op.execute(
        """
        UPDATE public.employee_employment_details
        SET profile_status = CASE onboarding_status
            WHEN 'SUBMITTED' THEN 'SUBMITTED'
            WHEN 'APPROVED' THEN 'APPROVED'
            ELSE 'PENDING'
        END
        """
    )
    op.create_index(
        "ix_employee_employment_department_id",
        "employee_employment_details",
        ["company_id", "department_id"],
        schema="public",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_employee_employment_entity_id",
        "employee_employment_details",
        ["company_id", "entity_id"],
        schema="public",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_employee_employment_profile_status",
        "employee_employment_details",
        ["company_id", "profile_status"],
        schema="public",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.drop_constraint(
        op.f("ck_onboarding_invitations_invitation_status_valid"),
        "onboarding_invitations",
        type_="check",
        schema="public",
    )
    op.execute(
        """
        UPDATE public.onboarding_invitations
        SET invitation_status = CASE
            WHEN invitation_status IN ('INVITED','DRAFT_SAVED','CHANGES_REQUESTED')
                THEN 'SENT'
            WHEN invitation_status IN ('SUBMITTED','APPROVED') THEN 'ACCEPTED'
            ELSE invitation_status
        END
        """
    )
    op.create_check_constraint(
        "invitation_status_valid",
        "onboarding_invitations",
        "invitation_status IN ('PENDING','SENT','ACCEPTED','EXPIRED','REVOKED')",
        schema="public",
    )
    op.alter_column(
        "onboarding_invitations",
        "invitation_status",
        existing_type=sa.String(length=30),
        server_default="PENDING",
        existing_nullable=False,
        schema="public",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_onboarding_invitations_invitation_status_valid"),
        "onboarding_invitations",
        type_="check",
        schema="public",
    )
    op.execute(
        """
        UPDATE public.onboarding_invitations
        SET invitation_status = CASE
            WHEN invitation_status IN ('PENDING','SENT') THEN 'INVITED'
            WHEN invitation_status = 'ACCEPTED' THEN 'SUBMITTED'
            ELSE invitation_status
        END
        """
    )
    op.create_check_constraint(
        "invitation_status_valid",
        "onboarding_invitations",
        "invitation_status IN ('INVITED','DRAFT_SAVED','SUBMITTED',"
        "'CHANGES_REQUESTED','APPROVED','EXPIRED','REVOKED')",
        schema="public",
    )
    op.alter_column(
        "onboarding_invitations",
        "invitation_status",
        existing_type=sa.String(length=30),
        server_default="INVITED",
        existing_nullable=False,
        schema="public",
    )
    op.drop_constraint(
        op.f("ck_employee_employment_details_profile_status_valid"),
        "employee_employment_details",
        type_="check",
        schema="public",
    )
    op.drop_constraint(
        op.f("fk_employee_employment_details_approved_by_user_id_users"),
        "employee_employment_details",
        type_="foreignkey",
        schema="public",
    )
    op.drop_constraint(
        op.f("fk_employee_employment_details_entity_id_entities"),
        "employee_employment_details",
        type_="foreignkey",
        schema="public",
    )
    op.drop_constraint(
        op.f("fk_employee_employment_details_department_id_departments"),
        "employee_employment_details",
        type_="foreignkey",
        schema="public",
    )
    op.drop_constraint(
        op.f("uq_employee_employment_company_entity_code"),
        "employee_employment_details",
        type_="unique",
        schema="public",
    )
    op.create_unique_constraint(
        "uq_employee_employment_company_code",
        "employee_employment_details",
        ["company_id", "employee_code"],
        schema="public",
    )
    op.drop_index(
        "ix_employee_employment_profile_status",
        table_name="employee_employment_details",
        schema="public",
    )
    op.drop_index(
        "ix_employee_employment_entity_id",
        table_name="employee_employment_details",
        schema="public",
    )
    op.drop_index(
        "ix_employee_employment_department_id",
        table_name="employee_employment_details",
        schema="public",
    )
    op.drop_column("employee_employment_details", "approved_at", schema="public")
    op.drop_column(
        "employee_employment_details", "approved_by_user_id", schema="public"
    )
    op.drop_column("employee_employment_details", "profile_status", schema="public")
    op.drop_column("employee_employment_details", "entity_id", schema="public")
    op.drop_column("employee_employment_details", "department_id", schema="public")
    op.drop_index("ix_entities_company_active", table_name="entities", schema="public")
    op.drop_table("entities", schema="public")
    op.drop_index(
        "ix_departments_company_active", table_name="departments", schema="public"
    )
    op.drop_table("departments", schema="public")
    for column, nullable in reversed(
        (("sent_at", False), ("expires_at", False), ("submitted_at", True))
    ):
        op.alter_column(
            "onboarding_invitations",
            column,
            existing_type=sa.DateTime(timezone=True),
            type_=sa.DateTime(),
            existing_nullable=nullable,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
            schema="public",
        )
