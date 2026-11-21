"""Schemas for employee administration and invitation onboarding."""

from datetime import date, datetime
import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StrictBool, field_validator

from app.schemas.validators import (
    DESIGNATION_ERROR,
    FIRST_NAME_ERROR,
    LAST_NAME_ERROR,
    LOCATION_ERROR,
    MIDDLE_NAME_ERROR,
    validate_name,
)


class MasterDataItem(BaseModel):
    id: UUID
    name: str
    code: str


class RoleItem(BaseModel):
    id: UUID
    name: str
    code: str


class EmployeeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str = Field(max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str = Field(max_length=100)
    department_id: UUID
    role_id: UUID
    designation: str = Field(max_length=150)
    entity_id: UUID
    location: str = Field(max_length=150)
    company_email: EmailStr | None = None
    personal_email: EmailStr
    pf_applicable: StrictBool
    joining_date: date
    start_date: date
    end_date: date | None = None

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, value: str) -> str:
        return validate_name(value, FIRST_NAME_ERROR)

    @field_validator("middle_name")
    @classmethod
    def validate_middle_name(cls, value: str | None) -> str | None:
        return validate_name(value or "", MIDDLE_NAME_ERROR, required=False) or None

    @field_validator("last_name")
    @classmethod
    def validate_last_name(cls, value: str) -> str:
        return validate_name(value, LAST_NAME_ERROR)

    @field_validator("designation")
    @classmethod
    def validate_designation(cls, value: str) -> str:
        return validate_name(value, DESIGNATION_ERROR)

    @field_validator("location")
    @classmethod
    def validate_location(cls, value: str) -> str:
        return validate_name(value, LOCATION_ERROR)

    @field_validator("company_email", "personal_email", mode="before")
    @classmethod
    def normalize_emails(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        value = value.strip()
        if "@" in value:
            local, domain = value.rsplit("@", 1)
            value = f"{local}@{domain.lower()}"
        return value

    @field_validator("joining_date", "start_date", "end_date", mode="before")
    @classmethod
    def validate_iso_dates(cls, value: object) -> object:
        if value is None or isinstance(value, (date, datetime)):
            return value
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("Date must be in YYYY-MM-DD format.")
        return value


class EmployeeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    department_id: UUID | None = None
    role_id: UUID | None = None
    designation: str | None = Field(default=None, min_length=1, max_length=150)
    entity_id: UUID | None = None
    location: str | None = Field(default=None, max_length=150)
    company_email: EmailStr | None = None
    personal_email: EmailStr | None = None
    pf_applicable: bool | None = None
    joining_date: date | None = None
    start_date: date | None = None
    end_date: date | None = None


class InvitationTokenRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)
