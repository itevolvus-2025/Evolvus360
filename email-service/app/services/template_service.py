"""Administrator-controlled reusable email templates."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.email import EmailTemplate
from app.schemas.email import EmailTemplateCreate, EmailTemplateUpdate


def _template_payload(row: EmailTemplate) -> dict:
    return {
        "id": row.id,
        "template_key": row.template_key,
        "name": row.name,
        "subject": row.subject,
        "body_html": row.body_html,
        "body_text": row.body_text,
        "description": row.description,
        "required_variables": row.required_variables,
        "allow_custom_subject": row.allow_custom_subject,
        "is_active": row.is_active,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def list_templates(db: Session) -> list[dict]:
    rows = db.scalars(select(EmailTemplate).order_by(EmailTemplate.template_key)).all()
    return [_template_payload(row) for row in rows]


def get_template(db: Session, key: str) -> dict:
    row = db.scalar(
        select(EmailTemplate).where(EmailTemplate.template_key == key.upper())
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Email template was not found")
    return _template_payload(row)


def create_template(db: Session, payload: EmailTemplateCreate) -> dict:
    row = EmailTemplate(**payload.model_dump())
    row.template_key = row.template_key.upper()
    try:
        db.add(row)
        db.commit()
        db.refresh(row)
        return _template_payload(row)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Template key already exists"
        ) from None


def update_template(db: Session, key: str, payload: EmailTemplateUpdate) -> dict:
    row = db.scalar(
        select(EmailTemplate).where(EmailTemplate.template_key == key.upper())
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Email template was not found")
    for name, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, name, value)
    if not row.body_html and not row.body_text:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Template must contain an HTML or text body",
        )
    db.commit()
    db.refresh(row)
    return _template_payload(row)


def set_template_status(db: Session, key: str, is_active: bool) -> dict:
    row = db.scalar(
        select(EmailTemplate).where(EmailTemplate.template_key == key.upper())
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Email template was not found")
    row.is_active = is_active
    db.commit()
    db.refresh(row)
    return _template_payload(row)
