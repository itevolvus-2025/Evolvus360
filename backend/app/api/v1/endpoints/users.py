"""HR and Super Admin employee management APIs."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dependencies import require_roles
from app.database.session import get_db
from app.models.hrms import User
from app.schemas.auth import ApiResponse
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.services import approval_service, employee_service
from app.utils.responses import success_response

router = APIRouter(prefix="/users", tags=["Employee management"])
DbSession = Annotated[Session, Depends(get_db)]
AdminUser = Annotated[User, Depends(require_roles("HR", "SUPER_ADMIN"))]


@router.post("", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED)
def create_employee(payload: EmployeeCreate, db: DbSession, user: AdminUser):
    result = employee_service.create_employee(db, user, payload)
    return success_response(
        "Employee created successfully", result, status.HTTP_201_CREATED
    )


@router.post("/{user_id}/invite", response_model=ApiResponse[dict])
def invite_employee(user_id: UUID, db: DbSession, user: AdminUser):
    result = employee_service.send_invitation(db, user, user_id)
    if result.get("email_dispatch_status") == "FAILED":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=jsonable_encoder(
                success_response(
                    "Employee invitation email could not be dispatched",
                    result,
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            ),
        )
    return success_response("Employee invitation sent", result)


@router.post("/{user_id}/invite/retry", response_model=ApiResponse[dict])
def retry_invitation(user_id: UUID, db: DbSession, user: AdminUser):
    result = employee_service.retry_invitation(db, user, user_id)
    return success_response("Employee invitation dispatch retried", result)


@router.get("", response_model=ApiResponse[dict])
def list_employees(
    db: DbSession,
    user: AdminUser,
    search: str | None = None,
    role_id: UUID | None = None,
    department_id: UUID | None = None,
    entity_id: UUID | None = None,
    profile_status: str | None = None,
    account_status: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
):
    result = employee_service.list_employees(
        db,
        user,
        search=search,
        role_id=role_id,
        department_id=department_id,
        entity_id=entity_id,
        profile_status=profile_status,
        account_status=account_status,
        page=page,
        page_size=page_size,
    )
    return success_response("Users fetched successfully", result)


@router.get("/{user_id}", response_model=ApiResponse[dict])
def get_employee(user_id: UUID, db: DbSession, user: AdminUser):
    result = employee_service.employee_details(db, user, user_id)
    return success_response("User details fetched successfully", result)


@router.put("/{user_id}", response_model=ApiResponse[dict])
def update_employee(
    user_id: UUID, payload: EmployeeUpdate, db: DbSession, user: AdminUser
):
    result = employee_service.update_employee(db, user, user_id, payload)
    return success_response("Employee updated successfully", result)


@router.post("/{user_id}/deactivate", response_model=ApiResponse[dict])
def deactivate_employee(user_id: UUID, db: DbSession, user: AdminUser):
    result = employee_service.deactivate_user(db, user_id)
    return success_response("User deactivated successfully", result)


@router.put("/{user_id}/documents", response_model=ApiResponse[dict])
async def replace_employee_documents(
    user_id: UUID,
    db: DbSession,
    user: AdminUser,
    identity_proof: UploadFile | None = File(default=None),
    cancelled_cheque: UploadFile | None = File(default=None),
):
    limit = get_settings().max_onboarding_file_size_bytes + 1
    files = {}
    for document_type, upload in (
        ("identity_proof", identity_proof),
        ("cancelled_cheque", cancelled_cheque),
    ):
        if upload is not None and upload.filename:
            files[document_type] = (
                upload.filename,
                upload.content_type,
                await upload.read(limit),
            )
    result = employee_service.replace_employee_documents(db, user, user_id, files)
    return success_response("Employee documents updated successfully", result)


@router.post("/{user_id}/approve", response_model=ApiResponse[dict])
def approve_employee(user_id: UUID, db: DbSession, user: AdminUser):
    result = approval_service.approve(db, user, user_id)
    return success_response("Employee profile approved successfully", result)
