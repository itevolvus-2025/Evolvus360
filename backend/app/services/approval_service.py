"""Employee approval queue, audited decisions, and credential delivery."""

import secrets
import string
from datetime import UTC, datetime, timedelta
from cryptography.fernet import Fernet, InvalidToken
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.config import get_settings
from app.core.security import hash_password
from app.core.config import get_settings
from app.models.hrms import (
    EmailDispatchOutbox,
    EmployeeApprovalDecision,
    EmployeeEmploymentDetails,
    Role,
    User,
    UserRole,
)
from app.services import email_dispatch


def _optional_uan(encrypted_value: str | None) -> str | None:
    if not encrypted_value:
        return None
    key = get_settings().pii_encryption_key
    if key is None:
        return None
    try:
        return Fernet(key.get_secret_value().encode("ascii")).decrypt(
            encrypted_value.encode()
        ).decode()
    except (InvalidToken, ValueError, UnicodeEncodeError):
        return None


def _temp_password() -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%*-_"
    chars = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%*-_"),
    ]
    chars.extend(secrets.choice(alphabet) for _ in range(28))
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


def _queue_approval_email(
    db: Session, employee: EmployeeEmploymentDetails, password: str
) -> EmailDispatchOutbox:
    user = employee.user
    settings = get_settings()
    user.email = employee.company_email
    expires_at = datetime.now(UTC) + timedelta(
        hours=settings.temporary_password_expire_hours
    )
    user.password_hash = hash_password(password)
    user.must_change_password = True
    user.temporary_password_expires_at = expires_at
    user.temporary_password_used_at = None
    return email_dispatch.enqueue(
        db,
        entity_type="EMPLOYEE_APPROVAL",
        entity_id=employee.id,
        recipient=employee.company_email,
        template_key="GENERAL_NOTIFICATION",
        variables={
            "subject_line": "Your Evolvus360 employee account is approved",
            "message_text": (
                f"Hello {employee.first_name}, your onboarding is approved. "
                f"Login ID: {user.email}. Temporary one-time password: {password}. "
                f"Sign in at {settings.frontend_login_url} within "
                f"{settings.temporary_password_expire_hours} hours and change "
                "your password before using the application."
            ),
        },
    )


