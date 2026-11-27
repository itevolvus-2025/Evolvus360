"""Email dispatch, status and audit API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class AttachmentInput(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)
    content_base64: str = Field(min_length=1)


class SendEmailRequest(BaseModel):
    application_name: str = Field(
        min_length=2, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$"
    )
    to: list[EmailStr] = Field(min_length=1, max_length=50)
    cc: list[EmailStr] = Field(default_factory=list, max_length=50)
    bcc: list[EmailStr] = Field(default_factory=list, max_length=50)
    template_key: str | None = Field(
        default=None, min_length=2, max_length=100, pattern=r"^[A-Z0-9_]+$"
    )
    subject: str | None = Field(default=None, max_length=255)
    body: str | None = Field(default=None, min_length=1)
    variables: dict[str, str | int | float | bool] = Field(default_factory=dict)
    attachments: list[AttachmentInput] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def template_or_body_required(self):
        if not self.template_key and not self.body:
            raise ValueError("Either template_key or body is required")
        return self

    @field_validator("to", "cc", "bcc")
    @classmethod
    def unique_addresses(cls, values: list[EmailStr]) -> list[EmailStr]:
        normalized = [str(value).casefold() for value in values]
        if len(set(normalized)) != len(normalized):
            raise ValueError("Recipient lists cannot contain duplicate addresses")
        return values


class EmailSendResult(BaseModel):
    email_id: UUID
    status: str
    idempotent_replay: bool = False


class EmailStatusResponse(BaseModel):
    id: UUID
    application_name: str
    recipient: str
    template_key: str
    status: str
    created_at: datetime
    sent_at: datetime | None
    retry_count: int


class EmailLogItem(EmailStatusResponse):
    subject: str
    error_message: str | None


class EmailLogPage(BaseModel):
    items: list[EmailLogItem]
    page: int
    page_size: int
    total: int
    total_pages: int


class EmailTemplateCreate(BaseModel):
    template_key: str = Field(min_length=2, max_length=100, pattern=r"^[A-Z0-9_]+$")
    name: str = Field(min_length=1, max_length=150)
    subject: str = Field(min_length=1, max_length=255)
    body_html: str | None = None
    body_text: str | None = None
    description: str | None = None
    required_variables: list[str] = Field(default_factory=list, max_length=100)
    allow_custom_subject: bool = False
    is_active: bool = True

    @model_validator(mode="after")
    def body_required(self):
        if not self.body_html and not self.body_text:
            raise ValueError("Template must contain an HTML or text body")
        return self


class EmailTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    subject: str | None = Field(default=None, min_length=1, max_length=255)
    body_html: str | None = None
    body_text: str | None = None
    description: str | None = None
    required_variables: list[str] | None = Field(default=None, max_length=100)
    allow_custom_subject: bool | None = None
    is_active: bool | None = None


class TemplateStatusUpdate(BaseModel):
    is_active: bool
