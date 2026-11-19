"""Tenant-aware dropdown data used by employee administration screens."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.database.session import get_db
from app.models.hrms import User
from app.schemas.auth import ApiResponse
from app.schemas.employee import MasterDataItem, RoleItem
from app.services import employee_service
from app.utils.responses import success_response

router = APIRouter(prefix="/master-data", tags=["Employee master data"])
DbSession = Annotated[Session, Depends(get_db)]
AdminUser = Annotated[User, Depends(require_roles("HR", "SUPER_ADMIN"))]


@router.get("/departments", response_model=ApiResponse[list[MasterDataItem]])
def departments(
    db: DbSession,
    user: AdminUser,
    company_id: UUID | None = None,
):
    rows = employee_service.list_departments(db, user, company_id)
    return success_response(
        "Departments fetched successfully",
        [MasterDataItem(id=row.id, name=row.name, code=row.code) for row in rows],
    )


@router.get("/entities", response_model=ApiResponse[list[MasterDataItem]])
def entities(db: DbSession, _user: AdminUser):
    rows = employee_service.list_entities(db)
    return success_response(
        "Entities fetched successfully",
        [MasterDataItem(id=row.id, name=row.name, code=row.code) for row in rows],
    )


@router.get("/roles", response_model=ApiResponse[list[RoleItem]])
def roles(db: DbSession, _user: AdminUser):
    rows = employee_service.list_roles(db)
    return success_response(
        "Roles fetched successfully",
        [RoleItem(id=row.id, name=row.role_name, code=row.role_code) for row in rows],
    )
