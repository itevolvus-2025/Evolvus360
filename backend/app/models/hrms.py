"""HRMS authentication, employee, and onboarding persistence models."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.database.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin

JSON_DOCUMENT = JSON().with_variant(JSONB(), "postgresql")


def _id() -> Mapped[UUID]:
    return mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)


class User(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "account_status IN ('INVITED','PENDING_APPROVAL','ACTIVE',"
            "'INACTIVE','LOCKED')",
            name="account_status",
        ),
        CheckConstraint(
            "failed_login_attempts >= 0", name="failed_login_attempts_nonnegative"
        ),
        Index(
            "uq_users_email_lower",
            func.lower(text("email")),
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
            sqlite_where=text("deleted_at IS NULL"),
        ),
        {"schema": None},
    )
    id: Mapped[UUID] = _id()
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    phone_number: Mapped[str | None] = mapped_column(String(25))
    account_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="INVITED"
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    temporary_password_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    temporary_password_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    employee: Mapped[EmployeeEmploymentDetails | None] = relationship(
        back_populates="user",
        foreign_keys="EmployeeEmploymentDetails.user_id",
        uselist=False,
    )
    refresh_sessions: Mapped[list[RefreshTokenSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    role_assignments: Mapped[list[UserRole]] = relationship(
        back_populates="user",
        foreign_keys="UserRole.user_id",
        cascade="all, delete-orphan",
    )


class Role(TimestampMixin, Base):
    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("role_code", name="uq_roles_role_code"),
        Index(
            "uq_roles_active_name_lower",
            func.lower(text("role_name")),
            unique=True,
            postgresql_where=text("is_deleted IS false AND is_active IS true"),
            sqlite_where=text("is_deleted IS false AND is_active IS true"),
        ),
        {"schema": None},
    )
    id: Mapped[UUID] = _id()
    role_code: Mapped[str] = mapped_column(String(50), nullable=False)
    role_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_system_role: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    permissions: Mapped[list[str]] = mapped_column(
        JSON_DOCUMENT,
        nullable=False,
        default=list,
        server_default=text("'[]'"),
    )
    assignments: Mapped[list[UserRole]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )
    permission_assignments: Mapped[list[RolePermission]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("permission_code", name="uq_permissions_permission_code"),
        {"schema": None},
    )
    id: Mapped[UUID] = _id()
    permission_code: Mapped[str] = mapped_column(String(100), nullable=False)
    permission_name: Mapped[str] = mapped_column(String(150), nullable=False)
    module_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    role_assignments: Mapped[list[RolePermission]] = relationship(
        back_populates="permission", cascade="all, delete-orphan"
    )


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
        {"schema": None},
    )
    id: Mapped[UUID] = _id()
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False
    )
    assigned_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    assigned_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    user: Mapped[User] = relationship(
        back_populates="role_assignments", foreign_keys=[user_id]
    )
    role: Mapped[Role] = relationship(back_populates="assignments")
    assigned_by: Mapped[User | None] = relationship(foreign_keys=[assigned_by_user_id])


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint(
            "role_id", "permission_id", name="uq_role_permissions_role_permission"
        ),
        {"schema": None},
    )
    id: Mapped[UUID] = _id()
    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    permission_id: Mapped[UUID] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    role: Mapped[Role] = relationship(back_populates="permission_assignments")
    permission: Mapped[Permission] = relationship(back_populates="role_assignments")


class RefreshTokenSession(Base):
    __tablename__ = "refresh_token_sessions"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_refresh_token_sessions_token_hash"),
        CheckConstraint("expires_at > created_at", name="expiry_after_creation"),
        Index(
            "ix_refresh_token_sessions_active",
            "user_id",
            "expires_at",
            postgresql_where=text("revoked_at IS NULL"),
        ),
        {"schema": None},
    )
    id: Mapped[UUID] = _id()
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    token_family_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("refresh_token_sessions.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(Text)
    user: Mapped[User] = relationship(back_populates="refresh_sessions")
    replaced_by: Mapped[RefreshTokenSession | None] = relationship(
        remote_side="RefreshTokenSession.id"
    )


class PasswordResetToken(Base):
    """Single-use, hashed password reset tokens with bounded lifetime."""

    __tablename__ = "password_reset_tokens"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_password_reset_tokens_token_hash"),
        Index(
            "ix_password_reset_tokens_user_active",
            "user_id",
            "expires_at",
            postgresql_where=text("used_at IS NULL AND revoked_at IS NULL"),
        ),
        {"schema": None},
    )
    id: Mapped[UUID] = _id()
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    user: Mapped[User] = relationship()


class Department(TimestampMixin, Base):
    __tablename__ = "departments"
    __table_args__ = ({"schema": None},)
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    employees: Mapped[list[EmployeeEmploymentDetails]] = relationship(
        back_populates="department"
    )


class Entity(TimestampMixin, Base):
    __tablename__ = "entities"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    employees: Mapped[list[EmployeeEmploymentDetails]] = relationship(
        back_populates="entity"
    )


class EmployeeEmploymentDetails(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "employee_employment_details"
    __table_args__ = (
        CheckConstraint(
            "employment_end_date IS NULL OR employment_end_date >= "
            "employment_start_date",
            name="employment_end_date_valid",
        ),
        CheckConstraint(
            "onboarding_status IN ('INVITED','ONBOARDING','DRAFT_SAVED','SUBMITTED',"
            "'PENDING_APPROVAL','CHANGES_REQUESTED','APPROVED','REJECTED')",
            name="onboarding_status_valid",
        ),
        CheckConstraint(
            "employment_status IN ('ACTIVE','INACTIVE','ON_LEAVE','TERMINATED')",
            name="employment_status_valid",
        ),
        CheckConstraint(
            "profile_status IN ('PENDING','SUBMITTED','PENDING_APPROVAL',"
            "'APPROVED','REJECTED')",
            name="profile_status_valid",
        ),
        Index(
            "ix_employee_employment_department",
            "department_name",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_employee_employment_department_id",
            "department_id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_employee_employment_entity_id",
            "entity_id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_employee_employment_profile_status",
            "profile_status",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        {"schema": None},
    )
    id: Mapped[UUID] = _id()
    department_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT")
    )
    entity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("entities.id", ondelete="RESTRICT")
    )
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), unique=True
    )
    employee_code: Mapped[str] = mapped_column(String(50), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    middle_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_name: Mapped[str | None] = mapped_column(String(150))
    department_name: Mapped[str] = mapped_column(String(150), nullable=False)
    designation: Mapped[str] = mapped_column(String(150), nullable=False)
    work_location: Mapped[str | None] = mapped_column(String(150))
    company_email: Mapped[str | None] = mapped_column(String(255))
    personal_email: Mapped[str] = mapped_column(String(255), nullable=False)
    pf_applicable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    joining_date: Mapped[date] = mapped_column(Date, nullable=False)
    employment_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    employment_end_date: Mapped[date | None] = mapped_column(Date)
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    onboarding_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="INVITED"
    )
    profile_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="PENDING"
    )
    approved_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    last_change_reason: Mapped[str | None] = mapped_column(Text)
    employment_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="ACTIVE"
    )
    department: Mapped[Department | None] = relationship(back_populates="employees")
    entity: Mapped[Entity | None] = relationship(back_populates="employees")
    user: Mapped[User | None] = relationship(
        back_populates="employee", foreign_keys=[user_id]
    )
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_user_id])
    approved_by: Mapped[User | None] = relationship(foreign_keys=[approved_by_user_id])
    personal_details: Mapped[EmployeePersonalDetails | None] = relationship(
        back_populates="employee", cascade="all, delete-orphan", uselist=False
    )
    contact_details: Mapped[EmployeeContactDetails | None] = relationship(
        back_populates="employee", cascade="all, delete-orphan", uselist=False
    )
    bank_details: Mapped[EmployeeBankDetails | None] = relationship(
        back_populates="employee", cascade="all, delete-orphan", uselist=False
    )
    documents: Mapped[list[EmployeeDocuments]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    skills_and_interests: Mapped[EmployeeSkillsAndInterests | None] = relationship(
        back_populates="employee", cascade="all, delete-orphan", uselist=False
    )
    invitation: Mapped[OnboardingInvitation | None] = relationship(
        back_populates="employee", cascade="all, delete-orphan", uselist=False
    )


class EmployeePersonalDetails(TimestampMixin, Base):
    __tablename__ = "employee_personal_details"
    __table_args__ = (
        CheckConstraint(
            "gender IN ('MALE','FEMALE','OTHER','PREFER_NOT_TO_SAY')",
            name="gender_valid",
        ),
        CheckConstraint(
            "blood_group IS NULL OR blood_group IN ('A+','A-','B+','B-',"
            "'AB+','AB-','O+','O-')",
            name="blood_group_valid",
        ),
        CheckConstraint(
            "marital_status IS NULL OR marital_status IN "
            "('SINGLE','MARRIED','DIVORCED','WIDOWED')",
            name="marital_status_valid",
        ),
        CheckConstraint("birth_date <= CURRENT_DATE", name="birth_date_valid"),
        {"schema": None},
    )
    id: Mapped[UUID] = _id()
    employee_id: Mapped[UUID] = mapped_column(
        ForeignKey("employee_employment_details.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    aadhaar_number_encrypted: Mapped[str | None] = mapped_column(Text)
    aadhaar_number_last_four: Mapped[str | None] = mapped_column(String(4))
    pan_number_encrypted: Mapped[str | None] = mapped_column(Text)
    passport_number_encrypted: Mapped[str | None] = mapped_column(Text)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str] = mapped_column(String(20), nullable=False)
    blood_group: Mapped[str | None] = mapped_column(String(10))
    mother_tongue: Mapped[str | None] = mapped_column(String(50))
    marital_status: Mapped[str | None] = mapped_column(String(20))
    uan_number_encrypted: Mapped[str | None] = mapped_column(Text)
    employee: Mapped[EmployeeEmploymentDetails] = relationship(
        back_populates="personal_details"
    )


class EmployeeContactDetails(TimestampMixin, Base):
    __tablename__ = "employee_contact_details"
    __table_args__ = {"schema": None}
    id: Mapped[UUID] = _id()
    employee_id: Mapped[UUID] = mapped_column(
        ForeignKey("employee_employment_details.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    mobile_number: Mapped[str] = mapped_column(String(25), nullable=False)
    landline_number: Mapped[str | None] = mapped_column(String(25))
    alternate_phone_number: Mapped[str | None] = mapped_column(String(25))
    emergency_contact_name: Mapped[str] = mapped_column(String(150), nullable=False)
    emergency_contact_phone: Mapped[str] = mapped_column(String(25), nullable=False)
    emergency_contact_relation: Mapped[str] = mapped_column(String(50), nullable=False)
    employee: Mapped[EmployeeEmploymentDetails] = relationship(
        back_populates="contact_details"
    )


class EmployeeBankDetails(TimestampMixin, Base):
    __tablename__ = "employee_bank_details"
    __table_args__ = (
        CheckConstraint("ifsc_code ~ '^[A-Z]{4}0[A-Z0-9]{6}$'", name="ifsc_format"),
        CheckConstraint(
            "verification_status IN ('PENDING','VERIFIED','REJECTED')",
            name="verification_status_valid",
        ),
        {"schema": None},
    )
    id: Mapped[UUID] = _id()
    employee_id: Mapped[UUID] = mapped_column(
        ForeignKey("employee_employment_details.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    bank_name: Mapped[str] = mapped_column(String(150), nullable=False)
    bank_account_number_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    bank_account_number_last_four: Mapped[str | None] = mapped_column(String(4))
    ifsc_code: Mapped[str] = mapped_column(String(11), nullable=False)
    account_holder_name: Mapped[str | None] = mapped_column(String(150))
    is_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    verification_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="PENDING"
    )
    employee: Mapped[EmployeeEmploymentDetails] = relationship(
        back_populates="bank_details"
    )


class EmployeeDocuments(Base):
    __tablename__ = "employee_documents"
    __table_args__ = (
        CheckConstraint(
            "file_size_bytes > 0 AND file_size_bytes <= 5242880", name="file_size_valid"
        ),
        CheckConstraint(
            "mime_type IN ('application/pdf','image/jpeg','image/png')",
            name="mime_type_valid",
        ),
        CheckConstraint(
            "verification_status IN ('PENDING','VERIFIED','REJECTED')",
            name="verification_status_valid",
        ),
        UniqueConstraint(
            "employee_id", "document_type", name="uq_employee_documents_employee_type"
        ),
        {"schema": None},
    )
    id: Mapped[UUID] = _id()
    employee_id: Mapped[UUID] = mapped_column(
        ForeignKey("employee_employment_details.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="PENDING"
    )
    ocr_extracted_data: Mapped[dict | None] = mapped_column(JSON_DOCUMENT)
    uploaded_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    verified_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    verified_at: Mapped[datetime | None] = mapped_column()
    employee: Mapped[EmployeeEmploymentDetails] = relationship(
        back_populates="documents"
    )
    uploaded_by: Mapped[User | None] = relationship(foreign_keys=[uploaded_by_user_id])
    verified_by: Mapped[User | None] = relationship(foreign_keys=[verified_by_user_id])


class EmployeeSkillsAndInterests(TimestampMixin, Base):
    __tablename__ = "employee_skills_and_interests"
    __table_args__ = {"schema": None}
    id: Mapped[UUID] = _id()
    employee_id: Mapped[UUID] = mapped_column(
        ForeignKey("employee_employment_details.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    additional_qualifications: Mapped[str | None] = mapped_column(Text)
    additional_skills: Mapped[str | None] = mapped_column(Text)
    hobbies: Mapped[str | None] = mapped_column(Text)
    languages_spoken: Mapped[str | None] = mapped_column(Text)
    languages_read_and_written: Mapped[str | None] = mapped_column(Text)
    employee: Mapped[EmployeeEmploymentDetails] = relationship(
        back_populates="skills_and_interests"
    )


class OnboardingInvitation(TimestampMixin, Base):
    __tablename__ = "onboarding_invitations"
    __table_args__ = (
        UniqueConstraint(
            "invitation_token_hash", name="uq_onboarding_invitations_token_hash"
        ),
        CheckConstraint("current_step BETWEEN 1 AND 3", name="current_step_valid"),
        CheckConstraint(
            "invitation_status IN ('PENDING','SENT','ACCEPTED','EXPIRED','REVOKED')",
            name="invitation_status_valid",
        ),
        CheckConstraint("expires_at > sent_at", name="expiry_after_sent"),
        Index("ix_onboarding_invitations_status", "invitation_status"),
        {"schema": None},
    )
    id: Mapped[UUID] = _id()
    employee_id: Mapped[UUID] = mapped_column(
        ForeignKey("employee_employment_details.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    invitation_token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    current_step: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="1"
    )
    invitation_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="PENDING"
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    draft_form_data: Mapped[dict | None] = mapped_column(JSON_DOCUMENT)
    employee: Mapped[EmployeeEmploymentDetails] = relationship(
        back_populates="invitation"
    )


class EmailDispatchOutbox(TimestampMixin, Base):
    """Encrypted minimum payload needed to safely retry centralized dispatch."""

    __tablename__ = "email_dispatch_outbox"
    __table_args__ = (
        UniqueConstraint(
            "idempotency_key", name="uq_email_dispatch_outbox_idempotency"
        ),
        CheckConstraint(
            "status IN ('PENDING','FAILED','DISPATCHED')", name="status_valid"
        ),
        Index("ix_email_dispatch_outbox_entity", "entity_type", "entity_id"),
        {"schema": None},
    )
    id: Mapped[UUID] = _id()
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    template_key: Mapped[str] = mapped_column(String(100), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(150), nullable=False)
    encrypted_payload: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="PENDING"
    )
    retry_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    last_error: Mapped[str | None] = mapped_column(String(120))
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EmployeeApprovalDecision(Base):
    """Append-only approval/rejection audit history for employee profiles."""

    __tablename__ = "employee_approval_decisions"
    __table_args__ = (
        CheckConstraint(
            "action IN ('APPROVED','REJECTED','RESUBMITTED')", name="action_valid"
        ),
        Index("ix_employee_approval_decisions_employee", "employee_id", "created_at"),
    )
    id: Mapped[UUID] = _id()
    employee_id: Mapped[UUID] = mapped_column(
        ForeignKey("employee_employment_details.id", ondelete="RESTRICT"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text)
    snapshot_encrypted: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
