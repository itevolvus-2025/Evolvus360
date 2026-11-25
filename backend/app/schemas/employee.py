"""Schemas for employee administration and invitation onboarding."""

import re
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StrictBool, field_validator

from app.schemas.validators import (
    DESIGNATION_ERROR,
    FIRST_NAME_ERROR,
    LAST_NAME_ERROR,
    LOCATION_ERROR,
    MIDDLE_NAME_ERROR,
    validate_name,
    validate_mobile,
    validate_uan,
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
    account_status: Literal[
        "ACTIVE", "INACTIVE", "INVITED", "PENDING_APPROVAL", "LOCKED"
    ] | None = None
    reason_for_change: str | None = Field(default=None, max_length=1000)
    date_of_birth: date | None = None
    gender: Literal["MALE", "FEMALE", "OTHER", "PREFER_NOT_TO_SAY"] | None = None
    blood_group: Literal["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"] | None = None
    mother_tongue: str | None = Field(default=None, max_length=50)
    marital_status: Literal["SINGLE", "MARRIED", "DIVORCED", "WIDOWED"] | None = None
    aadhaar_number: str | None = Field(default=None, max_length=12)
    pan_number: str | None = Field(default=None, max_length=10)
    passport_number: str | None = Field(default=None, max_length=30)
    uan_number: str | None = Field(default=None, max_length=12)
    mobile_number: str | None = Field(default=None, max_length=25)
    landline_number: str | None = Field(default=None, max_length=25)
    alternate_phone_number: str | None = Field(default=None, max_length=25)
    emergency_contact_name: str | None = Field(default=None, max_length=150)
    emergency_contact_phone: str | None = Field(default=None, max_length=25)
    emergency_contact_relationship: str | None = Field(default=None, max_length=50)
    bank_name: str | None = Field(default=None, max_length=150)
    account_holder_name: str | None = Field(default=None, max_length=150)
    account_number: str | None = Field(default=None, max_length=50)
    ifsc_code: str | None = Field(default=None, max_length=11)
    qualification: str | None = Field(default=None, max_length=4000)
    skills: str | None = Field(default=None, max_length=4000)
    hobbies: str | None = Field(default=None, max_length=4000)
    languages: list[str] | None = Field(default=None, max_length=50)
    languages_read_and_written: str | None = Field(default=None, max_length=1000)

    @field_validator("mobile_number", "emergency_contact_phone")
    @classmethod
    def validate_mobile_numbers(cls, value: str | None) -> str | None:
        return validate_mobile(value) if value is not None else None

    @field_validator("uan_number")
    @classmethod
    def validate_uan_number(cls, value: str | None) -> str | None:
        return validate_uan(value) if value and value.strip() else None

class InvitationTokenRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)
