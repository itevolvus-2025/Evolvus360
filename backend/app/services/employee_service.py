"""Employee administration and invitation onboarding business operations."""

import json
import re
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.config import get_settings
from app.core.security import (
    hash_token,
    new_opaque_token,
    normalize_email,
)
from app.database.session import SessionLocal
from app.models.hrms import (
    Department,
    EmailDispatchOutbox,
    EmployeeApprovalDecision,
    EmployeeBankDetails,
    EmployeeContactDetails,
    EmployeeDocuments,
    EmployeeEmploymentDetails,
    EmployeePersonalDetails,
    EmployeeSkillsAndInterests,
    Entity,
    OnboardingInvitation,
    PasswordResetToken,
    RefreshTokenSession,
    Role,
    User,
    UserRole,
)
from app.schemas.validators import (
    validate_aadhaar,
    validate_mobile,
    validate_pan,
    validate_uan,
)
from app.services import email_dispatch

ALLOWED_ROLES = {"HR", "SUPER_ADMIN"}
PROFILE_STATES = {"PENDING", "SUBMITTED", "PENDING_APPROVAL", "APPROVED", "REJECTED"}


def _field_validation_error(field: str, message: str) -> HTTPException:
    return HTTPException(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        {
            "message": "Validation failed. Please correct the highlighted fields.",
            "errors": {field: message},
        },
    )


def _validate_onboarding_contact_and_compliance(fields: dict, pf_applicable: bool) -> tuple[str, str | None]:
    name = (fields.get("emergency_contact_name") or "").strip()
    if not name or not all(char.isalpha() or char in " '-." for char in name):
        raise _field_validation_error("emergency_contact_name", "Enter a name using letters, spaces, apostrophes, hyphens or periods only.")
    relation = (fields.get("emergency_contact_relationship") or "").strip()
    if not relation or not all(char.isalpha() or char in " '-." for char in relation):
        raise _field_validation_error("emergency_contact_relationship", "Enter a relationship using letters, spaces, apostrophes, hyphens or periods only.")
    phone = fields.get("emergency_contact_phone") or ""
    try:
        validate_mobile(phone)
    except ValueError:
        raise _field_validation_error(
            "emergency_contact_phone", "Mobile number must be exactly 10 digits."
        ) from None
    bank_name = (fields.get("bank_name") or "").strip()
    if not bank_name or not all(char.isalnum() or char in " &().,'-/" for char in bank_name):
        raise _field_validation_error("bank_name", "Enter a valid bank name using letters, numbers, spaces or common punctuation.")
    account = re.sub(r"\s", "", fields.get("account_number") or "")
    if not re.fullmatch(r"[A-Za-z0-9]{6,35}", account):
        raise _field_validation_error("account_number", "Account number must contain 6 to 35 letters or digits.")
    if not re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", (fields.get("ifsc_code") or "").strip().upper()):
        raise _field_validation_error("ifsc_code", "Enter a valid 11-character IFSC code.")
    qualification = (fields.get("qualification") or "").strip()
    if len(qualification) > 4000 or any(not (char.isalnum() or char.isspace()) for char in qualification):
        raise _field_validation_error("qualification", "Qualification may contain letters, numbers and spaces only.")
    uan = (fields.get("uan_number") or "").strip()
    if uan:
        try:
            validate_uan(uan)
        except ValueError as error:
            raise _field_validation_error("uan_number", str(error)) from None
    return account, uan


def _role_codes(user: User) -> set[str]:
    return {
        item.role.role_code
        for item in user.role_assignments
        if item.role.is_active and not getattr(item.role, "is_deleted", False)
    }


def list_departments(db: Session, _user: User) -> list[Department]:
    query = select(Department).where(
        Department.is_active.is_(True),
        func.upper(Department.code).in_({"IT", "CHEMISTRY", "BIOLOGY", "HR"}),
    )
    return list(db.scalars(query.order_by(Department.name)).all())


def list_entities(db: Session) -> list[Entity]:
    query = select(Entity).where(Entity.is_active.is_(True))
    return list(db.scalars(query.order_by(Entity.name)).all())


def list_roles(db: Session) -> list[Role]:
    return list(
        db.scalars(
            select(Role)
            .where(Role.is_active.is_(True), Role.is_deleted.is_(False))
            .order_by(Role.role_name)
        ).all()
    )


def _resolve_masters(
    db: Session,
    actor: User,
    department_id: UUID,
    entity_id: UUID,
    role_id: UUID,
) -> tuple[Department, Entity, Role]:
    department = db.scalar(
        select(Department).where(
            Department.id == department_id,
            Department.is_active.is_(True),
        )
    )
    entity = db.scalar(
        select(Entity).where(
            Entity.id == entity_id,
            Entity.is_active.is_(True),
        )
    )
    role = db.scalar(
        select(Role).where(
            Role.id == role_id,
            Role.is_active.is_(True),
            Role.is_deleted.is_(False),
        )
    )
    if department is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Department is not active",
        )
    if entity is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Entity is not active"
        )
    if role is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Role is not active")
    if role.role_code == "SUPER_ADMIN" and "SUPER_ADMIN" not in _role_codes(actor):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "HR cannot assign the Super Admin role"
        )
    return department, entity, role


def _employee_prefix(entity_code: str) -> str:
    characters = re.findall(r"[A-Za-z0-9]", entity_code)
    if len(characters) < 2:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Entity code must contain at least two letters or digits",
        )
    return "".join(characters[:2]).upper()


def _next_employee_code(db: Session, entity: Entity) -> str:
    prefix = _employee_prefix(entity.code)
    locked_entity = db.scalar(
        select(Entity)
        .where(Entity.id == entity.id, Entity.is_active.is_(True))
        .with_for_update()
    )
    if locked_entity is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Entity is no longer active")
    prefix_pattern = re.compile(rf"{re.escape(prefix)}-(\d{{3}})", re.IGNORECASE)
    used_sequences = [
        int(match.group(1))
        for code in db.scalars(
            select(EmployeeEmploymentDetails.employee_code).where(
                EmployeeEmploymentDetails.entity_id == entity.id
            )
        )
        if (match := prefix_pattern.fullmatch(code)) is not None
    ]
    sequence = max(used_sequences, default=0) + 1
    if sequence > 999:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Employee code sequence is exhausted for this entity",
        )
    return f"{prefix}-{sequence:03d}"


def create_employee(db: Session, actor: User, payload: object) -> dict:
    try:
        if not payload.first_name.strip() or not payload.last_name.strip():
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "First name and last name are required",
            )
        if not payload.designation.strip():
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "Designation is required"
            )
        if payload.start_date < payload.joining_date:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Start date must be on or after joining date",
            )
        if payload.end_date and payload.end_date < payload.start_date:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "End date must be on or after start date",
            )
        department, entity, role = _resolve_masters(
            db,
            actor,
            payload.department_id,
            payload.entity_id,
            payload.role_id,
        )
        company_email = (
            normalize_email(str(payload.company_email))
            if payload.company_email
            else None
        )
        personal_email = normalize_email(str(payload.personal_email))
        login_email = company_email or personal_email
        if db.scalar(
            select(User.id).where(
                func.lower(User.email) == login_email,
                User.deleted_at.is_(None),
            )
        ):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Company email already exists"
                if company_email
                else "Personal email already exists",
            )
        if db.scalar(
            select(EmployeeEmploymentDetails.id).where(
                func.lower(EmployeeEmploymentDetails.personal_email) == personal_email,
                EmployeeEmploymentDetails.deleted_at.is_(None),
            )
        ):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Personal email already exists",
            )

        employee_code = _next_employee_code(db, entity)
        user = User(
            email=login_email,
            first_name=payload.first_name.strip(),
            last_name=payload.last_name.strip(),
            account_status="INVITED",
            is_active=True,
        )
        db.add(user)
        db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id, assigned_by_user_id=actor.id))
        employee = EmployeeEmploymentDetails(
            user_id=user.id,
            department_id=department.id,
            entity_id=entity.id,
            employee_code=employee_code,
            first_name=payload.first_name.strip(),
            middle_name=(payload.middle_name or "").strip() or None,
            last_name=payload.last_name.strip(),
            entity_name=entity.name,
            department_name=department.name,
            designation=payload.designation.strip(),
            work_location=(payload.location or "").strip() or None,
            company_email=company_email,
            personal_email=personal_email,
            pf_applicable=payload.pf_applicable,
            joining_date=payload.joining_date,
            employment_start_date=payload.start_date,
            employment_end_date=payload.end_date,
            created_by_user_id=actor.id,
            onboarding_status="INVITED",
            profile_status="PENDING",
            employment_status="ACTIVE",
        )
        db.add(employee)
        db.flush()
        settings = get_settings()
        db.add(
            OnboardingInvitation(
                employee_id=employee.id,
                invitation_token_hash=hash_token(new_opaque_token()),
                recipient_email=personal_email,
                invitation_status="PENDING",
                expires_at=datetime.now(UTC)
                + timedelta(hours=settings.onboarding_invitation_expire_hours),
            )
        )
        db.commit()
        # The employee and pending invitation are durable before delivery. The
        # invitation sender uses the encrypted outbox, so a temporary email
        # service failure is retryable without recreating either record.
        invitation_db = SessionLocal()
        try:
            invitation_result = send_invitation(invitation_db, actor, user.id)
        except Exception:
            # The user and the initial invitation are already committed. Never
            # report creation as rolled back or create a second employee just
            # because the delivery/outbox configuration is temporarily broken.
            invitation_result = {
                "invitation_status": "PENDING",
                "email_dispatch_status": "FAILED",
            }
        finally:
            invitation_db.close()
        return {
            "id": str(user.id),
            "employee_code": employee_code,
            "profile_status": employee.profile_status,
            "onboarding_status": employee.onboarding_status,
            "invitation_status": invitation_result["invitation_status"],
            "email_dispatch_status": invitation_result["email_dispatch_status"],
        }
    except IntegrityError as error:
        db.rollback()
        sqlstate = getattr(error.orig, "sqlstate", None) or getattr(
            error.orig, "pgcode", None
        )
        column_name = getattr(getattr(error.orig, "diag", None), "column_name", None)
        if sqlstate == "23502" and column_name == "company_id":
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "HRMS schema is behind; run Alembic upgrade head",
            ) from None
        if sqlstate and sqlstate != "23505":
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "Employee creation failed because of a database integrity error",
            ) from None
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Employee email or employee code already exists"
        ) from None
    except BaseException:
        db.rollback()
        raise


