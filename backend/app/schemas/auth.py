"""Validated authentication request and response payloads."""

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    statusCode: int
    message: str
    data: T | None = None


class AuthRole(BaseModel):
    id: str
    name: str
    code: str


class AuthMenu(BaseModel):
    id: str
    menu_name: str
    menu_icon_svg: str
    seq_no: int


class AuthUser(BaseModel):
    id: str
    email: EmailStr
    first_name: str | None
    last_name: str | None
    roles: list[AuthRole]
    permissions: list[str]
    menus: list[AuthMenu]


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"]
    expires_in: int
    user: AuthUser


class LoginRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"email": "admin@example.com", "password": "StrongPassword123!"}
            ]
        }
    )
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"refresh_token": "PASTE_REFRESH_TOKEN"}]}
    )
    refresh_token: str = Field(min_length=32, max_length=256)


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"email": "admin@example.com"}]}
    )
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "token": "1234",
                    "email": "admin@example.com",
                    "new_password": "NewStrongPassword123!",
                    "confirm_password": "NewStrongPassword123!",
                }
            ]
        }
    )
    token: str = Field(min_length=1, max_length=256)
    email: EmailStr | None = None
    new_password: str = Field(min_length=12, max_length=128)
    confirm_password: str = Field(min_length=12, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self
