"""Role creation with its menu assignments."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.database.session import get_db
from app.models.hrms import User
from app.schemas.auth import ApiResponse
from app.schemas.menu import RoleCreate
from app.services import role_service
from app.utils.responses import success_response

router = APIRouter(prefix="/roles", tags=["Roles"])
DbSession = Annotated[Session, Depends(get_db)]
SuperAdmin = Annotated[User, Depends(require_roles("SUPER_ADMIN"))]


@router.post("", response_model=ApiResponse[dict], status_code=201)
def create_role(payload: RoleCreate, db: DbSession, _admin: SuperAdmin):
    result = role_service.create_role(db, payload)
    return success_response("Role created", result, status_code=201)