def list_pending(
    db: Session,
    *,
    page: int,
    page_size: int,
    search: str | None,
    onboarding_status: str | None,
) -> dict:
    query = select(EmployeeEmploymentDetails).where(
        EmployeeEmploymentDetails.deleted_at.is_(None)
    )
    state = (onboarding_status or "PENDING_APPROVAL").upper()
    if state not in {"PENDING_APPROVAL", "REJECTED", "APPROVED"}:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid onboarding status"
        )
    query = query.where(EmployeeEmploymentDetails.onboarding_status == state)
    if search:
        pattern = f"%{search.strip()}%"
        conditions = [
            EmployeeEmploymentDetails.first_name.ilike(pattern),
            EmployeeEmploymentDetails.middle_name.ilike(pattern),
            EmployeeEmploymentDetails.last_name.ilike(pattern),
            func.concat(
                EmployeeEmploymentDetails.first_name,
                " ",
                EmployeeEmploymentDetails.last_name,
            ).ilike(pattern),
            EmployeeEmploymentDetails.company_email.ilike(pattern),
            EmployeeEmploymentDetails.personal_email.ilike(pattern),
            EmployeeEmploymentDetails.employee_code.ilike(pattern),
            EmployeeEmploymentDetails.department_name.ilike(pattern),
            EmployeeEmploymentDetails.designation.ilike(pattern),
            select(UserRole.id)
            .join(Role, UserRole.role_id == Role.id)
            .where(
                UserRole.user_id == EmployeeEmploymentDetails.user_id,
                or_(
                    Role.role_name.ilike(pattern),
                    Role.role_code.ilike(pattern),
                ),
            )
            .exists(),
        ]
        try:
            conditions.append(EmployeeEmploymentDetails.id == UUID(search))
        except ValueError:
            pass
        query = query.where(or_(*conditions))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(EmployeeEmploymentDetails.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [
            {
                "employee_id": str(row.id),
                "employee_code": row.employee_code,
                "name": f"{row.first_name} {row.last_name}".strip(),
                "email": row.company_email,
                "department": row.department_name,
                "designation": row.designation,
                "onboarding_status": row.onboarding_status,
                "submitted_at": row.invitation.submitted_at if row.invitation else None,
            }
            for row in rows
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


def details(db: Session, employee_id: UUID) -> dict:
    employee = db.scalar(
        select(EmployeeEmploymentDetails)
        .options(
            joinedload(EmployeeEmploymentDetails.user),
            joinedload(EmployeeEmploymentDetails.personal_details),
            joinedload(EmployeeEmploymentDetails.contact_details),
            joinedload(EmployeeEmploymentDetails.bank_details),
            joinedload(EmployeeEmploymentDetails.skills_and_interests),
            joinedload(EmployeeEmploymentDetails.invitation),
            selectinload(EmployeeEmploymentDetails.documents),
        )
        .where(
            or_(
                EmployeeEmploymentDetails.id == employee_id,
                EmployeeEmploymentDetails.user_id == employee_id,
            ),
            EmployeeEmploymentDetails.deleted_at.is_(None),
        )
    )
    if employee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
    personal, contact, bank, skills = (
        employee.personal_details,
        employee.contact_details,
        employee.bank_details,
        employee.skills_and_interests,
    )
    decisions = db.scalars(
        select(EmployeeApprovalDecision)
        .where(EmployeeApprovalDecision.employee_id == employee.id)
        .order_by(EmployeeApprovalDecision.created_at)
    ).all()
    return {
        "employee_id": str(employee.id),
        "employee_code": employee.employee_code,
        "name": " ".join(
            part
            for part in (employee.first_name, employee.middle_name, employee.last_name)
            if part
        ),
        "account": {
            "email": employee.user.email,
            "status": employee.user.account_status,
        },
        "employment": {
            "company_email": employee.company_email,
            "personal_email": employee.personal_email,
            "department": employee.department_name,
            "entity": employee.entity_name,
            "designation": employee.designation,
            "work_location": employee.work_location,
            "joining_date": employee.joining_date,
            "employment_start_date": employee.employment_start_date,
            "employment_end_date": employee.employment_end_date,
            "pf_applicable": employee.pf_applicable,
        },
        "personal_details": None
        if personal is None
        else {
            "birth_date": personal.birth_date,
            "gender": personal.gender,
            "aadhaar_last_four": personal.aadhaar_number_last_four,
            "pan_present": bool(personal.pan_number_encrypted),
            "passport_present": bool(personal.passport_number_encrypted),
            "uan_number": _optional_uan(personal.uan_number_encrypted),
            "blood_group": personal.blood_group,
            "marital_status": personal.marital_status,
        },
        "contact_details": None
        if contact is None
        else {
            "mobile_number": contact.mobile_number,
            "landline_number": contact.landline_number,
            "alternate_phone_number": contact.alternate_phone_number,
            "emergency_contact_name": contact.emergency_contact_name,
            "emergency_contact_phone": contact.emergency_contact_phone,
            "emergency_contact_relation": contact.emergency_contact_relation,
        },
        "bank_details": None
        if bank is None
        else {
            "bank_name": bank.bank_name,
            "account_number_last_four": bank.bank_account_number_last_four,
            "ifsc_code": bank.ifsc_code,
            "verification_status": bank.verification_status,
        },
        "skills_and_interests": None
        if skills is None
        else {
            "qualifications": skills.additional_qualifications,
            "skills": skills.additional_skills,
            "hobbies": skills.hobbies,
            "languages_spoken": skills.languages_spoken,
            "languages_read_and_written": skills.languages_read_and_written,
        },
        "documents": [
            {
                "id": str(doc.id),
                "document_type": doc.document_type,
                "filename": doc.original_filename,
                "mime_type": doc.mime_type,
                "size_bytes": doc.file_size_bytes,
                "verification_status": doc.verification_status,
                "download_url": (
                    f"/api/v1/approvals/employees/{employee.id}/documents/{doc.id}"
                ),
            }
            for doc in employee.documents
        ],
        "submitted_at": employee.invitation.submitted_at
        if employee.invitation
        else None,
        "onboarding_status": employee.onboarding_status,
        "profile_status": employee.profile_status,
        "approved_by_user_id": str(employee.approved_by_user_id)
        if employee.approved_by_user_id
        else None,
        "approved_at": employee.approved_at,
        "rejection_reason": employee.rejection_reason,
        "history": [
            {
                "action": d.action,
                "actor_user_id": str(d.actor_user_id),
                "reason": d.reason,
                "previous_submission_preserved": bool(d.snapshot_encrypted),
                "created_at": d.created_at,
            }
            for d in decisions
        ],
    }


def approve(db: Session, actor: User, employee_id: UUID) -> dict:
    try:
        employee = db.scalar(
            select(EmployeeEmploymentDetails)
            .options(
                joinedload(EmployeeEmploymentDetails.user),
                joinedload(EmployeeEmploymentDetails.personal_details),
                joinedload(EmployeeEmploymentDetails.contact_details),
                joinedload(EmployeeEmploymentDetails.bank_details),
                selectinload(EmployeeEmploymentDetails.documents),
            )
            .where(
                or_(
                    EmployeeEmploymentDetails.id == employee_id,
                    EmployeeEmploymentDetails.user_id == employee_id,
                ),
                EmployeeEmploymentDetails.deleted_at.is_(None),
            )
            .with_for_update(of=EmployeeEmploymentDetails)
        )
        if employee is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
        if employee.onboarding_status != "PENDING_APPROVAL":
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Employee is not pending approval"
            )
        if not employee.company_email:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Company email is required before login credentials can be issued",
            )
        docs = {d.document_type for d in employee.documents}
        if not {"identity_proof", "cancelled_cheque"}.issubset(docs) or not all(
            (employee.personal_details, employee.contact_details, employee.bank_details)
        ):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Required onboarding details or documents are missing",
            )
        password = _temp_password()
        now = datetime.now(UTC)
        employee.user.account_status = "ACTIVE"
        employee.user.is_active = True
        email_row = _queue_approval_email(db, employee, password)
        employee.profile_status = employee.onboarding_status = "APPROVED"
        employee.approved_by_user_id = actor.id
        employee.approved_at = now
        employee.rejection_reason = None
        db.add(
            EmployeeApprovalDecision(
                employee_id=employee.id, action="APPROVED", actor_user_id=actor.id
            )
        )
        db.commit()
    except BaseException:
        db.rollback()
        raise
    sent = email_dispatch.dispatch(email_row.id)
    return {
        "employee_id": str(employee.id),
        "onboarding_status": "APPROVED",
        "email_dispatch_status": "DISPATCHED" if sent else "FAILED",
    }


