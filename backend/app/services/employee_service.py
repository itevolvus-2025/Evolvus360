"""Employee administration and invitation onboarding business operations."""

import json
import re
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.config import get_settings
from app.core.security import (
    hash_password,
    hash_token,
    new_opaque_token,
    normalize_email,
)
from app.models.company import Company
from app.models.hrms import (
    Department,
    EmailDispatchOutbox,
    EmployeeBankDetails,
    EmployeeContactDetails,
    EmployeeDocuments,
    EmployeeEmploymentDetails,
    EmployeePersonalDetails,
    EmployeeSkillsAndInterests,
    Entity,
    OnboardingInvitation,
    Role,
    User,
    UserRole,
)
from app.services import email_dispatch

ALLOWED_ROLES = {"HR", "SUPER_ADMIN"}
PROFILE_STATES = {"PENDING", "SUBMITTED", "APPROVED"}


def _role_codes(user: User) -> set[str]:
    return {
        item.role.role_code for item in user.role_assignments if item.role.is_active
    }


def _company_scope(user: User, requested_company_id: UUID | None = None) -> UUID | None:
    roles = _role_codes(user)
    if "SUPER_ADMIN" in roles:
        return requested_company_id
    if "HR" not in roles or user.company_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Company access is required")
    if requested_company_id and requested_company_id != user.company_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient company access")
    return user.company_id


def _active_company(db: Session, company_id: UUID) -> Company:
    company = db.scalar(
        select(Company).where(Company.id == company_id, Company.is_active.is_(True))
    )
    if company is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Company is not active"
        )
    return company


def list_departments(
    db: Session, user: User, company_id: UUID | None = None
) -> list[Department]:
    scope = _company_scope(user, company_id)
    query = select(Department).where(Department.is_active.is_(True))
    if scope:
        query = query.where(Department.company_id == scope)
    return list(db.scalars(query.order_by(Department.name)).all())


def list_entities(
    db: Session, user: User, company_id: UUID | None = None
) -> list[Entity]:
    scope = _company_scope(user, company_id)
    query = select(Entity).where(Entity.is_active.is_(True))
    if scope:
        query = query.where(Entity.company_id == scope)
    return list(db.scalars(query.order_by(Entity.name)).all())


def list_roles(db: Session) -> list[Role]:
    return list(
        db.scalars(
            select(Role).where(Role.is_active.is_(True)).order_by(Role.role_name)
        ).all()
    )


def _resolve_masters(
    db: Session,
    actor: User,
    company_id: UUID,
    department_id: UUID,
    entity_id: UUID,
    role_id: UUID,
) -> tuple[Department, Entity, Role]:
    department = db.scalar(
        select(Department).where(
            Department.id == department_id,
            Department.company_id == company_id,
            Department.is_active.is_(True),
        )
    )
    entity = db.scalar(
        select(Entity).where(
            Entity.id == entity_id,
            Entity.company_id == company_id,
            Entity.is_active.is_(True),
        )
    )
    role = db.scalar(select(Role).where(Role.id == role_id, Role.is_active.is_(True)))
    if department is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Department is not active in this company",
        )
    if entity is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Entity is not active in this company"
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
    sequence = db.scalar(
        update(Entity)
        .where(Entity.id == entity.id, Entity.is_active.is_(True))
        .values(next_employee_sequence=Entity.next_employee_sequence + 1)
        .returning(Entity.next_employee_sequence)
        .execution_options(synchronize_session=False)
    )
    if sequence is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Entity is no longer active")
    if sequence > 999:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Employee code sequence is exhausted for this entity",
        )
    return f"{prefix}-{sequence:03d}"


