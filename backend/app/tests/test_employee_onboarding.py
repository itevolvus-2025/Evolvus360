"""Focused checks for employee onboarding validation and API registration."""

from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.main import app
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.schemas.validators import (
    AADHAAR_CHECKSUM_ERROR,
    AADHAAR_LENGTH_ERROR,
    validate_aadhaar,
    has_valid_verhoeff,
    validate_mobile,
    validate_pan,
)
from app.services.employee_service import (
    _decrypt,
    _employee_prefix,
    _encryptor,
    _store_document,
    _validate_onboarding_contact_and_compliance,
)


@pytest.mark.parametrize(
    ("code", "expected"), [("ETPL", "ET"), ("A-BC", "AB"), ("x9-team", "X9")]
)
def test_employee_prefix_uses_first_two_alphanumeric_characters(
    code: str, expected: str
) -> None:
    assert _employee_prefix(code) == expected


def test_employee_prefix_rejects_codes_without_two_alphanumeric_characters() -> None:
    with pytest.raises(HTTPException, match="at least two"):
        _employee_prefix("-")


def test_employee_create_rejects_frontend_employee_code() -> None:
    fields = {
        "first_name": "Alex",
        "last_name": "Employee",
        "department_id": "00000000-0000-0000-0000-000000000001",
        "role_id": "00000000-0000-0000-0000-000000000002",
        "designation": "Analyst",
        "entity_id": "00000000-0000-0000-0000-000000000003",
        "company_email": "alex@example.com",
        "personal_email": "alex.personal@example.com",
        "pf_applicable": True,
        "joining_date": "2026-11-24",
        "start_date": "2026-11-24",
        "employee_code": "ET-001",
    }
    with pytest.raises(ValidationError):
        EmployeeCreate.model_validate(fields)


def _valid_aadhaar() -> str:
    for prefix in range(100_000_000_000, 100_000_001_000):
        candidate = str(prefix)
        if has_valid_verhoeff(candidate):
            return candidate
    raise AssertionError("Could not construct a Verhoeff-valid test value")


def test_mobile_aadhaar_and_pan_validators_enforce_formats() -> None:
    assert validate_mobile("9876543210") == "9876543210"
    for invalid in ("5876543210", "987654321", "+919876543210", "98765 43210"):
        with pytest.raises(ValueError):
            validate_mobile(invalid)

    aadhaar = _valid_aadhaar()
    assert validate_aadhaar(aadhaar) == aadhaar
    with pytest.raises(ValueError, match=AADHAAR_LENGTH_ERROR):
        validate_aadhaar("12345678901")
    mutated = aadhaar[:-1] + str((int(aadhaar[-1]) + 1) % 10)
    with pytest.raises(ValueError, match=AADHAAR_CHECKSUM_ERROR):
        validate_aadhaar(mutated)

    assert validate_pan("abcde1234f") == "ABCDE1234F"
    for invalid in ("ABCDE12345", "ABCD12345F", "ABCDE12@4F", "ABCDE1234F "):
        with pytest.raises(ValueError):
            validate_pan(invalid)


def test_profile_submission_returns_all_sensitive_field_errors_without_values() -> None:
    user = type("TestUser", (), {"id": uuid4()})()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: object()
    data = {
        "date_of_birth": "1995-01-02",
        "gender": "OTHER",
        "mobile_number": "1234567890",
        "aadhaar_number": "123456789012",
        "pan_number": "bad-pan",
        "emergency_contact_name": "Contact",
        "emergency_contact_phone": "9876543210",
        "emergency_contact_relationship": "Sibling",
        "bank_name": "Bank",
        "account_number": "1234567890",
        "ifsc_code": "ABCD0123456",
    }
    files = {
        "identity_proof": ("id.pdf", b"%PDF-test", "application/pdf"),
        "cancelled_cheque": ("cheque.pdf", b"%PDF-test", "application/pdf"),
    }
    try:
        response = TestClient(app).post(
            "/api/v1/employee/onboarding/submit", data=data, files=files
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 422
    payload = response.json()
    assert payload["message"] == "Validation failed. Please correct the highlighted fields."
    assert set(payload["errors"]) == {"mobile_number", "aadhaar_number", "pan_number"}
    assert "1234567890" not in response.text
    assert "123456789012" not in response.text
    assert "bad-pan" not in response.text


def test_employee_create_trims_names_and_normalizes_email_domain() -> None:
    fields = {
        "first_name": "  Alex  Marie ",
        "middle_name": " O'Neil ",
        "last_name": " Employee ",
        "department_id": "00000000-0000-0000-0000-000000000001",
        "role_id": "00000000-0000-0000-0000-000000000002",
        "designation": "HR Generalist",
        "location": "New York",
        "entity_id": "00000000-0000-0000-0000-000000000003",
        "company_email": None,
        "personal_email": "  alex.personal@EXAMPLE.COM ",
        "pf_applicable": True,
        "joining_date": "2026-11-24",
        "start_date": "2026-11-24",
    }
    with pytest.raises(ValidationError) as error:
        EmployeeCreate.model_validate(fields)
    assert "middle_name" in str(error.value)

    fields["middle_name"] = "Marie"
    payload = EmployeeCreate.model_validate(fields)
    assert payload.first_name == "Alex Marie"
    assert payload.last_name == "Employee"
    assert str(payload.personal_email) == "alex.personal@example.com"
    assert payload.company_email is None


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("first_name", "Alex2"),
        ("middle_name", "Marie!"),
        ("last_name", "Employee-Doe"),
        ("designation", "HR 2"),
        ("location", "Pune!"),
        ("personal_email", "not-an-email"),
        ("department_id", "not-a-uuid"),
        ("role_id", "not-a-uuid"),
        ("entity_id", "not-a-uuid"),
        ("pf_applicable", "true"),
        ("joining_date", "24-11-2026"),
    ],
)
def test_employee_create_rejects_invalid_field_values(
    field: str, invalid_value: str
) -> None:
    payload = {
        "first_name": "Alex",
        "middle_name": "Marie",
        "last_name": "Employee",
        "department_id": "00000000-0000-0000-0000-000000000001",
        "role_id": "00000000-0000-0000-0000-000000000002",
        "designation": "HR Generalist",
        "location": "Pune",
        "entity_id": "00000000-0000-0000-0000-000000000003",
        "company_email": None,
        "personal_email": "alex.personal@example.com",
        "pf_applicable": True,
        "joining_date": "2026-11-24",
        "start_date": "2026-11-24",
    }
    payload[field] = invalid_value
    with pytest.raises(ValidationError):
        EmployeeCreate.model_validate(payload)


