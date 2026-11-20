"""Thin auth routes; request validation and business logic live elsewhere."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_password_change_user
from app.database.session import get_db
from app.models.hrms import User
from app.schemas.auth import (
    ApiResponse,
    AuthUser,
    ChangeTemporaryPasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.services import auth_service
from app.utils.responses import success_response

router = APIRouter(prefix="/auth", tags=["Authentication"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/login",
    summary="Authenticate with email and password",
    response_model=ApiResponse[TokenResponse],
)
def login(payload: LoginRequest, db: DbSession):
    return success_response(
        "Login successful", auth_service.login(db, payload.email, payload.password)
    )


@router.post(
    "/refresh",
    summary="Rotate a refresh token",
    response_model=ApiResponse[TokenResponse],
)
def refresh(payload: RefreshRequest, db: DbSession):
    return success_response(
        "Token refreshed", auth_service.refresh(db, payload.refresh_token)
    )


@router.post(
    "/logout", summary="Revoke a refresh token", response_model=ApiResponse[None]
)
def logout(payload: RefreshRequest, db: DbSession):
    auth_service.logout(db, payload.refresh_token)
    return success_response("Logged out successfully")


@router.post(
    "/forgot-password",
    summary="Send password reset instructions",
    response_model=ApiResponse[None],
)
def forgot_password(payload: ForgotPasswordRequest, db: DbSession):
    auth_service.forgot_password(db, payload.email)
    return success_response("Password reset instructions sent.")


@router.post(
    "/reset-password",
    summary="Set a new password using a single-use reset token",
    response_model=ApiResponse[None],
)
def reset_password(payload: ResetPasswordRequest, db: DbSession):
    auth_service.reset_password(db, payload.token, payload.new_password, payload.email)
    return success_response("Password reset successful")


@router.post("/change-temporary-password", response_model=ApiResponse[None])
def change_temporary_password(
    payload: ChangeTemporaryPasswordRequest,
    db: DbSession,
    user: Annotated[User, Depends(get_password_change_user)],
):
    auth_service.change_temporary_password(db, user, payload.new_password)
    return success_response("Password changed. Please sign in again.")


@router.get(
    "/me",
    summary="Return the authenticated user and database-backed access",
    response_model=ApiResponse[AuthUser],
)
def me(user: Annotated[User, Depends(get_current_user)]):
    return success_response("Current user", auth_service._user_payload(user))
