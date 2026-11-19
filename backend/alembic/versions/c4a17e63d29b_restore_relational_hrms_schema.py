"""restore the original relational HRMS schema and RBAC ownership

Revision ID: c4a17e63d29b
Revises: b6f1a7d2e903
Create Date: 2026-11-19
"""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from alembic import context

revision: str = "c4a17e63d29b"
down_revision: str | Sequence[str] | None = "b6f1a7d2e903"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# These stable system records were recovered from the verified pre-deletion
# backup. Their IDs are retained because existing RBAC link rows reference them.
ROLE_ROWS = [{'id': '5b59d81c-7c32-4dea-9d7a-90addb79d07a', 'role_code': 'CONSULTANT', 'role_name': 'Consultant', 'description': None, 'is_system_role': True, 'is_active': True}, {'id': 'd227d5a0-848f-4029-b159-42a46656e5a9', 'role_code': 'EMPLOYEE', 'role_name': 'Employee', 'description': None, 'is_system_role': True, 'is_active': True}, {'id': 'f0d0e3e6-8182-4550-990c-07ea3e4427bf', 'role_code': 'SUPER_ADMIN', 'role_name': 'Super Admin', 'description': None, 'is_system_role': True, 'is_active': True}, {'id': '67b6c3c2-a98c-4f38-82c1-4bfcadf25929', 'role_code': 'HR', 'role_name': 'HR', 'description': None, 'is_system_role': True, 'is_active': True}]
PERMISSION_ROWS = [{'id': 'b8fa098c-2ae3-4de6-b3f9-a3ea2b5ba1d5', 'permission_code': 'employees.manage', 'permission_name': 'Manage employees', 'module_name': 'employees', 'description': None}, {'id': '1f19fb31-de99-4a4c-bb9c-cd9ea3aa3e29', 'permission_code': 'employees.manage.global', 'permission_name': 'Manage employees across organizations', 'module_name': 'employees', 'description': None}, {'id': 'b7e43c3e-0eda-4d06-a0cd-db37e02a56fb', 'permission_code': 'employees.approve', 'permission_name': 'Approve employee profiles', 'module_name': 'employees', 'description': None}, {'id': '784a8ff6-92d6-4ea5-b761-43335adaa2de', 'permission_code': 'master_data.manage', 'permission_name': 'Manage master data', 'module_name': 'master-data', 'description': None}, {'id': 'a8d9ead4-69e2-4837-83cb-b98558740cd9', 'permission_code': 'roles.manage', 'permission_name': 'Manage roles', 'module_name': 'roles', 'description': None}, {'id': '800fd85b-7046-426a-bf05-b0812370842d', 'permission_code': 'roles.assign_super_admin', 'permission_name': 'Assign Super Admin role', 'module_name': 'roles', 'description': None}, {'id': '5d0ba9a3-67cd-46df-b898-e89795ab79a9', 'permission_code': 'employees.self.view', 'permission_name': 'View own employee profile', 'module_name': 'employees', 'description': None}, {'id': 'e695810a-aece-408f-9884-2dc364f442f2', 'permission_code': 'employees.self.update', 'permission_name': 'Update own employee profile', 'module_name': 'employees', 'description': None}, {'id': 'a374edc0-cc26-4d8e-a605-851fc5da7605', 'permission_code': 'documents.self.upload', 'permission_name': 'Upload own employee documents', 'module_name': 'documents', 'description': None}, {'id': '1810671c-845c-434d-9269-c509dca55db7', 'permission_code': 'reports.view', 'permission_name': 'View reports', 'module_name': 'reports', 'description': None}]
MENU_ROWS = [{'id': '05f033c3-4db7-4961-a9ff-bdff6b94d6a3', 'menu_name': 'User Management', 'menu_icon_svg': '<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">\n<path d="M13.3333 15.8337H16.6667C16.8877 15.8337 17.0996 15.7459 17.2559 15.5896C17.4122 15.4333 17.5 15.2213 17.5 15.0003V14.167C17.5 13.504 17.2366 12.8681 16.7678 12.3992C16.2989 11.9304 15.663 11.667 15 11.667H13.3333M11.47 8.33366C11.8075 8.71104 12.2517 8.97704 12.7437 9.09646C13.2358 9.21588 13.7525 9.18309 14.2254 9.00242C14.6984 8.82176 15.1054 8.50174 15.3925 8.08471C15.6797 7.66768 15.8334 7.17331 15.8334 6.66699C15.8334 6.16068 15.6797 5.6663 15.3925 5.24927C15.1054 4.83224 14.6984 4.51223 14.2254 4.33156C13.7525 4.1509 13.2358 4.11811 12.7437 4.23752C12.2517 4.35694 11.8075 4.62294 11.47 5.00033M2.5 15.0003V14.167C2.5 13.504 2.76339 12.8681 3.23223 12.3992C3.70107 11.9304 4.33696 11.667 5 11.667H8.33333C8.99637 11.667 9.63226 11.9304 10.1011 12.3992C10.5699 12.8681 10.8333 13.504 10.8333 14.167V15.0003C10.8333 15.2213 10.7455 15.4333 10.5893 15.5896C10.433 15.7459 10.221 15.8337 10 15.8337H3.33333C3.11232 15.8337 2.90036 15.7459 2.74408 15.5896C2.5878 15.4333 2.5 15.2213 2.5 15.0003ZM9.16667 6.66699C9.16667 7.33003 8.90327 7.96592 8.43443 8.43476C7.96559 8.9036 7.32971 9.16699 6.66667 9.16699C6.00363 9.16699 5.36774 8.9036 4.8989 8.43476C4.43006 7.96592 4.16667 7.33003 4.16667 6.66699C4.16667 6.00395 4.43006 5.36807 4.8989 4.89923C5.36774 4.43038 6.00363 4.16699 6.66667 4.16699C7.32971 4.16699 7.96559 4.43038 8.43443 4.89923C8.90327 5.36807 9.16667 6.00395 9.16667 6.66699Z" stroke-width="1.66667" stroke-linecap="round" stroke="#2563EB"/>\n</svg>\n', 'seq_no': 1}]

