"""remove legacy HRMS company, employee and master tables

Revision ID: 71e23cd0f92a
Revises: 4b59f22e454c
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "71e23cd0f92a"
down_revision: str | Sequence[str] | None = "4b59f22e454c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMPTY_EMPLOYEE_TABLES = (
    "employee_employment_details",
    "employee_personal_details",
    "employee_contact_details",
    "employee_bank_details",
    "employee_skills_and_interests",
    "employee_documents",
)


def _assert_empty(table: str) -> None:
    if op.get_context().as_sql:
        op.execute(sa.text(f"""
            DO $$ BEGIN
                IF EXISTS (SELECT 1 FROM public."{table}" LIMIT 1) THEN
                    RAISE EXCEPTION 'Refusing to drop non-empty table {table}';
                END IF;
            END $$;
        """))
        return
    count = op.get_bind().execute(
        sa.text(f'SELECT count(*) FROM public."{table}"')
    ).scalar_one()
    if count:
        raise RuntimeError(f"Refusing to drop non-empty table {table}")


def _assert_master_copy(source: str, group_type: str, id_column: str = "id") -> None:
    if op.get_context().as_sql:
        op.execute(sa.text(f"""
            DO $$ BEGIN
                IF EXISTS (
                    SELECT 1 FROM public."{source}" s
                    LEFT JOIN public.master_data m
                      ON m.id = s."{id_column}" AND m.group_type = '{group_type}'
                    WHERE m.id IS NULL
                ) THEN RAISE EXCEPTION 'Master data copy for {source} is incomplete'; END IF;
            END $$;
        """))
        return
    missing = op.get_bind().execute(sa.text(f"""
        SELECT count(*) FROM public."{source}" s
        LEFT JOIN public.master_data m
          ON m.id=s."{id_column}" AND m.group_type=:group_type
        WHERE m.id IS NULL
    """), {"group_type": group_type}).scalar_one()
    if missing:
        raise RuntimeError(f"Master data copy for {source} is incomplete")


def upgrade() -> None:
    # Recheck the verified live state immediately before removing old storage.
    for table in EMPTY_EMPLOYEE_TABLES:
        _assert_empty(table)
    _assert_empty("companies")
    if not op.get_context().as_sql:
        company_users = op.get_bind().execute(
            sa.text("SELECT count(*) FROM public.users WHERE company_id IS NOT NULL")
        ).scalar_one()
        if company_users:
            raise RuntimeError("Refusing to remove companies while users reference one")

    for source, group_type in (
        ("roles", "mst-roles"),
        ("permissions", "mst-permissions"),
        ("menus", "mst-menus"),
        ("departments", "mst-department"),
        ("entities", "mst-entity"),
    ):
        _assert_master_copy(source, group_type)

    op.create_check_constraint(
        "group_type_valid",
        "master_data",
        "group_type IN ('mst-entity','mst-department','mst-roles','mst-permissions','mst-menus')",
    )

    op.drop_constraint(
        "fk_users_company_id_companies", "users", type_="foreignkey", schema="public"
    )
    op.drop_index("ix_users_company_id", table_name="users", schema="public")
    op.drop_index("uq_users_email_lower", table_name="users", schema="public")
    op.drop_column("users", "company_id", schema="public")
    op.drop_column("users", "deleted_at", schema="public")
    op.create_index(
        "uq_users_email_lower",
        "users",
        [sa.text("lower(email)")],
        unique=True,
        postgresql_where=sa.text("is_deleted IS false"),
        schema="public",
    )

    for table in (
        "employee_bank_details",
        "employee_contact_details",
        "employee_documents",
        "employee_personal_details",
        "employee_skills_and_interests",
        "employee_employment_details",
        "departments",
        "entities",
        "roles",
        "permissions",
        "menus",
        "companies",
    ):
        op.drop_table(table, schema="public")


def downgrade() -> None:
    raise RuntimeError(
        "This cutover migration is forward-only; removed duplicate tables are not recreated."
    )
