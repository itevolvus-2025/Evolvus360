"""HR approval hub endpoints."""

from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.exceptions import HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dependencies import require_roles
from app.database.session import get_db
from app.models.hrms import EmployeeDocuments, EmployeeEmploymentDetails, User
from app.schemas.auth import ApiResponse
from app.services import approval_service
from app.utils.responses import success_response

router = APIRouter(prefix="/approvals/employees", tags=["Employee approvals"])
DbSession = Annotated[Session, Depends(get_db)]
Approver = Annotated[User, Depends(require_roles("HR", "SUPER_ADMIN"))]


class RejectionRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=4000)


@router.get("", response_model=ApiResponse[dict])
def list_approvals(
    db: DbSession,
    _user: Approver,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: str | None = None,
    onboarding_status: str | None = None,
):
    data = approval_service.list_pending(
        db,
        page=page,
        page_size=page_size,
        search=search,
        onboarding_status=onboarding_status,
    )
    return success_response("Employee approvals fetched", data)


@router.get("/{employee_id}", response_model=ApiResponse[dict])
def approval_details(employee_id: UUID, db: DbSession, _user: Approver):
    return success_response(
        "Employee approval details fetched", approval_service.details(db, employee_id)
    )


@router.get("/{employee_id}/documents/{document_id}")
def download_document(
    employee_id: UUID, document_id: UUID, db: DbSession, _user: Approver
):
    document = db.scalar(
        select(EmployeeDocuments)
        .join(EmployeeEmploymentDetails)
        .where(
            EmployeeDocuments.id == document_id,
            EmployeeDocuments.employee_id == employee_id,
            EmployeeEmploymentDetails.deleted_at.is_(None),
        )
    )
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    root = Path(get_settings().private_upload_dir).resolve()
    path = Path(document.storage_path).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found") from None
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return FileResponse(
        path,
        media_type=document.mime_type,
        filename=document.original_filename,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/{employee_id}/approve", response_model=ApiResponse[dict])
def approve_employee(employee_id: UUID, db: DbSession, user: Approver):
    result = approval_service.approve(db, user, employee_id)
    return success_response("Employee approved", result)


@router.post("/{employee_id}/reject", response_model=ApiResponse[dict])
def reject_employee(
    employee_id: UUID, payload: RejectionRequest, db: DbSession, user: Approver
):
    result = approval_service.reject(db, user, employee_id, payload.reason)
    return success_response("Employee rejected", result)


@router.post("/{employee_id}/emails/{event}/retry", response_model=ApiResponse[dict])
def retry_email(employee_id: UUID, event: str, db: DbSession, _user: Approver):
    return success_response(
        "Email delivery retried", approval_service.retry_email(db, employee_id, event)
    )


@router.post("/{employee_id}/credentials/regenerate", response_model=ApiResponse[dict])
def regenerate_credentials(employee_id: UUID, db: DbSession, user: Approver):
    result = approval_service.regenerate_credentials(db, user, employee_id)
    return success_response("Temporary credential delivery retried", result)