AUDIT_TABLES = (
    "users",
    "companies",
    "roles",
    "menus",
    "role_menus",
    "permissions",
    "user_roles",
    "role_permissions",
    "refresh_token_sessions",
    "password_reset_tokens",
    "departments",
    "entities",
    "employee_employment_details",
    "employee_personal_details",
    "employee_contact_details",
    "employee_bank_details",
    "employee_documents",
    "employee_skills_and_interests",
    "onboarding_invitations",
    "email_dispatch_outbox",
)

LEGACY_EMPLOYEE_TABLES = (
    "employee_employment_details",
    "employee_personal_details",
    "employee_contact_details",
    "employee_bank_details",
    "employee_documents",
    "employee_skills_and_interests",
)


def _assert_empty(table: str) -> None:
    count = op.get_bind().execute(
        sa.text(f'SELECT count(*) FROM public."{table}"')
    ).scalar_one()
    if count:
        raise RuntimeError(f"Refusing to reshape non-empty table {table}")


def _assert_empty_audit_values(table: str) -> None:
    columns = set(
        op.get_bind()
        .execute(
            sa.text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name=:table"
            ),
            {"table": table},
        )
        .scalars()
    )
    if not {"created_by", "updated_by", "is_deleted"}.issubset(columns):
        return
    count = op.get_bind().execute(
        sa.text(
            f'SELECT count(*) FROM public."{table}" '
            "WHERE created_by IS NOT NULL OR updated_by IS NOT NULL "
            "OR is_deleted IS TRUE"
        )
    ).scalar_one()
    if count:
        raise RuntimeError(f"Refusing to discard populated audit values in {table}")