def _get_employee(
    db: Session, user_id: UUID, lock: bool = False
) -> EmployeeEmploymentDetails:
    query = (
        select(EmployeeEmploymentDetails)
        .options(
            joinedload(EmployeeEmploymentDetails.user),
            joinedload(EmployeeEmploymentDetails.department),
            joinedload(EmployeeEmploymentDetails.entity),
            joinedload(EmployeeEmploymentDetails.invitation),
            selectinload(EmployeeEmploymentDetails.documents),
            joinedload(EmployeeEmploymentDetails.personal_details),
            joinedload(EmployeeEmploymentDetails.contact_details),
            joinedload(EmployeeEmploymentDetails.bank_details),
            joinedload(EmployeeEmploymentDetails.skills_and_interests),
        )
        .where(
            or_(
                EmployeeEmploymentDetails.user_id == user_id,
                EmployeeEmploymentDetails.id == user_id,
            ),
            EmployeeEmploymentDetails.deleted_at.is_(None),
        )
    )
    if lock:
        query = query.with_for_update(of=EmployeeEmploymentDetails)
    employee = db.scalar(query)
    if employee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
    return employee


def send_invitation(db: Session, actor: User, user_id: UUID) -> dict:
    try:
        employee = _get_employee(db, user_id, lock=True)
        if employee.profile_status not in {"PENDING", "REJECTED"}:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Invitation can only be sent while the profile is pending or rejected",
            )
        invitation = employee.invitation
        raw_token = new_opaque_token()
        now = datetime.now(UTC)
        expiry = now + timedelta(
            hours=get_settings().onboarding_invitation_expire_hours
        )
        token_hash = hash_token(raw_token)
        recipient = (
            employee.personal_email
            or employee.company_email
            or (employee.user.email if employee.user else None)
        )
        if not recipient:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Candidate email address is required to send invitation",
            )
        if invitation is None:
            invitation = OnboardingInvitation(
                employee_id=employee.id,
                recipient_email=recipient,
                invitation_token_hash=token_hash,
                current_step=1,
                invitation_status="SENT",
                sent_at=now,
                expires_at=expiry,
            )
            db.add(invitation)
            employee.invitation = invitation
        else:
            if invitation.invitation_status == "ACCEPTED":
                raise HTTPException(
                    status.HTTP_409_CONFLICT, "Invitation was already accepted"
                )
            invitation.sent_at = now
            invitation.expires_at = expiry
            invitation.submitted_at = None
            invitation.invitation_token_hash = token_hash
            invitation.invitation_status = "SENT"
            invitation.recipient_email = recipient

        # If previously rejected, restore to PENDING profile state and re-enable user account
        if employee.profile_status == "REJECTED" or employee.onboarding_status == "REJECTED":
            employee.profile_status = "PENDING"
            employee.onboarding_status = "INVITED"
            employee.rejection_reason = None
            if employee.user:
                employee.user.account_status = "INVITED"
                employee.user.is_active = True

        invitation_url = f"{get_settings().frontend_onboarding_url}?token={raw_token}"
        dispatch_row = email_dispatch.enqueue(
            db,
            entity_type="INVITATION",
            entity_id=user_id,
            recipient=recipient,
            template_key="EMPLOYEE_INVITATION",
            variables={
                "employee_name": f"{employee.first_name} {employee.last_name}".strip(),
                "invitation_link": invitation_url,
                "expiry_hours": get_settings().onboarding_invitation_expire_hours,
            },
        )
        db.commit()
        delivered = email_dispatch.dispatch(dispatch_row.id)
        return {
            "invitation_status": "SENT",
            "email_dispatch_status": "DISPATCHED" if delivered else "FAILED",
            "expires_at": expiry,
        }
    except BaseException:
        db.rollback()
        raise


def retry_invitation(db: Session, actor: User, user_id: UUID) -> dict:
    employee = _get_employee(db, user_id)
    invitation = employee.invitation
    if (
        invitation is None
        or invitation.invitation_status != "SENT"
        or invitation.expires_at <= datetime.now(UTC)
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Only an active invitation can be retried"
        )
    dispatch_row = db.scalar(
        select(EmailDispatchOutbox)
        .where(
            EmailDispatchOutbox.entity_type == "INVITATION",
            EmailDispatchOutbox.entity_id == user_id,
            EmailDispatchOutbox.status != "DISPATCHED",
        )
        .order_by(EmailDispatchOutbox.created_at.desc())
    )
    if dispatch_row is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "A failed invitation dispatch was not found"
        )
    delivered = email_dispatch.retry(
        dispatch_row.id, entity_type="INVITATION", entity_id=user_id
    )
    return {
        "invitation_status": "SENT",
        "email_dispatch_status": "DISPATCHED" if delivered else "FAILED",
        "expires_at": invitation.expires_at,
    }


def validate_invitation(db: Session, raw_token: str) -> dict:
    invitation = db.scalar(
        select(OnboardingInvitation)
        .options(joinedload(OnboardingInvitation.employee))
        .where(OnboardingInvitation.invitation_token_hash == hash_token(raw_token))
    )
    now = datetime.now(UTC)
    if (
        invitation is not None
        and invitation.invitation_status == "SENT"
        and invitation.expires_at <= now
    ):
        invitation.invitation_status = "EXPIRED"
        db.commit()
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Invalid or expired invitation"
        )
    if (
        invitation is None
        or invitation.invitation_status not in {"SENT", "ACCEPTED"}
        or invitation.employee.profile_status not in {"PENDING", "REJECTED"}
        or invitation.expires_at <= now
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Invalid or expired invitation"
        )
    employee = invitation.employee
    if employee.onboarding_status in {"INVITED", "REJECTED"}:
        employee.onboarding_status = "ONBOARDING"
        db.commit()
    return {
        "first_name": employee.first_name,
        "last_name": employee.last_name,
        "employee_code": employee.employee_code,
        "company_name": employee.entity_name or "Evolvus360",
        "entity": employee.entity_name or "ETPL",
        "company_email": employee.company_email or f"{employee.first_name.lower()}@evolvus.com",
        "department": employee.department_name or "Chemistry",
        "pf_applicable": "YES" if employee.pf_applicable else "NO",
        "role": employee.designation or "Employee",
        "expires_at": invitation.expires_at,
    }