def reject(db: Session, actor: User, employee_id: UUID, reason: str) -> dict:
    reason = reason.strip()
    if not reason:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Rejection reason is required"
        )
    try:
        employee = db.scalar(
            select(EmployeeEmploymentDetails)
            .options(
                joinedload(EmployeeEmploymentDetails.user),
                joinedload(EmployeeEmploymentDetails.invitation),
            )
            .where(
                or_(
                    EmployeeEmploymentDetails.id == employee_id,
                    EmployeeEmploymentDetails.user_id == employee_id,
                ),
                EmployeeEmploymentDetails.deleted_at.is_(None),
            )
            .with_for_update(of=EmployeeEmploymentDetails)
        )
        if employee is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
        if employee.onboarding_status != "PENDING_APPROVAL":
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Employee is not pending approval"
            )
        employee.onboarding_status = employee.profile_status = "REJECTED"
        employee.rejection_reason = reason
        if employee.user:
            employee.user.account_status = "INVITED"
            employee.user.is_active = True
            employee.user.password_hash = None
            employee.user.must_change_password = False
            employee.user.temporary_password_expires_at = None
            employee.user.temporary_password_used_at = None
        now = datetime.now(UTC)
        if employee.invitation is not None:
            employee.invitation.invitation_status = "REVOKED"
        db.add(
            EmployeeApprovalDecision(
                employee_id=employee.id,
                action="REJECTED",
                actor_user_id=actor.id,
                reason=reason,
            )
        )
        recipients = [employee.personal_email.strip()] if employee.personal_email else []
        email_rows = [
            email_dispatch.enqueue(
                db,
                entity_type="EMPLOYEE_REJECTION",
                entity_id=employee.id,
                recipient=recipient,
                template_key="EMPLOYEE_PROFILE_REJECTED",
                variables={
                    "employee_name": employee.first_name,
                    "rejection_reason": reason,
                },
            )
            for recipient in recipients
        ]
        db.commit()
    except BaseException:
        db.rollback()
        raise
    sent = bool(email_rows) and all(
        email_dispatch.dispatch(email_row.id) for email_row in email_rows
    )
    return {
        "employee_id": str(employee.id),
        "onboarding_status": "REJECTED",
        "rejection_reason": reason,
        "email_dispatch_status": "DISPATCHED" if sent else "FAILED",
        "rejected_at": now,
    }


