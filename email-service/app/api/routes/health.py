from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import require_service_key
from app.database.session import get_db
from app.utils.responses import success_response

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return success_response("Email service is running", {"status": "ok"})


@router.get("/ready", dependencies=[Depends(require_service_key)])
def ready(db: Session = Depends(get_db)):
    settings = get_settings()
    db.execute(text("SELECT 1"))
    configured = bool(
        settings.smtp_host
        and settings.smtp_from_email
        and settings.email_payload_encryption_key
    )
    if not configured:
        from fastapi import HTTPException, status

        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Required email provider configuration is missing",
        )
    return success_response("Email service is ready", {"status": "ready"})
