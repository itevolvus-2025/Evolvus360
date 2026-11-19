"""Role management endpoints restricted to Super Admin users."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.database.session import get_db
from app.models.hrms import User
from app.schemas.auth import ApiResponse
from app.schemas.role import RoleCreate, RoleUpdate
from app.services import role_service
from app.utils.responses import success_response

router = APIRouter(prefix="/roles", tags=["Roles"])
DbSession = Annotated[Session, Depends(get_db)]
SuperAdmin = Annotated[User, Depends(require_roles("SUPER_ADMIN"))]


@router.post("", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED)
def create_role(payload: RoleCreate, db: DbSession, admin: SuperAdmin):
    result = role_service.create_role(db, admin.id, payload)
    return success_response("Role created", result, status.HTTP_201_CREATED)


@router.get("", response_model=ApiResponse[dict])
def list_roles(
    db: DbSession,
    _admin: SuperAdmin,
    search: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
):
    result = role_service.list_roles(
        db, search=search, page=page, page_size=page_size
    )
    return success_response("Roles fetched", result)


@router.get("/{role_id}", response_model=ApiResponse[dict])
def get_role(role_id: UUID, db: DbSession, _admin: SuperAdmin):
    return success_response("Role fetched", role_service.get_role(db, role_id))


@router.put("/{role_id}", response_model=ApiResponse[dict])
def update_role(
    role_id: UUID, payload: RoleUpdate, db: DbSession, admin: SuperAdmin
):
    result = role_service.update_role(db, admin.id, role_id, payload)
    return success_response("Role updated", result)


@router.delete("/{role_id}", response_model=ApiResponse[dict])
def deactivate_role(role_id: UUID, db: DbSession, admin: SuperAdmin):
    result = role_service.deactivate_role(db, admin.id, role_id)
    return success_response("Role deactivated", result)