def _invitation_for_active_form(db: Session, raw_token: str) -> OnboardingInvitation:
    invitation = db.scalar(
        select(OnboardingInvitation)
        .options(
            joinedload(OnboardingInvitation.employee).joinedload(
                EmployeeEmploymentDetails.personal_details
            ),
            joinedload(OnboardingInvitation.employee).joinedload(
                EmployeeEmploymentDetails.contact_details
            ),
            joinedload(OnboardingInvitation.employee).joinedload(
                EmployeeEmploymentDetails.bank_details
            ),
            joinedload(OnboardingInvitation.employee).joinedload(
                EmployeeEmploymentDetails.skills_and_interests
            ),
            joinedload(OnboardingInvitation.employee).selectinload(
                EmployeeEmploymentDetails.documents
            ),
        )
        .where(OnboardingInvitation.invitation_token_hash == hash_token(raw_token))
    )
    now = datetime.now(UTC)
    if (
        invitation is None
        or invitation.invitation_status not in {"SENT", "ACCEPTED"}
        or invitation.expires_at <= now
        or invitation.employee.profile_status not in {"PENDING", "REJECTED"}
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired invitation")
    return invitation


def get_onboarding_invitation(db: Session, raw_token: str) -> dict:
    """Validate an invitation and return its candidate and saved draft data."""
    invitation = _invitation_for_active_form(db, raw_token)
    employee = invitation.employee
    if employee.onboarding_status in {"INVITED", "REJECTED"}:
        employee.onboarding_status = "ONBOARDING"
    return {
        "first_name": employee.first_name,
        "last_name": employee.last_name,
        "employee_code": employee.employee_code,
        "company_name": employee.entity_name or "Evolvus360",
        "entity": employee.entity_name or "ETPL",
        "company_email": employee.company_email or f"{employee.first_name.lower()}@evolvus.com",
        "department": employee.department_name or "Chemistry",
        "pf_applicable": "YES" if employee.pf_applicable else "NO",
        "role": employee.designation or "Employee",
        "expires_at": invitation.expires_at,
        "draft": _onboarding_draft_for_form(db, invitation),
        "documents": [
            {
                "document_type": document.document_type,
                "original_filename": document.original_filename,
            }
            for document in employee.documents
        ],
    }


def _onboarding_draft_for_form(
    db: Session, invitation: OnboardingInvitation
) -> dict:
    draft = invitation.draft_form_data or {}
    encryptor = _encryptor()

    def draft_value(name: str, fallback: object = None) -> object:
        encrypted_value = draft.get(name)
        if encrypted_value is None:
            return fallback
        return _decrypt(encryptor, encrypted_value)

    employee = invitation.employee
    personal, contact, bank = (
        employee.personal_details,
        employee.contact_details,
        employee.bank_details,
    )
    return {
        "date_of_birth": draft_value("date_of_birth", personal.birth_date.isoformat() if personal else None),
        "gender": draft_value("gender", personal.gender if personal else None),
        "mobile_number": draft_value("mobile_number", contact.mobile_number if contact else None),
        "aadhaar_number": draft_value("aadhaar_number"),
        "pan_number": draft_value("pan_number"),
        "passport_number": draft_value("passport_number"),
        "emergency_contact_name": draft_value("emergency_contact_name", contact.emergency_contact_name if contact else None),
        "emergency_contact_phone": draft_value("emergency_contact_phone", contact.emergency_contact_phone if contact else None),
        "emergency_contact_relationship": draft_value("emergency_contact_relationship", contact.emergency_contact_relation if contact else None),
        "bank_name": draft_value("bank_name", bank.bank_name if bank else None),
        "account_number": draft_value("account_number"),
        "ifsc_code": draft_value("ifsc_code", bank.ifsc_code if bank else None),
        "uan_number": draft_value("uan_number"),
        "qualification": draft_value("qualification", employee.skills_and_interests.additional_qualifications if employee.skills_and_interests else None),
        "languages": draft_value("languages", employee.skills_and_interests.languages_spoken if employee.skills_and_interests else None),
    }


def save_onboarding_draft(
    db: Session,
    raw_token: str,
    fields: dict,
    files: dict[str, tuple[str, str | None, bytes]],
) -> dict:
    """Encrypt and persist a partial invitation form without submitting it."""
    stored_paths: list[Path] = []
    replaced_paths: list[Path] = []
    try:
        invitation = _invitation_for_active_form(db, raw_token)
        invitation = db.scalar(
            select(OnboardingInvitation)
            .where(OnboardingInvitation.id == invitation.id)
            .with_for_update(of=OnboardingInvitation)
        )
        employee = invitation.employee
        encryptor = _encryptor()
        draft = dict(invitation.draft_form_data or {})
        for name, value in fields.items():
            if value is None:
                continue
            if name in {"aadhaar_number", "pan_number", "account_number", "uan_number"} and not value.strip():
                continue
            if name == "date_of_birth":
                normalized = value.strip()
                if normalized:
                    try:
                        normalized = date.fromisoformat(normalized).isoformat()
                    except ValueError:
                        raise _field_validation_error("date_of_birth", "Enter a valid date in YYYY-MM-DD format.") from None
            elif name == "languages":
                try:
                    parsed = json.loads(value or "[]")
                except (TypeError, ValueError):
                    raise _field_validation_error("languages", "Languages must be a JSON array.") from None
                if not isinstance(parsed, list) or any(not isinstance(item, str) for item in parsed):
                    raise _field_validation_error("languages", "Languages must be a JSON array of strings.")
                normalized = json.dumps(parsed, ensure_ascii=False)
            else:
                normalized = str(value).strip()
            if name in {"gender", "pan_number", "ifsc_code", "uan_number"}:
                normalized = normalized.upper()
            draft[name] = encryptor.encrypt(normalized.encode()).decode()

        for document_type, (filename, content_type, contents) in files.items():
            if not contents:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    f"{document_type.replace('_', ' ').capitalize()} file is empty",
                )
            document = next((item for item in employee.documents if item.document_type == document_type), None)
            if document:
                replaced_paths.append(Path(document.storage_path))
                db.delete(document)
        if replaced_paths:
            db.flush()

        for document_type, (filename, content_type, contents) in files.items():
            path, clean_name, mime = _store_document(document_type, filename, content_type, contents)
            stored_paths.append(Path(path))
            employee.documents.append(EmployeeDocuments(
                document_type=document_type,
                original_filename=clean_name,
                storage_path=path,
                file_size_bytes=len(contents),
                mime_type=mime,
                uploaded_by_user_id=employee.user_id,
            ))

        invitation.draft_form_data = draft
        flag_modified(invitation, "draft_form_data")
        if employee.onboarding_status in {"INVITED", "REJECTED"}:
            employee.onboarding_status = "ONBOARDING"
        db.commit()
        for path in replaced_paths:
            path.unlink(missing_ok=True)
        return {
            "saved": True,
            "saved_at": datetime.now(UTC),
            "documents": [
                {
                    "document_type": document.document_type,
                    "original_filename": document.original_filename,
                }
                for document in employee.documents
            ],
        }
    except BaseException:
        db.rollback()
        for path in stored_paths:
            path.unlink(missing_ok=True)
        raise


def documents_for_invitation(db: Session, raw_token: str) -> list[dict[str, str]]:
    invitation = _invitation_for_active_form(db, raw_token)
    return [
        {
            "document_type": document.document_type,
            "original_filename": document.original_filename,
        }
        for document in invitation.employee.documents
    ]


def _encryptor() -> Fernet:
    value = get_settings().pii_encryption_key
    if value is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "PII_ENCRYPTION_KEY is not configured",
        )
    try:
        return Fernet(value.get_secret_value().encode("ascii"))
    except (ValueError, UnicodeEncodeError):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "PII_ENCRYPTION_KEY is invalid",
        ) from None


def _store_document(
    document_type: str, filename: str, content_type: str | None, contents: bytes
) -> tuple[str, str, str]:
    signatures = {
        "application/pdf": (b"%PDF-",),
        "image/jpeg": (b"\xff\xd8\xff",),
        "image/png": (b"\x89PNG\r\n\x1a\n",),
    }
    suffix_by_type = {
        "application/pdf": ".pdf",
        "image/jpeg": ".jpg",
        "image/png": ".png",
    }
    detected = next(
        (
            media_type
            for media_type, prefixes in signatures.items()
            if any(contents.startswith(prefix) for prefix in prefixes)
        ),
        None,
    )
    if detected is None or (
        content_type and content_type not in {detected, "application/octet-stream"}
    ):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Invalid {document_type} file type"
        )
    settings = get_settings()
    if len(contents) == 0 or len(contents) > settings.max_onboarding_file_size_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "Document exceeds the configured size limit",
        )
    upload_root = Path(settings.private_upload_dir).resolve()
    upload_root.mkdir(parents=True, exist_ok=True)
    storage_name = f"{uuid.uuid4().hex}{suffix_by_type[detected]}"
    storage_path = upload_root / storage_name
    with storage_path.open("xb") as uploaded:
        uploaded.write(contents)
    clean_name = Path(filename.replace("\\", "/")).name[:255] or storage_name
    return str(storage_path), clean_name, detected


def _mask(value: str | None, visible: int = 4) -> str | None:
    if not value:
        return None
    return "*" * max(0, len(value) - visible) + value[-visible:]


