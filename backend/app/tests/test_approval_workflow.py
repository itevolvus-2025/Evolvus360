"""Focused approval-state checks without a live database or email service."""

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import CheckConstraint, create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dependencies import get_current_user, get_password_change_user
from app.core.security import verify_password
from app.database.base import Base
from app.models.hrms import (
    Department,
    EmailDispatchOutbox,
    EmployeeBankDetails,
    EmployeeEmploymentDetails,
    Entity,
    User,
)
from app.services import approval_service, auth_service, employee_service


class FakeSession:
    def __init__(self, row):
        self.row = row
        self.added = []
        self.commits = 0

    def scalar(self, _statement):
        return self.row

    def add(self, row):
        self.added.append(row)

    def commit(self):
        self.commits += 1

    def rollback(self):
        pass


def _employee():
    user = SimpleNamespace(
        id=uuid4(),
        email="employee@example.test",
        account_status="PENDING_APPROVAL",
        is_active=True,
        password_hash=None,
        must_change_password=False,
        temporary_password_expires_at=None,
        temporary_password_used_at=None,
    )
    return SimpleNamespace(
        id=uuid4(),
        user=user,
        first_name="Employee",
        profile_status="PENDING_APPROVAL",
        onboarding_status="PENDING_APPROVAL",
        documents=[
            SimpleNamespace(document_type="identity_proof"),
            SimpleNamespace(document_type="cancelled_cheque"),
        ],
        personal_details=object(),
        contact_details=object(),
        bank_details=object(),
        approved_by_user_id=None,
        approved_at=None,
        rejection_reason=None,
        invitation=None,
    )


def test_approval_activates_only_after_decision_and_never_returns_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    employee = _employee()
    session = FakeSession(employee)
    actor = SimpleNamespace(id=uuid4())
    dispatch_row = SimpleNamespace(id=uuid4())
    queued = {}

    def enqueue(*_args, **kwargs):
        queued.update(kwargs["variables"])
        return dispatch_row

    monkeypatch.setattr(approval_service.email_dispatch, "enqueue", enqueue)
    monkeypatch.setattr(approval_service.email_dispatch, "dispatch", lambda _id: False)

    result = approval_service.approve(session, actor, employee.id)

    assert result["onboarding_status"] == "APPROVED"
    assert result["email_dispatch_status"] == "FAILED"
    assert "password" not in result
    assert employee.user.account_status == "ACTIVE"
    assert employee.user.must_change_password is True
    assert employee.user.temporary_password_expires_at > datetime.now(UTC)
    assert employee.user.temporary_password_used_at is None
    temporary = re.search(
        r"Temporary one-time password: ([^.]*)\.", queued["message_text"]
    )
    assert temporary is not None
    assert verify_password(temporary.group(1), employee.user.password_hash)
    assert session.commits == 1

    with pytest.raises(HTTPException) as duplicate:
        approval_service.approve(session, actor, employee.id)
    assert duplicate.value.status_code == 409
    assert session.commits == 1


def test_rejection_keeps_account_ineligible_and_requires_reason(monkeypatch) -> None:
    employee = _employee()
    session = FakeSession(employee)
    actor = SimpleNamespace(id=uuid4())
    with pytest.raises(HTTPException) as missing_reason:
        approval_service.reject(session, actor, employee.id, "  ")
    assert missing_reason.value.status_code == 422

    row = SimpleNamespace(id=uuid4())
    monkeypatch.setattr(approval_service.email_dispatch, "enqueue", lambda *a, **k: row)
    monkeypatch.setattr(approval_service.email_dispatch, "dispatch", lambda _id: False)
    result = approval_service.reject(session, actor, employee.id, "Missing proof")
    assert result["onboarding_status"] == "REJECTED"
    assert result["email_dispatch_status"] == "FAILED"
    assert employee.user.account_status == "INVITED"
    assert employee.user.password_hash is None
    assert employee.user.must_change_password is False


