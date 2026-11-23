"""Validated authentication request and response payloads."""

from typing import Generic, Literal, TypeVar

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    statusCode: int
    message: str
    data: T | None = None


class AuthRole(BaseModel):
    id: str
    name: str
    code: str


class AuthUser(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    email: EmailStr
    first_name: str | None
    last_name: str | None
    roles: list[AuthRole]
    permissions: list[str]


class TokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str
    refresh_token: str
    token_type: Literal["bearer"]
    expires_in: int
    user: AuthUser
    permissions: list[str]
    password_change_required: bool = False


class ChangeTemporaryPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class LoginRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"email": "admin@example.com", "password": "StrongPassword123!"}
            ]
        }
    )
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_login_email(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


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
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self