def _assert_safe_preconditions() -> None:
    if context.is_offline_mode():
        op.execute(sa.text("""
            DO $$ BEGIN
                IF to_regclass('public.master_data') IS NOT NULL THEN
                    RAISE EXCEPTION 'master_data must remain absent';
                END IF;
                IF EXISTS (SELECT 1 FROM public.roles)
                   OR EXISTS (SELECT 1 FROM public.permissions)
                   OR EXISTS (SELECT 1 FROM public.companies)
                   OR EXISTS (SELECT 1 FROM public.employee_details)
                   OR EXISTS (SELECT 1 FROM public.employee_employment_details)
                   OR EXISTS (SELECT 1 FROM public.employee_personal_details)
                   OR EXISTS (SELECT 1 FROM public.employee_contact_details)
                   OR EXISTS (SELECT 1 FROM public.employee_bank_details)
                   OR EXISTS (SELECT 1 FROM public.employee_documents)
                   OR EXISTS (SELECT 1 FROM public.employee_skills_and_interests)
                   OR EXISTS (SELECT 1 FROM public.onboarding_invitations) THEN
                    RAISE EXCEPTION 'Refusing to reshape non-empty HRMS tables';
                END IF;
                IF EXISTS (SELECT 1 FROM public.users WHERE is_deleted IS TRUE) THEN
                    RAISE EXCEPTION 'Cannot restore users.deleted_at exactly';
                END IF;
            END $$;
        """))
        return

    bind = op.get_bind()
    if bind.execute(sa.text("SELECT to_regclass('public.master_data')")).scalar():
        raise RuntimeError(
            "master_data is expected to remain absent; this migration will not recreate it"
        )
    for table in (
        "roles",
        "permissions",
        "companies",
        *LEGACY_EMPLOYEE_TABLES,
        "employee_details",
        "onboarding_invitations",
    ):
        _assert_empty(table)

    if bind.execute(
        sa.text("SELECT count(*) FROM public.users WHERE is_deleted IS TRUE")
    ).scalar_one():
        raise RuntimeError(
            "Cannot restore users.deleted_at exactly while is_deleted is true"
        )

    for table in AUDIT_TABLES:
        _assert_empty_audit_values(table)

    if bind.execute(
        sa.text("SELECT count(*) FROM public.permissions WHERE created_at IS NOT NULL")
    ).scalar_one():
        raise RuntimeError("Refusing to reshape populated permissions table")


def _insert_rows(table_name: str, columns: tuple[sa.Column, ...], rows: list[dict]) -> None:
    if not rows:
        return
    table = sa.table(table_name, *columns, schema="public")
    op.bulk_insert(table, [{**row, "id": UUID(row["id"])} for row in rows])


