"""Transactional services for login, token lifecycle, and password recovery."""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    hash_password,
    hash_token,
    new_opaque_token,
    normalize_email,
    validate_password_strength,
    verify_password,
)
from app.models.hrms import (
    EmployeeEmploymentDetails,
    PasswordResetToken,
    RefreshTokenSession,
    Role,
    User,
    UserRole,
)
from app.services import email_dispatch

logger = logging.getLogger(__name__)
EMAIL_NOT_FOUND_ERROR = "The provided email address was not found in the system."
PASSWORD_MISMATCH_ERROR = "The password is incorrect. Please check your password and try again."
INACTIVE_ACCOUNT_ERROR = "Your account is inactive. Please contact HR."
LOCKED_ACCOUNT_ERROR = "Your account is temporarily locked. Please contact HR."
INVALID_TEMPORARY_PASSWORD_ERROR = (
    "Your temporary password has expired or was already used. Please contact HR."
)
RESET_EMAIL_NOT_FOUND_ERROR = "Email is not found in the system."
RESET_ACCOUNT_INACTIVE_ERROR = (
    "The credentials you want to reset are inactive. Please contact HR."
)
SYSTEM_ROLES = (
    ("CONSULTANT", "Consultant"),
    ("EMPLOYEE", "Employee"),
    ("SUPER_ADMIN", "Super Admin"),
    ("HR", "HR"),
)


def _new_password_reset_token() -> str:
    settings = get_settings()
    local_console = settings.app_env.lower() in {"development", "dev", "local"}
    # A fixed reset token is enabled only for local console-email development.
    if local_console and settings.dev_password_reset_token:
        return settings.dev_password_reset_token
    return new_opaque_token()


def _reset_token_hash(raw_token: str, user_id: UUID) -> str:
    settings = get_settings()
    fixed_local_token = (
        settings.app_env.lower() in {"development", "dev", "local"}
        and settings.dev_password_reset_token == raw_token
    )
    # Scope the shared local test token to a user so its stored hashes remain unique.
    return (
        hash_token(f"{raw_token}:{user_id}")
        if fixed_local_token
        else hash_token(raw_token)
    )


def seed_master_roles(db: Session) -> list[tuple[str, str, UUID, bool]]:
    """Insert only missing role codes and commit the master-data transaction once."""
    results = []
    try:
        for code, name in SYSTEM_ROLES:
            role = db.scalar(select(Role).where(Role.role_code == code))
            created = role is None
            if created:
                role = Role(
                    role_code=code, role_name=name, is_system_role=True, is_active=True
                )
                db.add(role)
                db.flush()
            results.append((code, name, role.id, created))
        db.commit()
        return results
    except Exception:
        db.rollback()
        raise


def create_super_admin(
    db: Session, email: str, first_name: str, last_name: str, password: str
) -> User:
    """Create a company-independent administrator and role assignment atomically."""
    normalized = normalize_email(email)
    encoded = hash_password(password)
    try:
        if db.scalar(
            select(User.id).where(
                func.lower(User.email) == normalized,
                User.deleted_at.is_(None),
            )
        ):
            raise ValueError("An account already exists for that email.")
        role = db.scalar(
            select(Role).where(
                Role.role_code == "SUPER_ADMIN",
                Role.is_active.is_(True),
                Role.is_deleted.is_(False),
            )
        )
        if role is None:
            raise LookupError(
                "Super Admin role not found. Please run the master data "
                "seed command first."
            )
        user = User(
            email=normalized,
            password_hash=encoded,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            account_status="ACTIVE",
            is_active=True,
        )
        db.add(user)
        db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id))
        db.commit()
        return user
    except Exception:
        db.rollback()
        raise


