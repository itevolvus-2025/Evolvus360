"""Database-backed authentication and authorization dependencies."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.security import decode_access_token
from app.database.session import get_db
from app.models.hrms import User, UserRole

bearer_scheme = HTTPBearer(auto_error=False, scheme_name="BearerAuth")


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    claims = _access_claims(credentials.credentials)
    if claims.get("purpose", "normal") != "normal":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Password change is required")
    user_id = UUID(claims["sub"])
    # Load current database role state; JWT role claims are never authoritative.
    user = db.scalar(
        select(User)
        .options(
            selectinload(User.role_assignments).joinedload(UserRole.role),
        )
        .where(User.id == user_id, User.deleted_at.is_(None))
    )
    if (
        user is None
        or not user.is_active
        or user.account_status != "ACTIVE"
        or user.must_change_password
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or inactive account")
    return user


def _access_claims(token: str) -> dict:
    try:
        claims = decode_access_token(token)
        UUID(claims["sub"])
        return claims
    except (ValueError, KeyError, TypeError):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


def get_password_change_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    claims = _access_claims(credentials.credentials)
    if claims.get("purpose") != "temporary_password_change":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Temporary credential required")
    user_id = UUID(claims["sub"])
    user = db.scalar(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    if (
        user is None
        or not user.is_active
        or user.account_status != "ACTIVE"
        or not user.must_change_password
        or user.temporary_password_used_at is None
        or claims.get("credential_use") != user.temporary_password_used_at.isoformat()
        or user.temporary_password_expires_at is None
        or user.temporary_password_expires_at <= datetime.now(UTC)
    ):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Temporary credential expired"
        )
    return user


def get_current_active_user(user: Annotated[User, Depends(get_current_user)]) -> User:
    return user


def _role_codes(user: User) -> set[str]:
    return {
        assignment.role.role_code
        for assignment in user.role_assignments
        if assignment.role.is_active
        and not getattr(assignment.role, "is_deleted", False)
    }


def _permission_codes(user: User) -> set[str]:
    return {
        permission
        for role in user.role_assignments
        if role.role.is_active and not getattr(role.role, "is_deleted", False)
        for permission in (role.role.permissions or [])
        if isinstance(permission, str)
    }


def require_roles(*role_codes: str) -> Callable:
    def dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        if not set(role_codes).intersection(_role_codes(user)):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
        return user

    return dependency


def require_permissions(*codes: str) -> Callable:
    def dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        if not set(codes).issubset(_permission_codes(user)):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permission")
        return user

    return dependency