def retry_email(db: Session, employee_id: UUID, event: str) -> dict:
    entity_type = {
        "approval": "EMPLOYEE_APPROVAL",
        "rejection": "EMPLOYEE_REJECTION",
    }.get(event)
    if entity_type is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid email event")
    row = db.scalar(
        select(EmailDispatchOutbox)
        .where(
            EmailDispatchOutbox.entity_type == entity_type,
            EmailDispatchOutbox.entity_id == employee_id,
            EmailDispatchOutbox.status != "DISPATCHED",
        )
        .order_by(EmailDispatchOutbox.created_at.desc())
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Retryable email was not found")
    employee = db.scalar(
        select(EmployeeEmploymentDetails).where(
            or_(
                EmployeeEmploymentDetails.id == employee_id,
                EmployeeEmploymentDetails.user_id == employee_id,
            ),
            EmployeeEmploymentDetails.deleted_at.is_(None),
        )
    )
    if (
        employee is None
        or not employee.personal_email
        or row.recipient_email.casefold() != employee.personal_email.casefold()
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Email retry requires the current personal email as recipient",
        )
    sent = email_dispatch.retry(row.id, entity_type=entity_type, entity_id=employee_id)
    return {"email_dispatch_status": "DISPATCHED" if sent else "FAILED"}


def regenerate_credentials(db: Session, actor: User, employee_id: UUID) -> dict:
    try:
        employee = db.scalar(
            select(EmployeeEmploymentDetails)
            .options(joinedload(EmployeeEmploymentDetails.user))
            .where(
                or_(
                    EmployeeEmploymentDetails.id == employee_id,
                    EmployeeEmploymentDetails.user_id == employee_id,
                ),
                EmployeeEmploymentDetails.deleted_at.is_(None),
            )
            .with_for_update(of=EmployeeEmploymentDetails)
        )
        if employee is None or employee.onboarding_status != "APPROVED":
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Approved employee was not found"
            )
        if not employee.company_email:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Company email is required before login credentials can be issued",
            )
        password = _temp_password()
        row = _queue_approval_email(db, employee, password)
        db.commit()
    except BaseException:
        db.rollback()
        raise
    sent = email_dispatch.dispatch(row.id)
    return {
        "employee_id": str(employee.id),
        "email_dispatch_status": "DISPATCHED" if sent else "FAILED",
    }