def _active_user(db: Session, user_id: UUID) -> User:
    user = db.scalar(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    if user is None or not user.is_active or user.account_status != "ACTIVE":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or inactive account")
    return user


def _user_payload(user: User) -> dict:
    roles = [
        assignment.role
        for assignment in user.role_assignments
        if assignment.role.is_active
        and not getattr(assignment.role, "is_deleted", False)
    ]
    permissions = _permissions_for_roles(roles)
    return {
        "id": str(user.id),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "roles": [
            {"id": str(role.id), "name": role.role_name, "code": role.role_code}
            for role in roles
        ],
        "permissions": permissions,
    }


def _permissions_for_roles(roles: list[Role]) -> list[str]:
    """Combine role JSON permission arrays without changing values or order."""
    permissions: list[str] = []
    seen: set[str] = set()
    for role in roles:
        for permission in role.permissions or []:
            if isinstance(permission, str) and permission not in seen:
                seen.add(permission)
                permissions.append(permission)
    return permissions


def _issue_bundle(
    db: Session, user: User, session: RefreshTokenSession | None = None
) -> dict:
    settings = get_settings()
    access_token, expires_in = create_access_token(str(user.id))
    refresh_token = new_opaque_token()
    now = datetime.now(UTC)
    replacement = RefreshTokenSession(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        token_family_id=session.token_family_id if session else uuid4(),
        expires_at=now + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(replacement)
    if session:
        # Rotation links the previous session to its replacement for reuse detection.
        session.revoked_at = now
        session.last_used_at = now
        session.replaced_by = replacement
    user_payload = _user_payload(user)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "user": user_payload,
        "permissions": user_payload["permissions"],
    }


def login(db: Session, email: str, password: str) -> dict:
    submitted_email = normalize_email(email)
    user = db.scalar(
        select(User)
        .options(
            selectinload(User.role_assignments).joinedload(UserRole.role),
        )
        .where(
            func.lower(User.email) == submitted_email,
            User.deleted_at.is_(None),
        )
        .with_for_update()
    )
    now = datetime.now(UTC)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, EMAIL_NOT_FOUND_ERROR)

    valid_password = verify_password(password, user.password_hash)
    account_is_active = user.is_active and user.account_status == "ACTIVE"
    if account_is_active and user.locked_until and user.locked_until > now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, LOCKED_ACCOUNT_ERROR)

    if not valid_password:
        if account_is_active:
            if user.locked_until and user.locked_until <= now:
                user.failed_login_attempts = 0
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= get_settings().login_max_failed_attempts:
                user.locked_until = now + timedelta(
                    minutes=get_settings().login_lockout_minutes
                )
            db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, PASSWORD_MISMATCH_ERROR)

    if not account_is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INACTIVE_ACCOUNT_ERROR)
    # Employee accounts must sign in with the company address on their linked
    # employment record. Company-independent accounts (such as Super Admins)
    # continue to authenticate with their registered account email.
    employee = user.employee
    if employee is not None and (
        not employee.company_email
        or normalize_email(employee.company_email) != submitted_email
        or employee.deleted_at is not None
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, EMAIL_NOT_FOUND_ERROR)
    if employee is not None and employee.employment_status in {"INACTIVE", "TERMINATED"}:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INACTIVE_ACCOUNT_ERROR)
    if user.must_change_password:
        if (
            user.temporary_password_expires_at is None
            or user.temporary_password_expires_at <= now
            or user.temporary_password_used_at is not None
        ):
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, INVALID_TEMPORARY_PASSWORD_ERROR
            )
        access_token, expires_in = create_access_token(
            str(user.id),
            purpose="temporary_password_change",
            credential_use=now.isoformat(),
        )
        user.temporary_password_used_at = now
        user.last_login_at = now
        user.failed_login_attempts = 0
        user.locked_until = None
        db.commit()
        payload = _user_payload(user)
        return {
            "access_token": access_token,
            "refresh_token": "",
            "token_type": "bearer",
            "expires_in": expires_in,
            "user": payload,
            "permissions": payload["permissions"],
            "password_change_required": True,
        }
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    result = _issue_bundle(db, user)
    db.commit()
    return result


def change_temporary_password(db: Session, user: User, new_password: str) -> None:
    try:
        user.password_hash = hash_password(new_password)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from None
    now = datetime.now(UTC)
    user.must_change_password = False
    user.temporary_password_expires_at = None
    user.temporary_password_used_at = None
    db.query(RefreshTokenSession).filter(
        RefreshTokenSession.user_id == user.id,
        RefreshTokenSession.revoked_at.is_(None),
    ).update({RefreshTokenSession.revoked_at: now}, synchronize_session=False)
    db.commit()


def refresh(db: Session, raw_token: str) -> dict:
    old = db.scalar(
        select(RefreshTokenSession)
        .options(
            joinedload(RefreshTokenSession.user)
            .selectinload(User.role_assignments)
            .joinedload(UserRole.role),
        )
        .where(RefreshTokenSession.token_hash == hash_token(raw_token))
    )
    if old is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    now = datetime.now(UTC)
    if old.revoked_at is not None:
        # Reuse of a rotated token revokes every session in its family.
        if old.replaced_by_session_id is not None:
            db.query(RefreshTokenSession).filter(
                RefreshTokenSession.token_family_id == old.token_family_id,
                RefreshTokenSession.revoked_at.is_(None),
            ).update({RefreshTokenSession.revoked_at: now}, synchronize_session=False)
            db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    if old.expires_at <= now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    user = old.user
    if (
        not user.is_active
        or user.deleted_at is not None
        or user.account_status != "ACTIVE"
        or user.must_change_password
    ):
        old.revoked_at = now
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    result = _issue_bundle(db, user, old)
    db.commit()
    return result


