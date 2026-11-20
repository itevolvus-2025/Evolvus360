"""Password hashing, opaque tokens, and signed access-token helpers."""

import hashlib
import re
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from jose import JWTError, jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

_password_hash = PasswordHash.recommended()


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def validate_password_strength(password: str) -> None:
    """Require a long mixed password before any new credential is stored."""
    if (
        len(password) < 12
        or len(password) > 128
        or not all(
            (
                re.search(r"[a-z]", password),
                re.search(r"[A-Z]", password),
                re.search(r"\d", password),
                re.search(r"[^A-Za-z0-9]", password),
            )
        )
    ):
        raise ValueError(
            "Password must be 12-128 characters with upper, lower, number, "
            "and symbol characters"
        )


def hash_password(password: str) -> str:
    validate_password_strength(password)
    return _password_hash.hash(password)


def verify_password(password: str, encoded: str | None) -> bool:
    return bool(encoded) and _password_hash.verify(password, encoded)


def new_opaque_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _jwt_secret() -> str:
    settings = get_settings()
    secret = settings.jwt_secret_key or settings.secret_key
    if not secret:
        raise RuntimeError("JWT_SECRET_KEY must be configured")
    raw_secret = secret.get_secret_value()
    if len(raw_secret) < 32:
        raise RuntimeError("JWT_SECRET_KEY must contain at least 32 characters")
    return raw_secret


def create_access_token(
    user_id: str, *, purpose: str = "normal", credential_use: str | None = None
) -> tuple[str, int]:
    settings = get_settings()
    now = datetime.now(UTC)
    lifetime = settings.access_token_expire_minutes * 60
    claims = {
        "sub": user_id,
        "type": "access",
        "purpose": purpose,
        "iat": now,
        "exp": now + timedelta(seconds=lifetime),
        "jti": str(uuid4()),
    }
    if credential_use is not None:
        claims["credential_use"] = credential_use
    return jwt.encode(claims, _jwt_secret(), algorithm=settings.jwt_algorithm), lifetime


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        claims = jwt.decode(token, _jwt_secret(), algorithms=[settings.jwt_algorithm])
        if claims.get("type") != "access" or not claims.get("sub"):
            raise JWTError("Invalid token claims")
        return claims
    except JWTError as exc:
        raise ValueError("Invalid access token") from exc
