from datetime import datetime
from threading import Lock
from time import monotonic
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import require_admin_key, require_service_key
from app.database.session import get_db
from app.schemas.email import SendEmailRequest
from app.services import email_service
from app.utils.responses import success_response

router = APIRouter(prefix="/emails", tags=["emails"])
_rate_lock = Lock()
_rate: dict[str, list[float]] = {}


def _limit(request: Request):
    key = request.client.host if request.client else "unknown"
    now = monotonic()
    with _rate_lock:
        recent = [t for t in _rate.get(key, []) if now - t < 60]
        if len(recent) >= get_settings().rate_limit_per_minute:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS, "Email request rate limit exceeded"
            )
        recent.append(now)
        _rate[key] = recent


@router.post("/send", dependencies=[Depends(require_service_key)])
def send(
    payload: SendEmailRequest,
    request: Request,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    _limit(request)
    if idempotency_key and len(idempotency_key) > 150:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Idempotency key is too long"
        )
    result, replay = email_service.send_email(
        db,
        payload,
        idempotency_key=idempotency_key,
        request_id=request.state.request_id,
    )
    if replay and result.status == "FAILED":
        result = email_service.retry_email(db, result.id)
    code = status.HTTP_200_OK if replay else status.HTTP_202_ACCEPTED
    return JSONResponse(
        status_code=code,
        content=success_response(
            "Email request processed",
            {
                "email_id": str(result.id),
                "status": result.status,
                "idempotent_replay": replay,
            },
            code,
        ),
    )


@router.get("/{email_id}", dependencies=[Depends(require_service_key)])
def get_email(email_id: UUID, db: Session = Depends(get_db)):
    from sqlalchemy import select

    from app.models.email import EmailLog

    row = db.scalar(select(EmailLog).where(EmailLog.id == email_id))
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Email was not found")
    return success_response("Email status retrieved", email_service.email_status(row))


@router.get("", dependencies=[Depends(require_admin_key)])
def list_emails(
    application_name: str | None = None,
    recipient: str | None = None,
    status_value: str | None = Query(default=None, alias="status"),
    template_key: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    result = email_service.list_email_logs(
        db,
        application_name=application_name,
        recipient=recipient,
        status_value=status_value,
        template_key=template_key,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )
    return success_response("Email logs retrieved", result)


@router.post("/{email_id}/retry", dependencies=[Depends(require_admin_key)])
def retry(email_id: UUID, db: Session = Depends(get_db)):
    row = email_service.retry_email(db, email_id)
    return success_response(
        "Email retry processed",
        {"email_id": row.id, "status": row.status, "retry_count": row.retry_count},
    )