def logout(db: Session, raw_token: str) -> None:
    session = db.scalar(
        select(RefreshTokenSession).where(
            RefreshTokenSession.token_hash == hash_token(raw_token)
        )
    )
    if session and session.revoked_at is None:
        session.revoked_at = datetime.now(UTC)
        db.commit()


def forgot_password(db: Session, email: str) -> None:
    employee = db.scalar(
        select(EmployeeEmploymentDetails)
        .options(joinedload(EmployeeEmploymentDetails.user))
        .where(
            func.lower(EmployeeEmploymentDetails.company_email)
            == normalize_email(email),
            EmployeeEmploymentDetails.deleted_at.is_(None),
        )
    )
    if employee is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            RESET_EMAIL_NOT_FOUND_ERROR,
        )
    user = employee.user
    if (
        user is None
        or user.deleted_at is not None
        or not user.is_active
        or user.account_status != "ACTIVE"
        or user.email.casefold() != employee.company_email.casefold()
        or employee.profile_status != "APPROVED"
        or employee.employment_status in {"INACTIVE", "TERMINATED"}
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            RESET_ACCOUNT_INACTIVE_ERROR,
        )

    recipient_email = employee.company_email
    now = datetime.now(UTC)
    previous_tokens = db.scalars(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
        )
    ).all()
    for previous in previous_tokens:
        if previous.used_at is None and previous.revoked_at is None:
            previous.revoked_at = now
        # Rotate old digests because the local fixed token is reused.
        previous.token_hash = hash_token(new_opaque_token())
    # Reset links are delivered by email, so they must be self-contained and
    # high entropy even when a fixed local-console token is configured.
    raw = new_opaque_token()
    reset = PasswordResetToken(
        user_id=user.id,
        token_hash=_reset_token_hash(raw, user.id),
        expires_at=now
        + timedelta(minutes=get_settings().password_reset_token_expire_minutes),
    )
    db.add(reset)
    url = f"{get_settings().frontend_reset_password_url}?token={raw}"
    dispatch_row = email_dispatch.enqueue(
        db,
        entity_type="PASSWORD_RESET",
        entity_id=user.id,
        recipient=recipient_email,
        template_key="PASSWORD_RESET",
        variables={"reset_link": url},
    )
    db.commit()
    if not email_dispatch.dispatch(dispatch_row.id):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Unable to send password reset instructions",
        )


def reset_password(
    db: Session, raw_token: str, new_password: str, email: str | None = None
) -> None:
    validate_password_strength(new_password)
    # Require high-entropy reset tokens in production deployments.
    if get_settings().app_env.lower() in {"prod", "production"} and len(raw_token) < 32:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Invalid or expired reset token"
        )
    reset = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == hash_token(raw_token)
        )
    )
    settings = get_settings()
    if (
        reset is None
        and raw_token == settings.dev_password_reset_token
        and settings.app_env.lower() in {"development", "dev", "local"}
    ):
        if email is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Email is required with the local development reset token",
            )
        candidate_user = db.scalar(
            select(User).where(
                func.lower(User.email) == normalize_email(email),
                User.deleted_at.is_(None),
            )
        )
        if candidate_user:
            reset = db.scalar(
                select(PasswordResetToken).where(
                    PasswordResetToken.user_id == candidate_user.id,
                    PasswordResetToken.token_hash
                    == _reset_token_hash(raw_token, candidate_user.id),
                )
            )
    now = datetime.now(UTC)
    if (
        reset is None
        or reset.used_at is not None
        or reset.revoked_at is not None
        or reset.expires_at <= now
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Invalid or expired reset token"
        )
    user = db.scalar(
        select(User).where(User.id == reset.user_id, User.deleted_at.is_(None))
    )
    if (
        user is None
        or not user.is_active
        or user.account_status != "ACTIVE"
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, RESET_ACCOUNT_INACTIVE_ERROR
        )
    employee = user.employee
    if employee is not None and (
        employee.deleted_at is not None
        or employee.profile_status != "APPROVED"
        or employee.employment_status in {"INACTIVE", "TERMINATED"}
        or not employee.company_email
        or employee.company_email.casefold() != user.email.casefold()
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, RESET_ACCOUNT_INACTIVE_ERROR
        )
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    user.temporary_password_expires_at = None
    user.temporary_password_used_at = None
    reset.used_at = now
    db.query(RefreshTokenSession).filter(
        RefreshTokenSession.user_id == user.id, RefreshTokenSession.revoked_at.is_(None)
    ).update({RefreshTokenSession.revoked_at: now}, synchronize_session=False)
    db.commit()