def test_employee_update_rejects_generated_code_and_employee_data_fields() -> None:
    with pytest.raises(ValidationError):
        EmployeeUpdate.model_validate({"employee_code": "ET-002"})
    update = EmployeeUpdate.model_validate(
        {
            "account_status": "INACTIVE",
            "reason_for_change": "Role change",
        }
    )
    assert update.account_status == "INACTIVE"
    assert update.reason_for_change == "Role change"
    with pytest.raises(ValidationError):
        EmployeeUpdate.model_validate({"account_number": "123456"})


def test_sensitive_values_are_encrypted_and_decrypted_from_configured_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PII_ENCRYPTION_KEY", Fernet.generate_key().decode())
    get_settings.cache_clear()
    try:
        encryptor = _encryptor()
        encrypted = encryptor.encrypt(b"123456789012").decode()
        assert encrypted != "123456789012"
        assert _decrypt(encryptor, encrypted) == "123456789012"
    finally:
        get_settings.cache_clear()


def test_private_document_storage_checks_file_signature_and_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_root = Path.cwd() / f".pytest-private-{uuid4().hex}"
    private_dir = private_root / "private"
    monkeypatch.setenv("PRIVATE_UPLOAD_DIR", str(private_dir))
    monkeypatch.setenv("MAX_ONBOARDING_FILE_SIZE_BYTES", "32")
    get_settings.cache_clear()
    try:
        path, filename, media_type = _store_document(
            "identity_proof", "identity.pdf", "application/pdf", b"%PDF-1.7 test"
        )
        assert filename == "identity.pdf"
        assert media_type == "application/pdf"
        assert str(private_dir) in path
        assert not path.endswith("identity.pdf")
        with pytest.raises(HTTPException) as error:
            _store_document(
                "identity_proof", "fake.pdf", "application/pdf", b"not a pdf"
            )
        assert error.value.status_code == 422
        with pytest.raises(HTTPException) as error:
            _store_document(
                "identity_proof",
                "large.pdf",
                "application/pdf",
                b"%PDF-" + b"x" * 40,
            )
        assert error.value.status_code == 413
    finally:
        get_settings.cache_clear()
        if private_root.resolve().parent == Path.cwd().resolve():
            rmtree(private_root, ignore_errors=True)


def test_onboarding_contact_bank_qualification_and_pf_validations() -> None:
    fields = {
        "emergency_contact_name": "Mary O'Neil",
        "emergency_contact_phone": "+91 9876543210",
        "emergency_contact_relationship": "Sister",
        "bank_name": "HDFC Bank Ltd.",
        "account_number": "AB1234567890",
        "ifsc_code": "HDFC0000123",
        "qualification": "BSc Biology 2024",
        "uan_number": "100912345678",
    }
    account, uan = _validate_onboarding_contact_and_compliance(fields, True)
    assert account == "AB1234567890"
    assert uan == "100912345678"

    fields["uan_number"] = ""
    with pytest.raises(HTTPException) as error:
        _validate_onboarding_contact_and_compliance(fields, True)
    assert error.value.detail["errors"].keys() == {"uan_number"}
    assert _validate_onboarding_contact_and_compliance(fields, False)[1] is None

    fields["qualification"] = "BSc Biology!"
    with pytest.raises(HTTPException) as error:
        _validate_onboarding_contact_and_compliance(fields, False)
    assert error.value.detail["errors"].keys() == {"qualification"}

    fields["qualification"] = "BSc Biology"
    fields["ifsc_code"] = "BADCODE"
    with pytest.raises(HTTPException) as error:
        _validate_onboarding_contact_and_compliance(fields, False)
    assert error.value.detail["errors"].keys() == {"ifsc_code"}


def test_onboarding_and_employee_routes_are_registered() -> None:
    paths = app.openapi()["paths"]
    assert {
        "/api/v1/master-data/departments",
        "/api/v1/master-data/entities",
        "/api/v1/master-data/roles",
        "/api/v1/users",
        "/api/v1/users/{user_id}",
        "/api/v1/users/{user_id}/invite",
        "/api/v1/users/{user_id}/approve",
        "/api/v1/onboarding/invitations/validate",
        "/api/v1/onboarding/submit",
        "/api/v1/employee/onboarding/form",
        "/api/v1/employee/onboarding/submit",
        "/api/v1/approvals/employees",
        "/api/v1/approvals/employees/{employee_id}",
        "/api/v1/approvals/employees/{employee_id}/approve",
        "/api/v1/approvals/employees/{employee_id}/reject",
        "/api/v1/auth/change-temporary-password",
    } <= set(paths)