def create_employee(db: Session, actor: User, payload: object) -> dict:
    try:
        company_id = _company_scope(actor, getattr(payload, "company_id", None))
        if company_id is None:
            department_scope = db.scalar(
                select(Department.company_id).where(
                    Department.id == payload.department_id,
                    Department.is_active.is_(True),
                )
            )
            entity_scope = db.scalar(
                select(Entity.company_id).where(
                    Entity.id == payload.entity_id,
                    Entity.is_active.is_(True),
                )
            )
            if department_scope is None or department_scope != entity_scope:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "Department and entity must belong to the same active company",
                )
            company_id = department_scope
        _active_company(db, company_id)
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
            company_id,
            payload.department_id,
            payload.entity_id,
            payload.role_id,
        )
        company_email = normalize_email(str(payload.company_email))
        personal_email = normalize_email(str(payload.personal_email))
        if db.scalar(
            select(User.id).where(
                func.lower(User.email) == company_email,
                User.deleted_at.is_(None),
            )
        ):
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Company email already exists"
            )
        if db.scalar(
            select(EmployeeEmploymentDetails.id).where(
                EmployeeEmploymentDetails.company_id == company_id,
                func.lower(EmployeeEmploymentDetails.personal_email) == personal_email,
                EmployeeEmploymentDetails.deleted_at.is_(None),
            )
        ):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Personal email already exists in this company",
            )

        employee_code = _next_employee_code(db, entity)
        user = User(
            company_id=company_id,
            email=company_email,
            first_name=payload.first_name.strip(),
            last_name=payload.last_name.strip(),
            account_status="INVITED",
            is_active=True,
        )
        db.add(user)
        db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id, assigned_by_user_id=actor.id))
        employee = EmployeeEmploymentDetails(
            company_id=company_id,
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
        return {
            "id": str(user.id),
            "employee_code": employee_code,
            "profile_status": employee.profile_status,
        }
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Employee email or employee code already exists"
        ) from None
    except BaseException:
        db.rollback()
        raise


def _employee_for_actor(
    db: Session, actor: User, user_id: UUID, lock: bool = False
) -> EmployeeEmploymentDetails:
    scope = _company_scope(actor)
    query = (
        select(EmployeeEmploymentDetails)
        .options(
            joinedload(EmployeeEmploymentDetails.user),
            joinedload(EmployeeEmploymentDetails.department),
            joinedload(EmployeeEmploymentDetails.entity),
            joinedload(EmployeeEmploymentDetails.company),
            selectinload(EmployeeEmploymentDetails.documents),
            joinedload(EmployeeEmploymentDetails.personal_details),
            joinedload(EmployeeEmploymentDetails.contact_details),
            joinedload(EmployeeEmploymentDetails.bank_details),
            joinedload(EmployeeEmploymentDetails.skills_and_interests),
            joinedload(EmployeeEmploymentDetails.invitation),
        )
        .where(
            EmployeeEmploymentDetails.user_id == user_id,
            EmployeeEmploymentDetails.deleted_at.is_(None),
        )
    )
    if scope:
        query = query.where(EmployeeEmploymentDetails.company_id == scope)
    if lock:
        query = query.with_for_update()
    employee = db.scalar(query)
    if employee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
    return employee


