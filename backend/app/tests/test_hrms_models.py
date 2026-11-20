"""Structural checks for the registered HRMS persistence model graph."""

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import configure_mappers

import app.models as models
from app.database.base import Base


def test_all_hrms_models_are_registered_with_uuid_primary_keys() -> None:
    expected = {
        "users",
        "roles",
        "permissions",
        "user_roles",
        "role_permissions",
        "refresh_token_sessions",
        "employee_employment_details",
        "departments",
        "entities",
        "employee_personal_details",
        "employee_contact_details",
        "employee_bank_details",
        "employee_documents",
        "employee_skills_and_interests",
        "onboarding_invitations",
        "password_reset_tokens",
        "email_dispatch_outbox",
        "employee_approval_decisions",
    }
    assert {table.name for table in Base.metadata.tables.values()} == expected
    assert all(table.c.id.primary_key for table in Base.metadata.tables.values())
    assert all(
        table.c.id.type.python_type.__name__ == "UUID"
        for table in Base.metadata.tables.values()
    )
    assert not hasattr(models, "Company")


def test_hrms_relationships_and_constraints_are_configured() -> None:
    configure_mappers()
    employee = Base.metadata.tables["employee_employment_details"]
    assert employee.c.user_id.nullable is True
    assert employee.c.profile_status.server_default is not None
    assert employee.c.department_id.nullable is True
    assert employee.c.entity_id.nullable is True
    assert any(isinstance(c, ForeignKeyConstraint) for c in employee.constraints)
    personal = Base.metadata.tables["employee_personal_details"]
    assert any(
        isinstance(c, UniqueConstraint)
        and {col.name for col in c.columns} == {"employee_id"}
        for c in personal.constraints
    )
    assert any(isinstance(c, CheckConstraint) for c in personal.constraints)
    assert len(Base.metadata.tables["employee_documents"].indexes) >= 1
    assert "company_id" not in Base.metadata.tables["entities"].c
    assert "next_employee_sequence" not in Base.metadata.tables["entities"].c
    assert all("company_id" not in table.c for table in Base.metadata.tables.values())


def test_authentication_timestamps_are_timezone_aware() -> None:
    refresh = Base.metadata.tables["refresh_token_sessions"]
    users = Base.metadata.tables["users"]
    assert refresh.c.expires_at.type.timezone is True
    assert refresh.c.created_at.type.timezone is True
    assert users.c.last_login_at.type.timezone is True


def test_role_soft_delete_audit_fields_and_active_name_index() -> None:
    roles = Base.metadata.tables["roles"]
    assert roles.c.is_deleted.server_default is not None
    assert roles.c.created_by.nullable is True
    assert roles.c.updated_by.nullable is True
    assert isinstance(
        roles.c.permissions.type.dialect_impl(postgresql.dialect()),
        postgresql.JSONB,
    )
    active_name_index = next(
        index for index in roles.indexes if index.name == "uq_roles_active_name_lower"
    )
    assert active_name_index.unique is True
