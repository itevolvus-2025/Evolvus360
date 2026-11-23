"""Authentication utility checks that do not require a live database."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core import security
from app.services import approval_service, auth_service


def test_password_hashing_uses_one_way_argon2_hashes() -> None:
    encoded = security.hash_password("StrongPassword123!")
    assert encoded.startswith("$argon2")
    assert encoded != "StrongPassword123!"
    assert security.verify_password("StrongPassword123!", encoded)
    assert not security.verify_password("WrongPassword123!", encoded)


def test_eight_character_password_matches_policy_and_schemas() -> None:
    from app.schemas.auth import ChangeTemporaryPasswordRequest, ResetPasswordRequest

    password = "Aa1!bcde"
    security.validate_password_strength(password)
    assert ResetPasswordRequest(
        token="reset-token", new_password=password, confirm_password=password
    )
    assert ChangeTemporaryPasswordRequest(
        new_password=password, confirm_password=password
    )
    with pytest.raises(ValueError, match="8-128"):
        security.validate_password_strength("Aa1!bcd")
    with pytest.raises(ValidationError):
        ResetPasswordRequest(
            token="reset-token", new_password="Aa1!bcd", confirm_password="Aa1!bcd"
        )


def test_reset_password_persists_hash_that_login_can_reuse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import auth_service

    now = datetime.now(UTC)
    user = SimpleNamespace(
        id=uuid4(),
        email="employee@example.test",
        password_hash=None,
        is_active=True,
        account_status="ACTIVE",
        locked_until=None,
        failed_login_attempts=0,
        must_change_password=True,
        temporary_password_expires_at=now + timedelta(hours=1),
        temporary_password_used_at=now,
        last_login_at=None,
    )
    reset = SimpleNamespace(
        user_id=user.id,
        used_at=None,
        revoked_at=None,
        expires_at=now + timedelta(minutes=30),
    )
    scalar_results = [reset, user]
    db = Mock()
    db.scalar.side_effect = lambda *_args, **_kwargs: (
        scalar_results.pop(0) if scalar_results else user
    )
    settings = SimpleNamespace(app_env="development", dev_password_reset_token=None)
    monkeypatch.setattr(auth_service, "get_settings", lambda: settings)
    monkeypatch.setattr(
        auth_service, "_issue_bundle", lambda *_args: {"access_token": "test-token"}
    )

    auth_service.reset_password(db, "single-use-token", "Aa1!bcde")

    assert security.verify_password("Aa1!bcde", user.password_hash)
    assert reset.used_at is not None
    assert user.must_change_password is False
    first_login = auth_service.login(db, user.email, "Aa1!bcde")
    second_login = auth_service.login(db, user.email, "Aa1!bcde")
    assert first_login["access_token"] == "test-token"
    assert second_login["access_token"] == "test-token"


def test_temporary_passwords_are_strong_and_temporary_login_is_single_use(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "0123456789abcdef0123456789abcdef")
    from app.core.config import get_settings

    get_settings.cache_clear()
    user = SimpleNamespace(
        id=uuid4(),
        email="employee@example.test",
        first_name="Test",
        last_name="User",
        password_hash=security.hash_password("Temporary123!"),
        account_status="ACTIVE",
        is_active=True,
        must_change_password=True,
        temporary_password_expires_at=datetime.now(UTC) + timedelta(hours=1),
        temporary_password_used_at=None,
        locked_until=None,
        failed_login_attempts=0,
        role_assignments=[],
    )
    db = Mock()
    db.scalar.return_value = user
    try:
        password = approval_service._temp_password()
        security.validate_password_strength(password)
        result = auth_service.login(db, user.email, "Temporary123!")
        assert result["password_change_required"] is True
        assert result["refresh_token"] == ""
        assert (
            security.decode_access_token(result["access_token"])["purpose"]
            == "temporary_password_change"
        )
        assert user.temporary_password_used_at is not None
        with pytest.raises(HTTPException) as error:
            auth_service.login(db, user.email, "Temporary123!")
        assert error.value.status_code == 401
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize("password", ["short", "alllowercase123!", "NoNumbersHere!"])
def test_password_strength_rejects_weak_passwords(password: str) -> None:
    with pytest.raises(ValueError, match="Password must be"):
        security.validate_password_strength(password)


def test_opaque_token_storage_uses_hash_not_raw_value() -> None:
    token = security.new_opaque_token()
    hashed = security.hash_token(token)
    assert len(token) > 40
    assert len(hashed) == 64
    assert token not in hashed
    assert security.hash_token(token) == hashed


def test_fixed_reset_token_is_only_used_in_local_development(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.config import get_settings
    from app.services.auth_service import _new_password_reset_token

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEV_PASSWORD_RESET_TOKEN", "1234")
    get_settings.cache_clear()
    try:
        assert _new_password_reset_token() == "1234"
        monkeypatch.setenv("APP_ENV", "production")
        get_settings.cache_clear()
        # Mock production settings because constructing them requires secrets.
        from types import SimpleNamespace

        monkeypatch.setattr(
            "app.services.auth_service.get_settings",
            lambda: SimpleNamespace(
                app_env="production", dev_password_reset_token="1234"
            ),
        )
        assert _new_password_reset_token() != "1234"
    finally:
        get_settings.cache_clear()


def test_fixed_reset_token_hash_is_scoped_to_user() -> None:
    from app.services.auth_service import _reset_token_hash

    assert _reset_token_hash("1234", uuid4()) != _reset_token_hash("1234", uuid4())


def test_forgot_password_reports_when_email_is_not_registered() -> None:
    from app.services.auth_service import forgot_password

    db = Mock()
    db.scalar.return_value = None
    with pytest.raises(HTTPException) as error:
        forgot_password(db, "missing@example.com")
    assert error.value.status_code == 404
    assert error.value.detail == "Email not found"
    db.commit.assert_not_called()


def test_forgot_password_uses_login_email_when_employee_has_no_company_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("PII_ENCRYPTION_KEY", "b" * 44)
    monkeypatch.setenv("FRONTEND_RESET_PASSWORD_URL", "https://hr.example.test/auth/reset-password")
    monkeypatch.setenv("DEV_PASSWORD_RESET_TOKEN", "local-console-only-token")
    get_settings.cache_clear()
    user = SimpleNamespace(
        id=uuid4(),
        email="personal@example.test",
        employee=SimpleNamespace(company_email=None),
    )
    db = Mock()
    db.scalar.return_value = user
    db.scalars.return_value.all.return_value = []
    dispatch_row = SimpleNamespace(id=uuid4())
    enqueue = Mock(return_value=dispatch_row)
    dispatch = Mock(return_value=True)
    monkeypatch.setattr(auth_service.email_dispatch, "enqueue", enqueue)
    monkeypatch.setattr(auth_service.email_dispatch, "dispatch", dispatch)
    try:
        auth_service.forgot_password(db, user.email)
    finally:
        get_settings.cache_clear()

    assert enqueue.call_args.kwargs["recipient"] == user.email
    assert enqueue.call_args.kwargs["template_key"] == "PASSWORD_RESET"
    reset_link = enqueue.call_args.kwargs["variables"]["reset_link"]
    assert reset_link.startswith("https://hr.example.test/auth/reset-password?token=")
    emailed_token = reset_link.split("?token=", 1)[1]
    assert len(emailed_token) >= 32
    assert emailed_token != "local-console-only-token"
    dispatch.assert_called_once_with(dispatch_row.id)
    db.commit.assert_called_once()


def test_password_recovery_api_accepts_the_frontend_json_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fastapi.testclient import TestClient

    from app.database.session import get_db
    from app.main import app

    fake_forgot = Mock()
    fake_reset = Mock()
    monkeypatch.setattr(auth_service, "forgot_password", fake_forgot)
    monkeypatch.setattr(auth_service, "reset_password", fake_reset)
    app.dependency_overrides[get_db] = lambda: object()
    try:
        client = TestClient(app)
        forgot_response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "employee@example.com"},
        )
        reset_response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": "single-use-token",
                "new_password": "StrongPassword123!",
                "confirm_password": "StrongPassword123!",
            },
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert forgot_response.status_code == 200
    assert fake_forgot.call_args.args[1] == "employee@example.com"
    assert reset_response.status_code == 200
    assert fake_reset.call_args.args[1:] == (
        "single-use-token",
        "StrongPassword123!",
        None,
    )


def test_access_token_has_expiry_type_subject_and_jti(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("JWT_SECRET_KEY", "0123456789abcdef0123456789abcdef")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    get_settings.cache_clear()
    try:
        signed, lifetime = security.create_access_token("user-123")
        claims = security.decode_access_token(signed)
        assert lifetime == 15 * 60
        assert claims["sub"] == "user-123"
        assert "company_id" not in claims
        assert claims["type"] == "access"
        assert claims["exp"] > int(datetime.now(UTC).timestamp())
        assert claims["jti"]
    finally:
        get_settings.cache_clear()


def test_auth_endpoints_are_mounted_and_documented() -> None:
    from app.main import app

    paths = set(app.openapi()["paths"])
    assert {
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/logout",
        "/api/v1/auth/forgot-password",
        "/api/v1/auth/reset-password",
        "/api/v1/auth/me",
    } <= paths
    assert "/docs" in {route.path for route in app.routes if hasattr(route, "path")}
    assert "BearerAuth" in app.openapi()["components"]["securitySchemes"]
