"""Validated menu and role creation payloads."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MenuCreate(BaseModel):
    menu_name: str = Field(min_length=1, max_length=100)
    menu_icon_svg: str = Field(min_length=1, max_length=20000)
    seq_no: int = Field(ge=0)


class MenuResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    menu_name: str
    menu_icon_svg: str
    seq_no: int


class RoleCreate(BaseModel):
    role_code: str = Field(min_length=1, max_length=50)
    role_name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    menu_ids: list[UUID] = Field(default_factory=list)