def test_submission_approval_and_forced_password_change_end_to_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload_dir = Path.cwd() / "uploads"
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("PII_ENCRYPTION_KEY", key)
    monkeypatch.setenv("JWT_SECRET_KEY", "0123456789abcdef0123456789abcdef")
    monkeypatch.setenv("PRIVATE_UPLOAD_DIR", str(upload_dir))
    get_settings.cache_clear()
    stored_files: list[Path] = []

    def store_document(kind, filename, content_type, contents):
        path = upload_dir / f"approval-test-{uuid4().hex}.pdf"
        path.write_bytes(contents)
        stored_files.append(path)
        return str(path), filename, content_type

    monkeypatch.setattr(employee_service, "_store_document", store_document)

    bank_table = EmployeeBankDetails.__table__
    regex_check = next(
        check
        for check in bank_table.constraints
        if isinstance(check, CheckConstraint) and "ifsc_code ~" in str(check.sqltext)
    )
    bank_table.constraints.remove(regex_check)
    engine = create_engine("sqlite://")
    try:
        Base.metadata.create_all(engine)
    finally:
        bank_table.constraints.add(regex_check)

    session = Session(engine, expire_on_commit=False)
    email_variables = {}
    try:
        from app.core.security import hash_password

        user = User(
            email="employee@example.test",
            first_name="Ari",
            last_name="Employee",
            password_hash=hash_password("OriginalPassword123!"),
            account_status="ACTIVE",
            is_active=True,
        )
        department = Department(name="People", code="PEOPLE", is_active=True)
        entity = Entity(name="Evolvus", code="EV", is_active=True)
        session.add_all([user, department, entity])
        session.flush()
        today = datetime.now(UTC).date()
        employee = EmployeeEmploymentDetails(
            user_id=user.id,
            department_id=department.id,
            entity_id=entity.id,
            employee_code="EV-001",
            first_name="Ari",
            last_name="Employee",
            entity_name=entity.name,
            department_name=department.name,
            designation="Analyst",
            company_email=user.email,
            personal_email="ari@example.test",
            pf_applicable=False,
            joining_date=today,
            employment_start_date=today,
            created_by_user_id=user.id,
            onboarding_status="INVITED",
            profile_status="PENDING",
        )
        session.add(employee)
        session.commit()

        submitted = employee_service.submit_employee_onboarding(
            session,
            user,
            {
                "date_of_birth": datetime(1995, 1, 2).date(),
                "gender": "OTHER",
                "mobile_number": "+14155550123",
                "aadhaar_number": "123456789012",
                "pan_number": "ABCDE1234F",
                "emergency_contact_name": "Contact",
                "emergency_contact_phone": "+14155550124",
                "emergency_contact_relationship": "Sibling",
                "bank_name": "Bank",
                "account_number": "1234567890",
                "ifsc_code": "ABCD0123456",
                "qualification": "BSc",
                "skills": "Python",
                "languages": "English",
            },
            {
                "identity_proof": ("id.pdf", "application/pdf", b"%PDF-identity"),
                "cancelled_cheque": ("cheque.pdf", "application/pdf", b"%PDF-cheque"),
            },
        )
        assert submitted["onboarding_status"] == "PENDING_APPROVAL"
        assert user.account_status == "PENDING_APPROVAL"
        with pytest.raises(HTTPException):
            auth_service.login(session, user.email, "OriginalPassword123!")

        def dispatch(outbox_id):
            row = session.get(EmailDispatchOutbox, outbox_id)
            email_variables.update(
                json.loads(Fernet(key.encode()).decrypt(row.encrypted_payload.encode()))
            )
            return True

        monkeypatch.setattr(approval_service.email_dispatch, "dispatch", dispatch)
        approved = approval_service.approve(session, user, employee.id)
        assert approved["onboarding_status"] == "APPROVED"
        assert "password" not in approved
        temp_match = re.search(
            r"Temporary one-time password: ([^.]*)\.", email_variables["message_text"]
        )
        assert temp_match is not None
        temp_password = temp_match.group(1)
        assert verify_password(temp_password, user.password_hash)

        limited = auth_service.login(session, user.email, temp_password)
        assert limited["password_change_required"] is True
        assert limited["refresh_token"] == ""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=limited["access_token"]
        )
        with pytest.raises(HTTPException):
            get_current_user(credentials, session)
        change_user = get_password_change_user(credentials, session)
        auth_service.change_temporary_password(
            session, change_user, "NewEmployeePassword123!"
        )
        with pytest.raises(HTTPException):
            auth_service.login(session, user.email, temp_password)
        normal = auth_service.login(session, user.email, "NewEmployeePassword123!")
        assert normal["refresh_token"]
        assert user.must_change_password is False
        assert employee.profile_status == "APPROVED"
    finally:
        session.close()
        engine.dispose()
        for file_path in stored_files:
            file_path.unlink(missing_ok=True)
        get_settings.cache_clear()