def send_invitation(db: Session, actor: User, user_id: UUID) -> dict:
    try:
        employee = _employee_for_actor(db, actor, user_id, lock=True)
        if employee.profile_status != "PENDING":
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Invitation can only be sent while the profile is pending",
            )
        invitation = employee.invitation
        if invitation is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Invitation state is missing")
        if invitation.invitation_status == "ACCEPTED":
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Invitation was already accepted"
            )
        raw_token = new_opaque_token()
        now = datetime.now(UTC)
        expiry = now + timedelta(
            hours=get_settings().onboarding_invitation_expire_hours
        )
        invitation.sent_at = now
        invitation.expires_at = expiry
        invitation.submitted_at = None
        invitation.invitation_token_hash = hash_token(raw_token)
        invitation.invitation_status = "SENT"
        invitation_url = f"{get_settings().frontend_onboarding_url}?token={raw_token}"
        dispatch_row = email_dispatch.enqueue(
            db,
            entity_type="INVITATION",
            entity_id=user_id,
            recipient=employee.personal_email,
            template_key="EMPLOYEE_INVITATION",
            variables={
                "employee_name": f"{employee.first_name} {employee.last_name}".strip(),
                "company_name": employee.company.company_name,
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
    employee = _employee_for_actor(db, actor, user_id)
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
        .options(
            joinedload(OnboardingInvitation.employee).joinedload(
                EmployeeEmploymentDetails.company
            )
        )
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
        or invitation.invitation_status != "SENT"
        or invitation.employee.profile_status != "PENDING"
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Invalid or expired invitation"
        )
    employee = invitation.employee
    return {
        "first_name": employee.first_name,
        "last_name": employee.last_name,
        "company_name": employee.company.company_name,
        "expires_at": invitation.expires_at,
    }


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


def submit_onboarding(
    db: Session,
    raw_token: str,
    fields: dict,
    files: dict[str, tuple[str, str | None, bytes]],
) -> dict:
    stored_paths: list[Path] = []
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
            )
            .where(OnboardingInvitation.invitation_token_hash == hash_token(raw_token))
            .with_for_update()
        )
        now = datetime.now(UTC)
        if (
            invitation is None
            or invitation.invitation_status != "SENT"
            or invitation.expires_at <= now
        ):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Invalid or expired invitation"
            )
        employee = invitation.employee
        if employee.profile_status != "PENDING":
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Employee profile was already submitted"
            )
        if (
            employee.personal_details
            or employee.contact_details
            or employee.bank_details
        ):
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Employee profile was already submitted"
            )
        if fields["new_password"] != fields["confirm_password"]:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "Passwords do not match"
            )
        try:
            password_hash = hash_password(fields["new_password"])
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)
            ) from None
        encryptor = _encryptor()
        aadhaar = re.sub(r"\D", "", fields["aadhaar_number"])
        pan = fields["pan_number"].strip().upper()
        if len(aadhaar) != 12:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Aadhaar number must contain 12 digits",
            )
        if not re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", pan):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "PAN number is invalid"
            )
        if not re.fullmatch(
            r"[A-Z]{4}0[A-Z0-9]{6}", fields["ifsc_code"].strip().upper()
        ):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "IFSC code is invalid"
            )
        account_number = re.sub(r"\s", "", fields["account_number"])
        if not account_number.isdigit() or not 4 <= len(account_number) <= 50:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Bank account number must contain only digits",
            )
        if fields["date_of_birth"] >= date.today():
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Date of birth must be in the past",
            )
        mobile_number = fields["mobile_number"].strip()
        if not re.fullmatch(r"\+[1-9][0-9]{7,14}", mobile_number):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Mobile number must include a valid country code",
            )
        if (
            not fields["emergency_contact_name"].strip()
            or not fields["emergency_contact_phone"].strip()
            or not fields["emergency_contact_relationship"].strip()
        ):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Emergency contact name and phone are required",
            )
        if not fields["bank_name"].strip():
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "Bank name is required"
            )
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
        if set(files) != {"identity_proof", "cancelled_cheque"}:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Both required documents must be provided",
            )

        stored: list[tuple[str, str, str, int, str]] = []
        for document_type, (filename, content_type, contents) in files.items():
            path, clean_name, media_type = _store_document(
                document_type, filename, content_type, contents
            )
            stored_paths.append(Path(path))
            stored.append((document_type, path, clean_name, len(contents), media_type))

        gender = fields["gender"].upper()
        if gender not in {"MALE", "FEMALE", "OTHER", "PREFER_NOT_TO_SAY"}:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "Gender is invalid"
            )
        employee.personal_details = EmployeePersonalDetails(
            birth_date=fields["date_of_birth"],
            gender=gender,
            aadhaar_number_encrypted=encryptor.encrypt(aadhaar.encode()).decode(),
            aadhaar_number_last_four=aadhaar[-4:],
            pan_number_encrypted=encryptor.encrypt(pan.encode()).decode(),
            passport_number_encrypted=(
                encryptor.encrypt(fields["passport_number"].strip().encode()).decode()
                if fields.get("passport_number", "").strip()
                else None
            ),
        )
        employee.contact_details = EmployeeContactDetails(
            mobile_number=mobile_number,
            emergency_contact_name=fields["emergency_contact_name"].strip(),
            emergency_contact_phone=fields["emergency_contact_phone"].strip(),
            emergency_contact_relation=fields["emergency_contact_relationship"].strip(),
        )
        employee.bank_details = EmployeeBankDetails(
            bank_name=fields["bank_name"].strip(),
            bank_account_number_encrypted=encryptor.encrypt(
                account_number.encode()
            ).decode(),
            bank_account_number_last_four=account_number[-4:],
            ifsc_code=fields["ifsc_code"].strip().upper(),
            account_holder_name=f"{employee.first_name} {employee.last_name}".strip(),
        )
        employee.skills_and_interests = EmployeeSkillsAndInterests(
            additional_qualifications=fields.get("qualification") or None,
            languages_spoken=json.dumps(languages, ensure_ascii=False),
        )
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
        employee.profile_status = "SUBMITTED"
        employee.onboarding_status = "SUBMITTED"
        invitation.invitation_status = "ACCEPTED"
        invitation.submitted_at = now
        invitation.draft_form_data = None
        employee.user.password_hash = password_hash
        employee.user.phone_number = mobile_number
        employee.user.account_status = "ACTIVE"
        employee.user.is_active = True
        db.commit()
        return {"profile_status": "SUBMITTED"}
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
            (item for item in user.role_assignments if item.role.is_active), None
        )
        if assignment:
            role_name = assignment.role.role_name
            role_id = str(assignment.role.id)
    return {
        "id": str(user.id) if user else None,
        "first_name": employee.first_name,
        "middle_name": employee.middle_name,
        "last_name": employee.last_name,
        "employee_code": employee.employee_code,
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
    }


