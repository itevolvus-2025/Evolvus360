"""Focused checks for employee onboarding validation and API registration."""

from pathlib import Path
from shutil import rmtree
from types import SimpleNamespace
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.config import get_settings
from app.main import app
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.services.employee_service import (
    _company_scope,
    _decrypt,
    _employee_prefix,
    _encryptor,
    _store_document,
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


def test_employee_update_rejects_employee_code_and_employee_data_fields() -> None:
    with pytest.raises(ValidationError):
        EmployeeUpdate.model_validate({"employee_code": "ET-002"})
    with pytest.raises(ValidationError):
        EmployeeUpdate.model_validate({"account_number": "123456"})


def test_hr_company_scope_is_enforced() -> None:
    company_id = uuid4()
    hr = SimpleNamespace(
        company_id=company_id,
        role_assignments=[
            SimpleNamespace(role=SimpleNamespace(role_code="HR", is_active=True))
        ],
    )
    assert _company_scope(hr) == company_id
    with pytest.raises(HTTPException) as error:
        _company_scope(hr, uuid4())
    assert error.value.status_code == 403


def test_super_admin_can_select_global_company_scope() -> None:
    admin = SimpleNamespace(
        company_id=None,
        role_assignments=[
            SimpleNamespace(
                role=SimpleNamespace(role_code="SUPER_ADMIN", is_active=True)
            )
        ],
    )
    assert _company_scope(admin) is None


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
    } <= set(paths)
