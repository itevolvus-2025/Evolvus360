"""Validated role management request payloads."""

from typing import Literal, Self

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class RoleCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(
        min_length=1,
        max_length=100,
        validation_alias=AliasChoices("name", "role_name", "role"),
    )
    description: str | None = Field(
        default=None,
        max_length=4000,
        validation_alias=AliasChoices("description", "purpose"),
    )
    permissions: list[str] = Field(default_factory=list)
    status: str = "active"
    role_code: str | None = Field(default=None, min_length=1, max_length=50)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Role name must not be blank")
        return value

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: str | None) -> str:
        if isinstance(value, str):
            val = value.lower().strip()
            if val in {"active"}:
                return "active"
            return "inactive"
        return "active"

    @field_validator("role_code")
    @classmethod
    def normalize_role_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().upper()
        if not value:
            raise ValueError("Role code must not be blank")
        return value


class RoleUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        validation_alias=AliasChoices("name", "role_name", "role"),
    )
    description: str | None = Field(
        default=None,
        max_length=4000,
        validation_alias=AliasChoices("description", "purpose"),
    )
    permissions: list[str] | None = None
    status: str | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Role name must not be blank")
        return value

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            val = value.lower().strip()
            if val in {"active", "enabled"}:
                return "active"
            return "inactive"
        return "active"

    @model_validator(mode="after")
    def require_update_field(self) -> Self:
        if not self.model_fields_set:
            raise ValueError(
                "Provide a role name, description, permissions, or status to update"
            )
        if "permissions" in self.model_fields_set and self.permissions is None:
            raise ValueError("Permissions must be an array; use an empty array to clear them")
        return self