def _submission_snapshot(employee: EmployeeEmploymentDetails) -> str:
    """Encrypt the previous rejected submission before a correction replaces it."""
    snapshot = {
        "personal": {
            key: getattr(employee.personal_details, key)
            for key in (
                "aadhaar_number_encrypted",
                "aadhaar_number_last_four",
                "pan_number_encrypted",
                "passport_number_encrypted",
                "birth_date",
                "gender",
                "blood_group",
                "mother_tongue",
                "marital_status",
                "uan_number_encrypted",
            )
        }
        if employee.personal_details
        else None,
        "contact": {
            key: getattr(employee.contact_details, key)
            for key in (
                "mobile_number",
                "landline_number",
                "alternate_phone_number",
                "emergency_contact_name",
                "emergency_contact_phone",
                "emergency_contact_relation",
            )
        }
        if employee.contact_details
        else None,
        "bank": {
            key: getattr(employee.bank_details, key)
            for key in (
                "bank_name",
                "bank_account_number_encrypted",
                "bank_account_number_last_four",
                "ifsc_code",
                "account_holder_name",
            )
        }
        if employee.bank_details
        else None,
        "skills": {
            key: getattr(employee.skills_and_interests, key)
            for key in (
                "additional_qualifications",
                "additional_skills",
                "hobbies",
                "languages_spoken",
                "languages_read_and_written",
            )
        }
        if employee.skills_and_interests
        else None,
        "documents": [
            {
                "id": str(doc.id),
                "document_type": doc.document_type,
                "original_filename": doc.original_filename,
                "storage_path": doc.storage_path,
                "mime_type": doc.mime_type,
                "file_size_bytes": doc.file_size_bytes,
            }
            for doc in employee.documents
        ],
    }
    raw = json.dumps(snapshot, default=str, ensure_ascii=False).encode()
    return _encryptor().encrypt(raw).decode()


def get_employee_onboarding_form(db: Session, user: User) -> dict:
    employee = _get_employee(db, user.id)
    personal = employee.personal_details
    contact = employee.contact_details
    bank = employee.bank_details
    skills = employee.skills_and_interests
    return {
        "employee": {
            "id": str(employee.id),
            "employee_code": employee.employee_code,
            "first_name": employee.first_name,
            "middle_name": employee.middle_name,
            "last_name": employee.last_name,
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
        "education_and_skills": None
        if skills is None
        else {
            "additional_qualifications": skills.additional_qualifications,
            "additional_skills": skills.additional_skills,
            "languages_spoken": skills.languages_spoken,
            "languages_read_and_written": skills.languages_read_and_written,
        },
        "documents": [
            {
                "document_type": doc.document_type,
                "original_filename": doc.original_filename,
                "verification_status": doc.verification_status,
            }
            for doc in employee.documents
        ],
        "required_documents": ["identity_proof", "cancelled_cheque"],
        "onboarding_status": employee.onboarding_status,
        "profile_status": employee.profile_status,
        "submitted_at": employee.invitation.submitted_at
        if employee.invitation
        else None,
    }


def submit_employee_onboarding(
    db: Session,
    user: User,
    fields: dict,
    files: dict[str, tuple[str, str | None, bytes]],
) -> dict:
    """Persist an authenticated employee's full profile against existing tables."""
    stored_paths: list[Path] = []
    replaced_paths: list[Path] = []
    try:
        employee = _get_employee(db, user.id, lock=True)
        if employee.profile_status == "APPROVED":
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Approved profiles cannot be changed"
            )
        account, uan = _validate_onboarding_contact_and_compliance(
            fields, employee.pf_applicable
        )
        was_rejected = employee.profile_status == "REJECTED"
        previous_snapshot = _submission_snapshot(employee) if was_rejected else None
        encryptor = _encryptor()
        try:
            aadhaar = validate_aadhaar(fields.get("aadhaar_number", ""))
        except ValueError as error:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                {"message": "Validation failed. Please correct the highlighted fields.", "errors": {"aadhaar_number": str(error)}},
            ) from None
        try:
            pan = validate_pan(fields.get("pan_number", ""))
        except ValueError as error:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                {"message": "Validation failed. Please correct the highlighted fields.", "errors": {"pan_number": str(error)}},
            ) from None
        gender = fields.get("gender", "").upper()
        if gender not in {"MALE", "FEMALE", "OTHER", "PREFER_NOT_TO_SAY"}:
            raise _field_validation_error("gender", "Please select a valid gender.")
        if fields["date_of_birth"] >= date.today():
            raise _field_validation_error(
                "date_of_birth", "Date of birth must be in the past."
            )
        try:
            validate_mobile(fields.get("mobile_number", ""))
        except ValueError as error:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                {"message": "Validation failed. Please correct the highlighted fields.", "errors": {"mobile_number": str(error)}},
            ) from None
        if not re.fullmatch(
            r"[A-Z]{4}0[A-Z0-9]{6}", fields.get("ifsc_code", "").strip().upper()
        ):
            raise _field_validation_error("ifsc_code", "Enter a valid IFSC code.")
        for field_name in (
            "emergency_contact_name",
            "emergency_contact_phone",
            "emergency_contact_relationship",
            "bank_name",
        ):
            if not fields[field_name].strip():
                label = field_name.replace("_", " ").capitalize()
                raise _field_validation_error(field_name, f"{label} is required.")
        account = re.sub(r"\s", "", fields.get("account_number", ""))
        if not re.fullmatch(r"[A-Za-z0-9]{6,35}", account):
            raise _field_validation_error(
                "account_number", "Account number must contain 6 to 35 letters or digits."
            )
        required = {"identity_proof", "cancelled_cheque"}
        if not required.issubset(files):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                {
                    "message": "Validation failed. Please correct the highlighted fields.",
                    "errors": {
                        kind: f"{kind.replace('_', ' ').capitalize()} is required."
                        for kind in required.difference(files)
                    },
                },
            )
        new_docs = []
        for kind, (filename, content_type, contents) in files.items():
            for old_doc in employee.documents:
                if old_doc.document_type == kind:
                    replaced_paths.append(Path(old_doc.storage_path))
                    db.delete(old_doc)
            path, clean, mime = _store_document(kind, filename, content_type, contents)
            stored_paths.append(Path(path))
            new_docs.append(
                EmployeeDocuments(
                    document_type=kind,
                    original_filename=clean,
                    storage_path=path,
                    file_size_bytes=len(contents),
                    mime_type=mime,
                    uploaded_by_user_id=user.id,
                )
            )
        p = employee.personal_details or EmployeePersonalDetails(
            employee_id=employee.id
        )
        p.birth_date = fields["date_of_birth"]
        p.gender = gender
        p.aadhaar_number_encrypted = encryptor.encrypt(aadhaar.encode()).decode()
        p.aadhaar_number_last_four = aadhaar[-4:]
        p.pan_number_encrypted = encryptor.encrypt(pan.encode()).decode()
        passport = (fields.get("passport_number") or "").strip()
        p.passport_number_encrypted = (
            encryptor.encrypt(passport.encode()).decode() if passport else None
        )
        p.uan_number_encrypted = (
            encryptor.encrypt(uan.encode()).decode() if uan else None
        )
        employee.personal_details = p
        c = employee.contact_details or EmployeeContactDetails(employee_id=employee.id)
        c.mobile_number = fields["mobile_number"].strip()
        c.emergency_contact_name = fields["emergency_contact_name"].strip()
        c.emergency_contact_phone = fields["emergency_contact_phone"].strip()
        c.emergency_contact_relation = fields["emergency_contact_relationship"].strip()
        employee.contact_details = c
        b = employee.bank_details or EmployeeBankDetails(employee_id=employee.id)
        b.bank_name = fields["bank_name"].strip()
        b.bank_account_number_encrypted = encryptor.encrypt(account.encode()).decode()
        b.bank_account_number_last_four = account[-4:]
        b.ifsc_code = fields["ifsc_code"].strip().upper()
        b.account_holder_name = f"{employee.first_name} {employee.last_name}".strip()
        employee.bank_details = b
        sk = employee.skills_and_interests or EmployeeSkillsAndInterests(
            employee_id=employee.id
        )
        sk.additional_qualifications = fields.get("qualification") or None
        sk.additional_skills = fields.get("skills") or None
        sk.languages_spoken = fields.get("languages") or None
        employee.skills_and_interests = sk
        employee.documents.extend(new_docs)
        if previous_snapshot is not None:
            db.add(
                EmployeeApprovalDecision(
                    employee_id=employee.id,
                    action="RESUBMITTED",
                    actor_user_id=user.id,
                    reason="Previous rejected submission preserved",
                    snapshot_encrypted=previous_snapshot,
                )
            )
        now = datetime.now(UTC)
        employee.profile_status = "PENDING_APPROVAL"
        employee.onboarding_status = "PENDING_APPROVAL"
        employee.user.account_status = "PENDING_APPROVAL"
        employee.rejection_reason = None
        if employee.invitation:
            employee.invitation.submitted_at = now
            employee.invitation.invitation_status = "ACCEPTED"
            employee.invitation.expires_at = now
        db.commit()
        if not was_rejected:
            for path in replaced_paths:
                path.unlink(missing_ok=True)
        return {
            "employee_id": str(employee.id),
            "onboarding_status": employee.onboarding_status,
            "profile_status": employee.profile_status,
            "submitted_at": now,
        }
    except BaseException:
        db.rollback()
        for path in stored_paths:
            path.unlink(missing_ok=True)
        raise


