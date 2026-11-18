"""Authentication utility checks that do not require a live database."""

from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core import security


def test_password_hashing_uses_one_way_argon2_hashes() -> None:
    encoded = security.hash_password("StrongPassword123!")
    assert encoded.startswith("$argon2")
    assert encoded != "StrongPassword123!"
    assert security.verify_password("StrongPassword123!", encoded)
    assert not security.verify_password("WrongPassword123!", encoded)


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


def test_access_token_has_expiry_type_subject_and_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("JWT_SECRET_KEY", "0123456789abcdef0123456789abcdef")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    get_settings.cache_clear()
    try:
        signed, lifetime = security.create_access_token("user-123", "company-123")
        claims = security.decode_access_token(signed)
        assert lifetime == 15 * 60
        assert claims["sub"] == "user-123"
        assert claims["company_id"] == "company-123"
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