def upgrade() -> None:
    _assert_safe_preconditions()

    op.create_table(
        "departments",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["public.companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_departments"),
        sa.UniqueConstraint("company_id", "name", name="uq_departments_company_name"),
        sa.UniqueConstraint("company_id", "code", name="uq_departments_company_code"),
        schema="public",
    )
    op.create_index("ix_departments_company_active", "departments", ["company_id", "is_active"], schema="public")

    op.create_table(
        "entities",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("next_employee_sequence", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("next_employee_sequence >= 0", name="ck_entities_sequence_nonnegative"),
        sa.ForeignKeyConstraint(["company_id"], ["public.companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_entities"),
        sa.UniqueConstraint("company_id", "code", name="uq_entities_company_code"),
        schema="public",
    )
    op.create_index("ix_entities_company_active", "entities", ["company_id", "is_active"], schema="public")

    op.create_table(
        "menus",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("menu_name", sa.String(100), nullable=False),
        sa.Column("menu_icon_svg", sa.Text(), nullable=False),
        sa.Column("seq_no", sa.Integer(), nullable=False),
        sa.CheckConstraint("seq_no >= 0", name="ck_menus_seq_no_nonnegative"),
        sa.PrimaryKeyConstraint("id", name="pk_menus"),
        sa.UniqueConstraint("menu_name", name="uq_menus_menu_name"),
        schema="public",
    )

    _insert_rows(
        "roles",
        (
            sa.Column("id", sa.Uuid()), sa.Column("role_code", sa.String(50)),
            sa.Column("role_name", sa.String(100)), sa.Column("description", sa.Text()),
            sa.Column("is_system_role", sa.Boolean()), sa.Column("is_active", sa.Boolean()),
        ),
        ROLE_ROWS,
    )
    _insert_rows(
        "permissions",
        (
            sa.Column("id", sa.Uuid()), sa.Column("permission_code", sa.String(100)),
            sa.Column("permission_name", sa.String(150)), sa.Column("module_name", sa.String(100)),
            sa.Column("description", sa.Text()),
        ),
        PERMISSION_ROWS,
    )
    _insert_rows(
        "menus",
        (
            sa.Column("id", sa.Uuid()), sa.Column("menu_name", sa.String(100)),
            sa.Column("menu_icon_svg", sa.Text()), sa.Column("seq_no", sa.Integer()),
        ),
        MENU_ROWS,
    )

    op.add_column("users", sa.Column("company_id", sa.Uuid(), nullable=True), schema="public")
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True), schema="public")
    op.create_foreign_key(
        "fk_users_company_id_companies", "users", "companies", ["company_id"], ["id"],
        ondelete="RESTRICT", source_schema="public", referent_schema="public",
    )
    op.drop_index("uq_users_email_lower", table_name="users", schema="public")
    op.create_index(
        "uq_users_email_lower", "users", [sa.text("lower(email)")], unique=True,
        schema="public", postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_users_company_id", "users", ["company_id"], schema="public",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.add_column("employee_employment_details", sa.Column("department_id", sa.Uuid(), nullable=True), schema="public")
    op.add_column("employee_employment_details", sa.Column("entity_id", sa.Uuid(), nullable=True), schema="public")
    op.add_column(
        "employee_employment_details",
        sa.Column("profile_status", sa.String(20), server_default="PENDING", nullable=False),
        schema="public",
    )
    op.add_column("employee_employment_details", sa.Column("approved_by_user_id", sa.Uuid(), nullable=True), schema="public")
    op.add_column("employee_employment_details", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True), schema="public")
    op.drop_constraint("uq_employee_employment_company_code", "employee_employment_details", type_="unique", schema="public")
    op.drop_constraint("employee_employment_details_user_id_key", "employee_employment_details", type_="unique", schema="public")
    op.create_unique_constraint(
        "uq_employee_employment_company_entity_code", "employee_employment_details",
        ["company_id", "entity_id", "employee_code"], schema="public",
    )
    op.create_unique_constraint(
        "uq_employee_employment_details_user_id", "employee_employment_details",
        ["user_id"], schema="public",
    )
    op.create_check_constraint(
        "ck_employee_employment_details_profile_status_valid", "employee_employment_details",
        "profile_status IN ('PENDING','SUBMITTED','APPROVED')", schema="public",
    )
    op.create_foreign_key(
        "fk_employee_employment_details_department_id_departments", "employee_employment_details",
        "departments", ["department_id"], ["id"], ondelete="RESTRICT",
        source_schema="public", referent_schema="public",
    )
    op.create_foreign_key(
        "fk_employee_employment_details_entity_id_entities", "employee_employment_details",
        "entities", ["entity_id"], ["id"], ondelete="RESTRICT",
        source_schema="public", referent_schema="public",
    )
    op.create_foreign_key(
        "fk_employee_employment_details_approved_by_user_id_users", "employee_employment_details",
        "users", ["approved_by_user_id"], ["id"], ondelete="SET NULL",
        source_schema="public", referent_schema="public",
    )

    for index in (
        "idx_employee_employment_company_id",
        "idx_employee_employment_employee_code",
        "idx_employee_employment_company_email",
        "idx_employee_employment_user_id",
        "idx_employee_employment_department",
    ):
        op.drop_index(index, table_name="employee_employment_details", schema="public")
    op.create_index("ix_employee_employment_company_id", "employee_employment_details", ["company_id"], schema="public", postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_index("ix_employee_employment_department", "employee_employment_details", ["company_id", "department_name"], schema="public", postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_index("ix_employee_employment_department_id", "employee_employment_details", ["company_id", "department_id"], schema="public", postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_index("ix_employee_employment_entity_id", "employee_employment_details", ["company_id", "entity_id"], schema="public", postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_index("ix_employee_employment_profile_status", "employee_employment_details", ["company_id", "profile_status"], schema="public", postgresql_where=sa.text("deleted_at IS NULL"))
    op.drop_index("idx_employee_documents_employee_id", table_name="employee_documents", schema="public")
    op.create_index("ix_employee_documents_employee_id", "employee_documents", ["employee_id"], schema="public")

    for table, constraint, target, ondelete in (
        ("user_roles", "fk_user_roles_role_id_master_data", "roles", "RESTRICT"),
        ("role_permissions", "fk_role_permissions_role_id_master_data", "roles", "CASCADE"),
        ("role_permissions", "fk_role_permissions_permission_id_master_data", "permissions", "CASCADE"),
        ("role_menus", "fk_role_menus_role_id_master_data", "roles", "CASCADE"),
        ("role_menus", "fk_role_menus_menu_id_master_data", "menus", "RESTRICT"),
    ):
        op.execute(sa.text(f'ALTER TABLE public."{table}" DROP CONSTRAINT IF EXISTS "{constraint}"'))
        cols = {"user_roles": ["role_id"], "role_permissions": ["role_id"] if "role_id" in constraint else ["permission_id"], "role_menus": ["role_id"] if "role_id" in constraint else ["menu_id"]}[table]
        op.create_foreign_key(
            f"fk_{table}_{cols[0]}_{target}", table, target, cols, ["id"],
            ondelete=ondelete, source_schema="public", referent_schema="public",
        )

    op.execute(sa.text('ALTER TABLE public.permissions DROP COLUMN IF EXISTS created_at'))
    op.execute(sa.text('ALTER TABLE public.onboarding_invitations DROP CONSTRAINT IF EXISTS fk_onboarding_invitations_employee_id_employee_details'))
    op.create_foreign_key(
        op.f("fk_onboarding_invitations_employee_id_employee_employment_details"),
        "onboarding_invitations", "employee_employment_details", ["employee_id"], ["id"],
        ondelete="CASCADE", source_schema="public", referent_schema="public",
    )

    for table in AUDIT_TABLES:
        op.execute(sa.text(f'ALTER TABLE public."{table}" DROP CONSTRAINT IF EXISTS "fk_{table}_created_by_users"'))
        op.execute(sa.text(f'ALTER TABLE public."{table}" DROP CONSTRAINT IF EXISTS "fk_{table}_updated_by_users"'))
        op.execute(sa.text(f'ALTER TABLE public."{table}" DROP COLUMN IF EXISTS created_by'))
        op.execute(sa.text(f'ALTER TABLE public."{table}" DROP COLUMN IF EXISTS updated_by'))
        op.execute(sa.text(f'ALTER TABLE public."{table}" DROP COLUMN IF EXISTS is_deleted'))

    for table in (
        "companies", "roles", "employee_employment_details", "employee_personal_details",
        "employee_contact_details", "employee_bank_details", "employee_skills_and_interests",
    ):
        op.execute(sa.text(f'DROP TRIGGER IF EXISTS "trg_{table}_updated_at" ON public."{table}"'))
    op.execute(sa.text("DROP FUNCTION IF EXISTS public.set_updated_at()"))

    op.drop_table("employee_details", schema="public")


def downgrade() -> None:
    raise RuntimeError(
        "This schema restoration preserves recovered RBAC IDs and is forward-only."
    )