def submit_onboarding(
    db: Session,
    raw_token: str,
    fields: dict,
    files: dict[str, tuple[str, str | None, bytes]],
) -> dict:
    stored_paths: list[Path] = []
    replaced_paths: list[Path] = []
    try:
        invitation = db.scalar(
            select(OnboardingInvitation)
            .options(
                joinedload(OnboardingInvitation.employee).joinedload(
                    EmployeeEmploymentDetails.user
                ),
                joinedload(OnboardingInvitation.employee).joinedload(
                    EmployeeEmploymentDetails.personal_details
                ),
                joinedload(OnboardingInvitation.employee).joinedload(
                    EmployeeEmploymentDetails.contact_details
                ),
                joinedload(OnboardingInvitation.employee).joinedload(
                    EmployeeEmploymentDetails.bank_details
                ),
                joinedload(OnboardingInvitation.employee).joinedload(
                    EmployeeEmploymentDetails.skills_and_interests
                ),
                joinedload(OnboardingInvitation.employee).selectinload(
                    EmployeeEmploymentDetails.documents
                ),
            )
            .where(OnboardingInvitation.invitation_token_hash == hash_token(raw_token))
            .with_for_update(of=OnboardingInvitation)
        )
        now = datetime.now(UTC)
        if (
            invitation is None
            or invitation.invitation_status not in {"SENT", "ACCEPTED"}
            or invitation.expires_at <= now
        ):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Invalid or expired invitation"
            )
        employee = invitation.employee
        if employee.profile_status not in {"PENDING", "REJECTED"}:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Employee profile was already submitted"
            )
        was_rejected = employee.profile_status == "REJECTED"
        previous_snapshot = _submission_snapshot(employee) if was_rejected else None
        saved_draft = _onboarding_draft_for_form(db, invitation)
        fields = {
            key: value if value not in (None, "") else saved_draft.get(key)
            for key, value in fields.items()
        }
        if isinstance(fields.get("date_of_birth"), str):
            try:
                fields["date_of_birth"] = date.fromisoformat(fields["date_of_birth"])
            except ValueError:
                raise _field_validation_error(
                    "date_of_birth", "Enter a valid date in YYYY-MM-DD format."
                ) from None
        account_number, uan = _validate_onboarding_contact_and_compliance(
            fields, employee.pf_applicable
        )
        if uan:
            try:
                validate_uan(uan)
            except ValueError as error:
                raise _field_validation_error("uan_number", str(error)) from None
        encryptor = _encryptor()
        try:
            aadhaar = validate_aadhaar(fields["aadhaar_number"])
        except ValueError as error:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                {"message": "Validation failed. Please correct the highlighted fields.", "errors": {"aadhaar_number": str(error)}},
            ) from None
        try:
            pan = validate_pan(fields["pan_number"])
        except ValueError as error:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                {"message": "Validation failed. Please correct the highlighted fields.", "errors": {"pan_number": str(error)}},
            ) from None
        if not re.fullmatch(
            r"[A-Z]{4}0[A-Z0-9]{6}", fields["ifsc_code"].strip().upper()
        ):
            raise _field_validation_error("ifsc_code", "Enter a valid IFSC code.")
        account_number = re.sub(r"\s", "", fields["account_number"])
        if fields["date_of_birth"] >= date.today():
            raise _field_validation_error(
                "date_of_birth", "Date of birth must be in the past."
            )
        mobile_number = fields["mobile_number"]
        try:
            validate_mobile(mobile_number)
        except ValueError as error:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                {"message": "Validation failed. Please correct the highlighted fields.", "errors": {"mobile_number": str(error)}},
            ) from None
        if (
            not fields["emergency_contact_name"].strip()
            or not fields["emergency_contact_phone"].strip()
            or not fields["emergency_contact_relationship"].strip()
        ):
            for field_name in (
                "emergency_contact_name",
                "emergency_contact_phone",
                "emergency_contact_relationship",
            ):
                if not fields[field_name].strip():
                    label = field_name.replace("_", " ").capitalize()
                    raise _field_validation_error(field_name, f"{label} is required.")
        if not fields["bank_name"].strip():
            raise _field_validation_error("bank_name", "Bank name is required.")
        try:
            languages = json.loads(fields["languages"] or "[]")
        except (TypeError, ValueError):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "Languages must be a JSON array"
            ) from None
        if not isinstance(languages, list) or any(
            not isinstance(item, str) for item in languages
        ):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Languages must be a JSON array of strings",
            )
        existing_document_types = {
            document.document_type for document in employee.documents
        }
        available_document_types = existing_document_types | set(files)
        if not {"identity_proof", "cancelled_cheque"}.issubset(
            available_document_types
        ):
            missing = {"identity_proof", "cancelled_cheque"}.difference(
                available_document_types
            )
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                {
                    "message": "Validation failed. Please correct the highlighted fields.",
                    "errors": {
                        kind: f"{kind.replace('_', ' ').capitalize()} is required."
                        for kind in missing
                    },
                },
            )
        for document in employee.documents:
            if document.document_type in {"identity_proof", "cancelled_cheque"}:
                if not Path(document.storage_path).is_file():
                    raise _field_validation_error(
                        document.document_type,
                        f"Please upload the {document.document_type.replace('_', ' ')} document again.",
                    )
        for document_type, (_, _, contents) in files.items():
            if not contents:
                raise _field_validation_error(
                    document_type,
                    f"Please upload a valid {document_type.replace('_', ' ')} document.",
                )

        stored: list[tuple[str, str, str, int, str]] = []
        for document_type, (filename, content_type, contents) in files.items():
            for previous in employee.documents:
                if previous.document_type == document_type:
                    replaced_paths.append(Path(previous.storage_path))
                    db.delete(previous)
            path, clean_name, media_type = _store_document(
                document_type, filename, content_type, contents
            )
            stored_paths.append(Path(path))
            stored.append((document_type, path, clean_name, len(contents), media_type))

        gender = fields["gender"].upper()
        if gender not in {"MALE", "FEMALE", "OTHER", "PREFER_NOT_TO_SAY"}:
            raise _field_validation_error("gender", "Please select a valid gender.")
        passport_number = (fields.get("passport_number") or "").strip()
        personal = employee.personal_details or EmployeePersonalDetails(employee_id=employee.id)
        personal.birth_date = fields["date_of_birth"]
        personal.gender = gender
        personal.aadhaar_number_encrypted = encryptor.encrypt(aadhaar.encode()).decode()
        personal.aadhaar_number_last_four = aadhaar[-4:]
        personal.pan_number_encrypted = encryptor.encrypt(pan.encode()).decode()
        personal.passport_number_encrypted = (
            encryptor.encrypt(passport_number.encode()).decode() if passport_number else None
        )
        personal.uan_number_encrypted = encryptor.encrypt(uan.encode()).decode() if uan else None
        employee.personal_details = personal

        contact = employee.contact_details or EmployeeContactDetails(employee_id=employee.id)
        contact.mobile_number = mobile_number
        contact.emergency_contact_name = fields["emergency_contact_name"].strip()
        contact.emergency_contact_phone = fields["emergency_contact_phone"].strip()
        contact.emergency_contact_relation = fields["emergency_contact_relationship"].strip()
        employee.contact_details = contact

        bank = employee.bank_details or EmployeeBankDetails(employee_id=employee.id)
        bank.bank_name = fields["bank_name"].strip()
        bank.bank_account_number_encrypted = encryptor.encrypt(account_number.encode()).decode()
        bank.bank_account_number_last_four = account_number[-4:]
        bank.ifsc_code = fields["ifsc_code"].strip().upper()
        bank.account_holder_name = f"{employee.first_name} {employee.last_name}".strip()
        employee.bank_details = bank

        skills = employee.skills_and_interests or EmployeeSkillsAndInterests(employee_id=employee.id)
        skills.additional_qualifications = fields.get("qualification") or None
        skills.languages_spoken = json.dumps(languages, ensure_ascii=False)
        employee.skills_and_interests = skills
        for document_type, path, filename, size, media_type in stored:
            employee.documents.append(
                EmployeeDocuments(
                    document_type=document_type,
                    original_filename=filename,
                    storage_path=path,
                    file_size_bytes=size,
                    mime_type=media_type,
                )
            )
        # Submission consumes the invitation; retain documents in private storage.
        final_document_types = existing_document_types | set(files)
        if not {"identity_proof", "cancelled_cheque"}.issubset(final_document_types):
            missing = next(iter({"identity_proof", "cancelled_cheque"} - final_document_types))
            raise _field_validation_error(
                missing, f"Please upload the {missing.replace('_', ' ')} document."
            )
        if previous_snapshot is not None:
            db.add(
                EmployeeApprovalDecision(
                    employee_id=employee.id,
                    action="RESUBMITTED",
                    actor_user_id=employee.user_id,
                    reason="Previous rejected submission preserved",
                    snapshot_encrypted=previous_snapshot,
                )
            )
        employee.profile_status = "PENDING_APPROVAL"
        employee.onboarding_status = "PENDING_APPROVAL"
        invitation.invitation_status = "ACCEPTED"
        invitation.submitted_at = now
        invitation.expires_at = now
        # Invalidate the opaque invitation credential as well as its expiry.
        # This keeps a copied link unusable after a successful submission.
        invitation.invitation_token_hash = hash_token(new_opaque_token())
        invitation.draft_form_data = None
        employee.rejection_reason = None
        employee.user.phone_number = mobile_number
        employee.user.account_status = "PENDING_APPROVAL"
        employee.user.is_active = True
        db.commit()
        if not was_rejected:
            for path in replaced_paths:
                path.unlink(missing_ok=True)
        return {"profile_status": "PENDING_APPROVAL"}
    except BaseException:
        db.rollback()
        for path in stored_paths:
            path.unlink(missing_ok=True)
        raise