def list_employees(
    db: Session,
    actor: User,
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
    scope = _company_scope(actor)
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
        )
        .where(EmployeeEmploymentDetails.deleted_at.is_(None))
    )
    conditions = []
    if scope:
        conditions.append(EmployeeEmploymentDetails.company_id == scope)
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
    return {
        "items": [_employee_list_item(employee) for employee in rows],
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
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Unable to decrypt stored employee information",
        ) from None


def employee_details(db: Session, actor: User, user_id: UUID) -> dict:
    employee = _employee_for_actor(db, actor, user_id)
    user = employee.user
    assignment = (
        next((item for item in user.role_assignments if item.role.is_active), None)
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
        "location": employee.work_location,
        "company_email": employee.company_email,
        "personal_email": employee.personal_email,
        "pf_applicable": employee.pf_applicable,
        "joining_date": employee.joining_date,
        "start_date": employee.employment_start_date,
        "end_date": employee.employment_end_date,
    }
    submitted = employee.profile_status in {"SUBMITTED", "APPROVED"}
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
            "aadhaar_number": (
                f"********{personal.aadhaar_number_last_four}"
                if personal.aadhaar_number_last_four
                else None
            ),
            "pan_number": _mask(_decrypt(encryptor, personal.pan_number_encrypted), 4),
            "passport_number": _mask(
                _decrypt(encryptor, personal.passport_number_encrypted), 4
            ),
            "mobile_number": contact.mobile_number,
            "emergency_contact": {
                "name": contact.emergency_contact_name,
                "phone": contact.emergency_contact_phone,
                "relationship": contact.emergency_contact_relation,
            },
            "bank_details": {
                "bank_name": bank.bank_name,
                "account_number": _mask(bank.bank_account_number_last_four, 4),
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
        employee = _employee_for_actor(db, actor, user_id, lock=True)
        user = employee.user
        values = payload.model_dump(exclude_unset=True)
        company_id = employee.company_id
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
                    Department.company_id == company_id,
                    Department.is_active.is_(True),
                )
            )
            if department is None:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "Department is not active in this company",
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
                    Entity.company_id == company_id,
                    Entity.is_active.is_(True),
                )
            )
            if entity is None:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "Entity is not active in this company",
                )
            employee.entity_id = entity.id
            employee.entity_name = entity.name
        if "role_id" in values:
            role = db.scalar(
                select(Role).where(
                    Role.id == values["role_id"], Role.is_active.is_(True)
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
        if "company_email" in values:
            email = normalize_email(str(values["company_email"]))
            duplicate = db.scalar(
                select(User.id).where(
                    func.lower(User.email) == email,
                    User.id != user_id,
                    User.deleted_at.is_(None),
                )
            )
            if duplicate:
                raise HTTPException(
                    status.HTTP_409_CONFLICT, "Company email already exists"
                )
            user.email = email
            employee.company_email = email
        if "personal_email" in values:
            email = normalize_email(str(values["personal_email"]))
            duplicate = db.scalar(
                select(EmployeeEmploymentDetails.id).where(
                    EmployeeEmploymentDetails.company_id == company_id,
                    EmployeeEmploymentDetails.user_id != user_id,
                    func.lower(EmployeeEmploymentDetails.personal_email) == email,
                    EmployeeEmploymentDetails.deleted_at.is_(None),
                )
            )
            if duplicate:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "Personal email already exists in this company",
                )
            employee.personal_email = email
        if employee.employment_start_date < employee.joining_date:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Start date must be on or after joining date",
            )
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


def approve_employee(db: Session, actor: User, user_id: UUID) -> dict:
    try:
        employee = _employee_for_actor(db, actor, user_id, lock=True)
        if employee.profile_status != "SUBMITTED":
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Only submitted profiles can be approved"
            )
        required_documents = {doc.document_type for doc in employee.documents}
        if not {"identity_proof", "cancelled_cheque"}.issubset(required_documents):
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Required documents are missing"
            )
        if not (
            employee.personal_details
            and employee.contact_details
            and employee.bank_details
        ):
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Submitted employee details are incomplete"
            )
        employee.profile_status = "APPROVED"
        employee.onboarding_status = "APPROVED"
        employee.approved_by_user_id = actor.id
        employee.approved_at = datetime.now(UTC)
        db.commit()
        return {"profile_status": "APPROVED"}
    except BaseException:
        db.rollback()
        raise
