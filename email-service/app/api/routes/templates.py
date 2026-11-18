from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import require_admin_key
from app.database.session import get_db
from app.schemas.email import (
    EmailTemplateCreate,
    EmailTemplateUpdate,
    TemplateStatusUpdate,
)
from app.services import template_service
from app.utils.responses import success_response

router = APIRouter(
    prefix="/templates", tags=["templates"], dependencies=[Depends(require_admin_key)]
)


@router.get("")
def list_templates(db: Session = Depends(get_db)):
    return success_response("Templates retrieved", template_service.list_templates(db))


@router.get("/{template_key}")
def get_template(template_key: str, db: Session = Depends(get_db)):
    return success_response(
        "Template retrieved", template_service.get_template(db, template_key)
    )


@router.post("", status_code=201)
def create_template(payload: EmailTemplateCreate, db: Session = Depends(get_db)):
    return success_response(
        "Template created", template_service.create_template(db, payload), 201
    )


@router.put("/{template_key}")
def update_template(
    template_key: str, payload: EmailTemplateUpdate, db: Session = Depends(get_db)
):
    return success_response(
        "Template updated", template_service.update_template(db, template_key, payload)
    )


@router.patch("/{template_key}/status")
def set_status(
    template_key: str, payload: TemplateStatusUpdate, db: Session = Depends(get_db)
):
    return success_response(
        "Template status updated",
        template_service.set_template_status(db, template_key, payload.is_active),
    )