def _employee_list_item(employee: EmployeeEmploymentDetails) -> dict:
    user = employee.user
    role_name = None
    role_id = None
    if user:
        assignment = next(
            (
                item
                for item in user.role_assignments
                if item.role.is_active and not getattr(item.role, "is_deleted", False)
            ),
            None,
        )
        if assignment:
            role_name = assignment.role.role_name
            role_id = str(assignment.role.id)
    invitation = getattr(employee, "invitation", None)
    return {
        "id": str(user.id) if user else str(employee.id),
        "user_id": str(user.id) if user else None,
        "employee_id": str(employee.id),
        "first_name": employee.first_name,
        "middle_name": employee.middle_name,
        "last_name": employee.last_name,
        "employee_code": employee.employee_code,
        "company_email": employee.company_email,
        "personal_email": employee.personal_email,
        "department": (
            {"id": str(employee.department.id), "name": employee.department.name}
            if employee.department
            else None
        ),
        "role": {"id": role_id, "name": role_name} if role_id else None,
        "designation": employee.designation,
        "entity": (
            {
                "id": str(employee.entity.id),
                "name": employee.entity.name,
                "code": employee.entity.code,
            }
            if employee.entity
            else None
        ),
        "location": employee.work_location,
        "account_status": user.account_status if user else None,
        "profile_status": employee.profile_status,
        "pf_applicable": employee.pf_applicable,
        "joining_date": str(employee.joining_date) if employee.joining_date else None,
        "start_date": str(employee.employment_start_date) if employee.employment_start_date else None,
        "end_date": str(employee.employment_end_date) if employee.employment_end_date else None,
        "invitation_status": invitation.invitation_status if invitation else None,
    }


