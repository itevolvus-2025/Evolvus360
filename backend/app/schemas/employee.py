"""Schemas for employee administration and invitation onboarding."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class MasterDataItem(BaseModel):
    id: UUID
    name: str
    code: str


class RoleItem(BaseModel):
    id: UUID
    name: str
    code: str


class EmployeeCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    first_name: str = Field(min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    department_id: UUID
    role_id: UUID
    designation: str = Field(min_length=1, max_length=150)
    entity_id: UUID
    location: str | None = Field(default=None, max_length=150)
    company_email: EmailStr
    personal_email: EmailStr
    pf_applicable: bool
    joining_date: date
    start_date: date
    end_date: date | None = None


class EmployeeUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

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
