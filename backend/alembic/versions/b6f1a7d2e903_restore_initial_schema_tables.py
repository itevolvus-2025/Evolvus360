"""restore tables absent from the initial schema reference

Revision ID: b6f1a7d2e903
Revises: 71e23cd0f92a
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b6f1a7d2e903"
down_revision: str | Sequence[str] | None = "71e23cd0f92a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_DDL = {
    'companies': r"""CREATE TABLE public.companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(200) NOT NULL,
    company_code VARCHAR(50) NOT NULL,
    legal_name VARCHAR(255),
    email VARCHAR(255),
    phone_number VARCHAR(25),
    website VARCHAR(255),
    address_line_1 VARCHAR(255),
    address_line_2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    postal_code VARCHAR(20),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_companies_company_code UNIQUE (company_code)
)""",
    'roles': r"""CREATE TABLE public.roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_code VARCHAR(50) NOT NULL,
    role_name VARCHAR(100) NOT NULL,
    description TEXT,
    is_system_role BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_roles_role_code UNIQUE (role_code)
)""",
    'permissions': r"""CREATE TABLE public.permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    permission_code VARCHAR(100) NOT NULL,
    permission_name VARCHAR(150) NOT NULL,
    module_name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_permissions_permission_code UNIQUE (permission_code)
)""",
    'employee_employment_details': r"""CREATE TABLE public.employee_employment_details (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE RESTRICT,
    user_id UUID UNIQUE REFERENCES public.users(id) ON DELETE SET NULL,
    employee_code VARCHAR(50) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    middle_name VARCHAR(100),
    last_name VARCHAR(100) NOT NULL,
    entity_name VARCHAR(150),
    department_name VARCHAR(150) NOT NULL,
    designation VARCHAR(150) NOT NULL,
    work_location VARCHAR(150),
    company_email VARCHAR(255) NOT NULL,
    personal_email VARCHAR(255) NOT NULL,
    pf_applicable BOOLEAN NOT NULL DEFAULT FALSE,
    joining_date DATE NOT NULL,
    employment_start_date DATE NOT NULL,
    employment_end_date DATE,
    created_by_user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
    onboarding_status VARCHAR(30) NOT NULL DEFAULT 'INVITED',
    employment_status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_employee_employment_company_code UNIQUE (company_id, employee_code),
    CONSTRAINT uq_employee_employment_company_email UNIQUE (company_id, company_email),
    CONSTRAINT chk_employee_employment_end_date
        CHECK (employment_end_date IS NULL OR employment_end_date >= employment_start_date),
    CONSTRAINT chk_employee_onboarding_status
        CHECK (onboarding_status IN ('INVITED', 'DRAFT_SAVED', 'SUBMITTED', 'CHANGES_REQUESTED', 'APPROVED')),
    CONSTRAINT chk_employee_employment_status
        CHECK (employment_status IN ('ACTIVE', 'INACTIVE', 'ON_LEAVE', 'TERMINATED'))
)""",
    'employee_personal_details': r"""CREATE TABLE public.employee_personal_details (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL UNIQUE
        REFERENCES public.employee_employment_details(id) ON DELETE CASCADE,
    aadhaar_number_encrypted TEXT,
    aadhaar_number_last_four CHAR(4),
    pan_number_encrypted TEXT,
    passport_number_encrypted TEXT,
    birth_date DATE NOT NULL,
    gender VARCHAR(20) NOT NULL,
    blood_group VARCHAR(10),
    mother_tongue VARCHAR(50),
    marital_status VARCHAR(20),
    uan_number_encrypted TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_employee_personal_gender
        CHECK (gender IN ('MALE', 'FEMALE', 'OTHER', 'PREFER_NOT_TO_SAY')),
    CONSTRAINT chk_employee_personal_blood_group
        CHECK (blood_group IS NULL OR blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')),
    CONSTRAINT chk_employee_personal_marital_status
        CHECK (marital_status IS NULL OR marital_status IN ('SINGLE', 'MARRIED', 'DIVORCED', 'WIDOWED')),
    CONSTRAINT chk_employee_personal_birth_date
        CHECK (birth_date <= CURRENT_DATE)
)""",
    'employee_contact_details': r"""CREATE TABLE public.employee_contact_details (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL UNIQUE
        REFERENCES public.employee_employment_details(id) ON DELETE CASCADE,
    mobile_number VARCHAR(25) NOT NULL,
    landline_number VARCHAR(25),
    alternate_phone_number VARCHAR(25),
    emergency_contact_name VARCHAR(150) NOT NULL,
    emergency_contact_phone VARCHAR(25) NOT NULL,
    emergency_contact_relation VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)""",
    'employee_bank_details': r"""CREATE TABLE public.employee_bank_details (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL UNIQUE
        REFERENCES public.employee_employment_details(id) ON DELETE CASCADE,
    bank_name VARCHAR(150) NOT NULL,
    bank_account_number_encrypted TEXT NOT NULL,
    bank_account_number_last_four CHAR(4),
    ifsc_code VARCHAR(11) NOT NULL,
    account_holder_name VARCHAR(150),
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    verification_status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_employee_bank_ifsc_format
        CHECK (ifsc_code ~ '^[A-Z]{4}0[A-Z0-9]{6}$'),
    CONSTRAINT chk_employee_bank_verification_status
        CHECK (verification_status IN ('PENDING', 'VERIFIED', 'REJECTED'))
)""",
    'employee_documents': r"""CREATE TABLE public.employee_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL
        REFERENCES public.employee_employment_details(id) ON DELETE CASCADE,
    document_type VARCHAR(50) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    storage_path VARCHAR(500) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    verification_status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    ocr_extracted_data JSONB,
    uploaded_by_user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    verified_by_user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    verified_at TIMESTAMPTZ,
    CONSTRAINT chk_employee_documents_file_size
        CHECK (file_size_bytes > 0 AND file_size_bytes <= 5242880),
    CONSTRAINT chk_employee_documents_mime_type
        CHECK (mime_type IN ('application/pdf', 'image/jpeg', 'image/png')),
    CONSTRAINT chk_employee_documents_verification_status
        CHECK (verification_status IN ('PENDING', 'VERIFIED', 'REJECTED'))
)""",
    'employee_skills_and_interests': r"""CREATE TABLE public.employee_skills_and_interests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL UNIQUE
        REFERENCES public.employee_employment_details(id) ON DELETE CASCADE,
    additional_qualifications TEXT,
    additional_skills TEXT,
    hobbies TEXT,
    languages_spoken TEXT,
    languages_read_and_written TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)""",
}

INDEX_DDL = [
    r"""CREATE INDEX idx_companies_active
    ON public.companies (is_active)
    WHERE deleted_at IS NULL""",
    r"""CREATE INDEX idx_employee_employment_company_id
    ON public.employee_employment_details (company_id)
    WHERE deleted_at IS NULL""",
    r"""CREATE INDEX idx_employee_employment_employee_code
    ON public.employee_employment_details (LOWER(employee_code))""",
    r"""CREATE INDEX idx_employee_employment_company_email
    ON public.employee_employment_details (LOWER(company_email))""",
    r"""CREATE INDEX idx_employee_employment_user_id
    ON public.employee_employment_details (user_id)""",
    r"""CREATE INDEX idx_employee_employment_department
    ON public.employee_employment_details (company_id, department_name)
    WHERE deleted_at IS NULL""",
    r"""CREATE UNIQUE INDEX uq_employee_documents_employee_type
    ON public.employee_documents (employee_id, document_type)""",
    r"""CREATE INDEX idx_employee_documents_employee_id
    ON public.employee_documents (employee_id)""",
 ]

TRIGGER_TABLES = (
    "companies",
    "roles",
    "employee_employment_details",
    "employee_personal_details",
    "employee_contact_details",
    "employee_bank_details",
    "employee_skills_and_interests",
)


def upgrade() -> None:
    op.execute(sa.text("""
        CREATE FUNCTION public.set_updated_at()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$
    """))
    for statement in TABLE_DDL.values():
        op.execute(sa.text(statement))
    for statement in INDEX_DDL:
        op.execute(sa.text(statement))
    for table in TRIGGER_TABLES:
        op.execute(sa.text(f"""
            CREATE TRIGGER trg_{table}_updated_at
            BEFORE UPDATE ON public.{table}
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
        """))


def downgrade() -> None:
    bind = op.get_bind()
    for table in TABLE_DDL:
        count = bind.execute(sa.text(f'SELECT count(*) FROM public."{table}"')).scalar_one()
        if count:
            raise RuntimeError(
                f"Refusing to drop restored table {table}: it contains {count} rows"
            )
    for table in reversed(tuple(TABLE_DDL)):
        op.drop_table(table, schema="public")
    op.execute(sa.text("DROP FUNCTION public.set_updated_at()"))