def list_employees(
    db: Session,
    _actor: User,
    *,
    search: str | None,
    role_id: UUID | None,
    department_id: UUID | None,
    entity_id: UUID | None,
    profile_status: str | None,
    account_status: str | None,
    page: int,
    page_size: int,
) -> dict:
    if profile_status and profile_status.upper() not in PROFILE_STATES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid profile status"
        )
    query = (
        select(EmployeeEmploymentDetails)
        .join(User, EmployeeEmploymentDetails.user_id == User.id)
        .options(
            joinedload(EmployeeEmploymentDetails.user)
            .selectinload(User.role_assignments)
            .joinedload(UserRole.role),
            joinedload(EmployeeEmploymentDetails.department),
            joinedload(EmployeeEmploymentDetails.entity),
            joinedload(EmployeeEmploymentDetails.invitation),
        )
        .where(EmployeeEmploymentDetails.deleted_at.is_(None))
    )
    conditions = []
    if role_id:
        conditions.append(
            select(UserRole.id)
            .where(UserRole.user_id == User.id, UserRole.role_id == role_id)
            .exists()
        )
    if department_id:
        conditions.append(EmployeeEmploymentDetails.department_id == department_id)
    if entity_id:
        conditions.append(EmployeeEmploymentDetails.entity_id == entity_id)
    if profile_status:
        conditions.append(
            EmployeeEmploymentDetails.profile_status == profile_status.upper()
        )
    if account_status:
        conditions.append(User.account_status == account_status.upper())
    if search:
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(
                EmployeeEmploymentDetails.first_name.ilike(pattern),
                EmployeeEmploymentDetails.middle_name.ilike(pattern),
                EmployeeEmploymentDetails.last_name.ilike(pattern),
                EmployeeEmploymentDetails.employee_code.ilike(pattern),
                EmployeeEmploymentDetails.company_email.ilike(pattern),
                EmployeeEmploymentDetails.personal_email.ilike(pattern),
                select(UserRole.id)
                .join(Role, UserRole.role_id == Role.id)
                .where(
                    UserRole.user_id == User.id,
                    or_(
                        Role.role_name.ilike(pattern),
                        Role.role_code.ilike(pattern),
                    ),
                )
                .exists(),
            )
        )
    if conditions:
        query = query.where(*conditions)
    total = (
        db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
        or 0
    )
    rows = (
        db.scalars(
            query.order_by(
                EmployeeEmploymentDetails.created_at.desc(),
                EmployeeEmploymentDetails.id,
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .unique()
        .all()
    )
    user_ids = [employee.user_id for employee in rows if employee.user_id]
    dispatch_status_by_user: dict[UUID, str] = {}
    if user_ids:
        dispatch_rows = db.execute(
            select(EmailDispatchOutbox.entity_id, EmailDispatchOutbox.status)
            .where(
                EmailDispatchOutbox.entity_type == "INVITATION",
                EmailDispatchOutbox.entity_id.in_(user_ids),
            )
            .order_by(EmailDispatchOutbox.created_at.desc())
        ).all()
        for user_id, dispatch_status in dispatch_rows:
            dispatch_status_by_user.setdefault(user_id, dispatch_status)
    return {
        "items": [
            {
                **_employee_list_item(employee),
                "email_dispatch_status": dispatch_status_by_user.get(
                    employee.user_id
                ),
            }
            for employee in rows
        ],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }


def _decrypt(encryptor: Fernet, value: str | None) -> str | None:
    if not value:
        return None
    try:
        return encryptor.decrypt(value.encode()).decode()
    except (InvalidToken, ValueError, UnicodeDecodeError):
        return value


def employee_details(db: Session, actor: User, user_id: UUID) -> dict:
    employee = _get_employee(db, user_id)
    user = employee.user
    assignment = (
        next(
            (
                item
                for item in user.role_assignments
                if item.role.is_active and not getattr(item.role, "is_deleted", False)
            ),
            None,
        )
        if user
        else None
    )
    hr_details = {
        "first_name": employee.first_name,
        "middle_name": employee.middle_name,
        "last_name": employee.last_name,
        "department": (
            {"id": str(employee.department.id), "name": employee.department.name}
            if employee.department
            else None
        ),
        "role": (
            {"id": str(assignment.role.id), "name": assignment.role.role_name}
            if assignment
            else None
        ),
        "designation": employee.designation,
        "entity": (
            {"id": str(employee.entity.id), "name": employee.entity.name}
            if employee.entity
            else None
        ),
        "employee_code": employee.employee_code,
        "reason_for_change": employee.last_change_reason,
        "location": employee.work_location,
        "company_email": employee.company_email,
        "personal_email": employee.personal_email,
        "pf_applicable": employee.pf_applicable,
        "joining_date": employee.joining_date,
        "start_date": employee.employment_start_date,
        "end_date": employee.employment_end_date,
    }
    submitted = employee.profile_status in {
        "SUBMITTED",
        "PENDING_APPROVAL",
        "APPROVED",
        "REJECTED",
    }
    details = None
    if submitted:
        if not (
            employee.personal_details
            and employee.contact_details
            and employee.bank_details
        ):
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Submitted employee details are incomplete"
            )
        encryptor = _encryptor()
        personal = employee.personal_details
        contact = employee.contact_details
        bank = employee.bank_details
        details = {
            "date_of_birth": personal.birth_date,
            "gender": personal.gender,
            "blood_group": personal.blood_group,
            "mother_tongue": personal.mother_tongue,
            "marital_status": personal.marital_status,
            "aadhaar_number": _decrypt(
                encryptor, personal.aadhaar_number_encrypted
            )
            or personal.aadhaar_number_last_four,
            "pan_number": _decrypt(encryptor, personal.pan_number_encrypted),
            "passport_number": _decrypt(
                encryptor, personal.passport_number_encrypted
            ),
            "uan_number": _decrypt(encryptor, personal.uan_number_encrypted),
            "mobile_number": contact.mobile_number,
            "landline_number": contact.landline_number,
            "alternate_phone_number": contact.alternate_phone_number,
            "emergency_contact": {
                "name": contact.emergency_contact_name,
                "phone": contact.emergency_contact_phone,
                "relationship": contact.emergency_contact_relation,
            },
            "bank_details": {
                "bank_name": bank.bank_name,
                "account_holder_name": bank.account_holder_name,
                "account_number": _decrypt(
                    encryptor, bank.bank_account_number_encrypted
                )
                or bank.bank_account_number_last_four,
                "ifsc_code": bank.ifsc_code,
            },
            "documents": [
                {
                    "id": str(doc.id),
                    "document_type": doc.document_type,
                    "file_name": doc.original_filename,
                    "file_size_bytes": doc.file_size_bytes,
                    "mime_type": doc.mime_type,
                    "verification_status": doc.verification_status,
                }
                for doc in employee.documents
            ],
            "qualification": (
                employee.skills_and_interests.additional_qualifications
                if employee.skills_and_interests
                else None
            ),
            "skills": (
                employee.skills_and_interests.additional_skills
                if employee.skills_and_interests
                else None
            ),
            "hobbies": (
                employee.skills_and_interests.hobbies
                if employee.skills_and_interests
                else None
            ),
            "languages_read_and_written": (
                employee.skills_and_interests.languages_read_and_written
                if employee.skills_and_interests
                else None
            ),
            "languages": (
                json.loads(employee.skills_and_interests.languages_spoken or "[]")
                if employee.skills_and_interests
                else []
            ),
        }
    return {
        "id": str(user.id) if user else str(employee.user_id),
        "profile_status": employee.profile_status,
        "account_status": user.account_status if user else None,
        "can_view_employee_details": submitted,
        "hr_details": hr_details,
        "employee_details": details,
    }


def update_employee(db: Session, actor: User, user_id: UUID, payload: object) -> dict:
    try:
        employee = _get_employee(db, user_id, lock=True)
        user = employee.user
        values = payload.model_dump(exclude_unset=True)
        required_fields = {
            "first_name",
            "last_name",
            "department_id",
            "role_id",
            "designation",
            "entity_id",
            "company_email",
            "personal_email",
            "pf_applicable",
            "joining_date",
            "start_date",
            "account_status",
        }
        if any(name in values and values[name] is None for name in required_fields):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Required employee fields cannot be null",
            )
        if "department_id" in values:
            department_id = values["department_id"]
            if department_id is None:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY, "Department is required"
                )
            department = db.scalar(
                select(Department).where(
                    Department.id == department_id,
                    Department.is_active.is_(True),
                )
            )
            if department is None:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "Department is not active",
                )
            employee.department_id = department.id
            employee.department_name = department.name
        if "entity_id" in values:
            entity_id = values["entity_id"]
            if entity_id is None:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY, "Entity is required"
                )
            entity = db.scalar(
                select(Entity).where(
                    Entity.id == entity_id,
                    Entity.is_active.is_(True),
                )
            )
            if entity is None:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "Entity is not active",
                )
            employee.entity_id = entity.id
            employee.entity_name = entity.name
        if "role_id" in values:
            role = db.scalar(
                select(Role).where(
                    Role.id == values["role_id"],
                    Role.is_active.is_(True),
                    Role.is_deleted.is_(False),
                )
            )
            if role is None:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY, "Role is not active"
                )
            db.query(UserRole).filter(UserRole.user_id == user_id).delete(
                synchronize_session=False
            )
            db.add(
                UserRole(user_id=user_id, role_id=role.id, assigned_by_user_id=actor.id)
            )
        field_map = {
            "first_name": "first_name",
            "middle_name": "middle_name",
            "last_name": "last_name",
            "designation": "designation",
            "location": "work_location",
            "pf_applicable": "pf_applicable",
            "joining_date": "joining_date",
            "start_date": "employment_start_date",
            "end_date": "employment_end_date",
        }
        for name, model_name in field_map.items():
            if name in values:
                value = values[name]
                setattr(
                    employee,
                    model_name,
                    value.strip() if isinstance(value, str) else value,
                )
        if "reason_for_change" in values:
            employee.last_change_reason = (
                values["reason_for_change"].strip()
                if values["reason_for_change"]
                else None
            )
        if "company_email" in values:
            email = (
                normalize_email(str(values["company_email"]))
                if values["company_email"]
                else None
            )
            if email is None and employee.onboarding_status == "APPROVED":
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "Company email cannot be removed after credentials are issued",
                )
            login_email = email or employee.personal_email
            duplicate = db.scalar(
                select(User.id).where(
                    func.lower(User.email) == login_email,
                    User.id != user_id,
                    User.deleted_at.is_(None),
                )
            )
            if duplicate:
                raise HTTPException(
                    status.HTTP_409_CONFLICT, "Company email already exists"
                )
            user.email = login_email
            employee.company_email = email
        if "personal_email" in values:
            email = normalize_email(str(values["personal_email"]))
            duplicate = db.scalar(
                select(EmployeeEmploymentDetails.id).where(
                    EmployeeEmploymentDetails.user_id != user_id,
                    func.lower(EmployeeEmploymentDetails.personal_email) == email,
                    EmployeeEmploymentDetails.deleted_at.is_(None),
                )
            )
            if duplicate:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "Personal email already exists",
                )
            employee.personal_email = email
            if not employee.company_email:
                duplicate_user = db.scalar(
                    select(User.id).where(
                        func.lower(User.email) == email,
                        User.id != user_id,
                        User.deleted_at.is_(None),
                    )
                )
                if duplicate_user:
                    raise HTTPException(
                        status.HTTP_409_CONFLICT, "Personal email already exists"
                    )
                user.email = email
        profile_fields = {
            "date_of_birth", "gender", "blood_group", "mother_tongue", "marital_status",
            "aadhaar_number", "pan_number",
            "passport_number", "uan_number", "mobile_number",
            "emergency_contact_name", "emergency_contact_phone",
            "emergency_contact_relationship", "bank_name", "account_holder_name",
            "account_number", "ifsc_code", "qualification", "skills", "languages",
        }
        if profile_fields.intersection(values):
            required_profile_values = {
                "date_of_birth", "gender", "mobile_number", "emergency_contact_name",
                "emergency_contact_phone", "emergency_contact_relationship",
                "bank_name", "ifsc_code",
            }
            if any(name in values and values[name] is None for name in required_profile_values):
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "Required employee profile fields cannot be null",
                )
            encryptor = _encryptor()
            personal = employee.personal_details
            personal_fields = {
            "date_of_birth", "gender", "blood_group", "mother_tongue", "marital_status",
            "aadhaar_number", "pan_number",
                "passport_number", "uan_number",
            }
            if personal_fields.intersection(values):
                if personal is None:
                    if not {"date_of_birth", "gender"}.issubset(values):
                        raise HTTPException(
                            status.HTTP_409_CONFLICT,
                            "Date of birth and gender are required to create personal details",
                        )
                    personal = EmployeePersonalDetails(employee_id=employee.id)
                    employee.personal_details = personal
                if "date_of_birth" in values:
                    if values["date_of_birth"] >= date.today():
                        raise _field_validation_error(
                            "date_of_birth", "Date of birth must be in the past."
                        )
                    personal.birth_date = values["date_of_birth"]
                if "gender" in values:
                    personal.gender = values["gender"]
                if "blood_group" in values:
                    personal.blood_group = values["blood_group"]
                if "mother_tongue" in values:
                    personal.mother_tongue = (values["mother_tongue"] or "").strip() or None
                if "marital_status" in values:
                    personal.marital_status = values["marital_status"]
                if (values.get("aadhaar_number") or "").strip():
                    try:
                        aadhaar = validate_aadhaar(values["aadhaar_number"])
                    except ValueError as error:
                        raise _field_validation_error("aadhaar_number", str(error)) from None
                    personal.aadhaar_number_encrypted = encryptor.encrypt(aadhaar.encode()).decode()
                    personal.aadhaar_number_last_four = aadhaar[-4:]
                if (values.get("pan_number") or "").strip():
                    try:
                        pan = validate_pan(values["pan_number"])
                    except ValueError as error:
                        raise _field_validation_error("pan_number", str(error)) from None
                    personal.pan_number_encrypted = encryptor.encrypt(pan.encode()).decode()
                if "passport_number" in values:
                    passport = (values["passport_number"] or "").strip().upper()
                    personal.passport_number_encrypted = (
                        encryptor.encrypt(passport.encode()).decode() if passport else None
                    )
                if "uan_number" in values:
                    uan = (values["uan_number"] or "").strip()
                    if uan:
                        try:
                            validate_uan(uan)
                        except ValueError as error:
                            raise _field_validation_error("uan_number", str(error)) from None
                    personal.uan_number_encrypted = (
                        encryptor.encrypt(uan.encode()).decode() if uan else None
                    )

            contact_fields = {
                "mobile_number", "landline_number", "alternate_phone_number",
                "emergency_contact_name", "emergency_contact_phone", "emergency_contact_relationship",
            }
            if contact_fields.intersection(values):
                contact = employee.contact_details
                if contact is None:
                    required_contact = {"mobile_number", "emergency_contact_name", "emergency_contact_phone", "emergency_contact_relationship"}
                    if not required_contact.issubset(values):
                        raise HTTPException(
                            status.HTTP_409_CONFLICT,
                            "All contact fields are required to create employee contact details",
                        )
                    contact = EmployeeContactDetails(employee_id=employee.id)
                    employee.contact_details = contact
                if "mobile_number" in values:
                    try:
                        contact.mobile_number = validate_mobile(values["mobile_number"])
                    except ValueError as error:
                        raise _field_validation_error("mobile_number", str(error)) from None
                    user.phone_number = contact.mobile_number
                for phone_field in ("landline_number", "alternate_phone_number"):
                    if phone_field in values:
                        phone = re.sub(r"[\s()-]", "", values[phone_field] or "")
                        if phone and not re.fullmatch(r"(?:\+[1-9][0-9]{7,14}|[0-9]{7,15})", phone):
                            raise _field_validation_error(phone_field, "Enter a valid phone number.")
                        setattr(contact, phone_field, phone or None)
                if "emergency_contact_name" in values:
                    name = (values["emergency_contact_name"] or "").strip()
                    if not name or not all(char.isalpha() or char in " '-." for char in name):
                        raise _field_validation_error("emergency_contact_name", "Enter a valid contact name.")
                    contact.emergency_contact_name = name
                if "emergency_contact_relationship" in values:
                    relation = (values["emergency_contact_relationship"] or "").strip()
                    if not relation or not all(char.isalpha() or char in " '-." for char in relation):
                        raise _field_validation_error("emergency_contact_relationship", "Enter a valid relationship.")
                    contact.emergency_contact_relation = relation
                if "emergency_contact_phone" in values:
                    phone = values["emergency_contact_phone"] or ""
                    try:
                        validate_mobile(phone)
                    except ValueError:
                        raise _field_validation_error(
                            "emergency_contact_phone", "Mobile number must be exactly 10 digits."
                        ) from None
                    contact.emergency_contact_phone = phone

            bank_fields = {"bank_name", "account_holder_name", "account_number", "ifsc_code"}
            if bank_fields.intersection(values):
                bank = employee.bank_details
                if bank is None:
                    required_bank = {"bank_name", "account_number", "ifsc_code"}
                    if not required_bank.issubset(values):
                        raise HTTPException(
                            status.HTTP_409_CONFLICT,
                            "Bank name, account number, and IFSC are required to create bank details",
                        )
                    bank = EmployeeBankDetails(employee_id=employee.id)
                    employee.bank_details = bank
                if "bank_name" in values:
                    bank_name = (values["bank_name"] or "").strip()
                    if not bank_name or not all(char.isalnum() or char in " &().,'-/" for char in bank_name):
                        raise _field_validation_error("bank_name", "Enter a valid bank name.")
                    bank.bank_name = bank_name
                if "account_holder_name" in values:
                    holder = (values["account_holder_name"] or "").strip()
                    if holder and not all(char.isalpha() or char in " '-." for char in holder):
                        raise _field_validation_error("account_holder_name", "Enter a valid account holder name.")
                    bank.account_holder_name = holder or None
                if (values.get("account_number") or "").strip():
                    account = re.sub(r"\s", "", values["account_number"])
                    if not re.fullmatch(r"[A-Za-z0-9]{6,35}", account):
                        raise _field_validation_error("account_number", "Account number must contain 6 to 35 letters or digits.")
                    bank.bank_account_number_encrypted = encryptor.encrypt(account.encode()).decode()
                    bank.bank_account_number_last_four = account[-4:]
                if "ifsc_code" in values:
                    ifsc = (values["ifsc_code"] or "").strip().upper()
                    if not re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", ifsc):
                        raise _field_validation_error("ifsc_code", "Enter a valid 11-character IFSC code.")
                    bank.ifsc_code = ifsc
                if {"bank_name", "account_holder_name", "account_number", "ifsc_code"}.intersection(values):
                    bank.is_verified = False
                    bank.verification_status = "PENDING"
            skill_fields = {"qualification", "skills", "hobbies", "languages", "languages_read_and_written"}
            if skill_fields.intersection(values):
                skills = employee.skills_and_interests
                if skills is None:
                    skills = EmployeeSkillsAndInterests(employee_id=employee.id)
                    employee.skills_and_interests = skills
                if "qualification" in values:
                    skills.additional_qualifications = values["qualification"] or None
                if "skills" in values:
                    skills.additional_skills = values["skills"] or None
                if "hobbies" in values:
                    skills.hobbies = values["hobbies"] or None
                if "languages" in values:
                    skills.languages_spoken = json.dumps(values["languages"], ensure_ascii=False)
                if "languages_read_and_written" in values:
                    skills.languages_read_and_written = values["languages_read_and_written"] or None
        if employee.employment_start_date < employee.joining_date:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Start date must be on or after joining date",
            )
        if "account_status" in values:
            next_status = values["account_status"]
            if next_status == "ACTIVE" and employee.profile_status != "APPROVED":
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "Employee profile must be approved before activating the account",
                )
            user.account_status = next_status
            user.is_active = next_status != "INACTIVE"
            if next_status != "ACTIVE":
                now = datetime.now(UTC)
                db.query(RefreshTokenSession).filter(
                    RefreshTokenSession.user_id == user.id,
                    RefreshTokenSession.revoked_at.is_(None),
                ).update(
                    {RefreshTokenSession.revoked_at: now},
                    synchronize_session=False,
                )
                db.query(PasswordResetToken).filter(
                    PasswordResetToken.user_id == user.id,
                    PasswordResetToken.used_at.is_(None),
                    PasswordResetToken.revoked_at.is_(None),
                ).update(
                    {PasswordResetToken.revoked_at: now},
                    synchronize_session=False,
                )
                if user.employee and user.employee.invitation:
                    invitation = user.employee.invitation
                    if invitation.invitation_status in {"PENDING", "SENT"}:
                        invitation.invitation_status = "REVOKED"
        if (
            employee.employment_end_date
            and employee.employment_end_date < employee.employment_start_date
        ):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "End date must be on or after start date",
            )
        result = employee_details(db, actor, user_id)
        db.commit()
        return result
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Employee update conflicts with existing data"
        ) from None
    except BaseException:
        db.rollback()
        raise


