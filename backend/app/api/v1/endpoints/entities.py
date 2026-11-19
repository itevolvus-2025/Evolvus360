"""Entity dropdown endpoint backed by the relational entities table."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.database.session import get_db
from app.models.hrms import User
from app.schemas.auth import ApiResponse
from app.schemas.employee import MasterDataItem
from app.services import employee_service
from app.utils.responses import success_response

router = APIRouter(prefix="/entities", tags=["Entities"])
DbSession = Annotated[Session, Depends(get_db)]
AdminUser = Annotated[User, Depends(require_roles("HR", "SUPER_ADMIN"))]


@router.get("", response_model=ApiResponse[list[MasterDataItem]])
def list_entities(db: DbSession, _user: AdminUser):
    rows = employee_service.list_entities(db)
    items = [MasterDataItem(id=row.id, name=row.name, code=row.code) for row in rows]
    return success_response("Entities fetched successfully", items)