def replace_employee_documents(
    db: Session,
    actor: User,
    user_id: UUID,
    files: dict[str, tuple[str, str | None, bytes]],
) -> dict:
    """Replace selected onboarding documents without removing untouched files."""
    if not files:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Choose at least one document")
    stored_paths: list[Path] = []
    removed_paths: list[Path] = []
    try:
        employee = _get_employee(db, user_id, lock=True)
        for document_type, (filename, content_type, contents) in files.items():
            if document_type not in {"identity_proof", "cancelled_cheque"}:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid document type")
            path, clean_name, media_type = _store_document(
                document_type, filename, content_type, contents
            )
            stored_paths.append(Path(path))
            for previous in list(employee.documents):
                if previous.document_type == document_type:
                    removed_paths.append(Path(previous.storage_path))
                    db.delete(previous)
            employee.documents.append(
                EmployeeDocuments(
                    document_type=document_type,
                    original_filename=clean_name,
                    storage_path=path,
                    file_size_bytes=len(contents),
                    mime_type=media_type,
                    uploaded_by_user_id=actor.id,
                )
            )
        db.commit()
        for path in removed_paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        return {
            "documents": [
                {
                    "document_type": document.document_type,
                    "file_name": document.original_filename,
                    "file_size_bytes": document.file_size_bytes,
                    "verification_status": document.verification_status,
                }
                for document in employee.documents
            ]
        }
    except BaseException:
        db.rollback()
        for path in stored_paths:
            path.unlink(missing_ok=True)
        raise


def deactivate_user(db: Session, user_id: UUID) -> dict:
    """Disable an account and revoke every outstanding authentication credential."""
    user = db.scalar(
        select(User)
        .where(User.id == user_id, User.deleted_at.is_(None))
        .with_for_update()
    )
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    now = datetime.now(UTC)
    user.is_active = False
    user.account_status = "INACTIVE"
    db.query(RefreshTokenSession).filter(
        RefreshTokenSession.user_id == user.id,
        RefreshTokenSession.revoked_at.is_(None),
    ).update({RefreshTokenSession.revoked_at: now}, synchronize_session=False)
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.revoked_at.is_(None),
    ).update({PasswordResetToken.revoked_at: now}, synchronize_session=False)
    if user.employee and user.employee.invitation:
        invitation = user.employee.invitation
        if invitation.invitation_status in {"PENDING", "SENT"}:
            invitation.invitation_status = "REVOKED"
    db.commit()
    return {
        "id": str(user.id),
        "account_status": user.account_status,
        "is_active": user.is_active,
    }


def approve_employee(db: Session, actor: User, user_id: UUID) -> dict:
    from app.services.approval_service import approve

    return approve(db, actor, user_id)
