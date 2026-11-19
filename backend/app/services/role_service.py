"""Role management persistence operations."""

import re
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.hrms import Role
from app.schemas.role import RoleCreate, RoleUpdate


def _visible_role_filter():
    """Roles that have not been soft-deleted (inactive roles remain manageable)."""
    return (Role.is_deleted.is_(False),)


def _role_payload(role: Role) -> dict:
    return {
        "id": str(role.id),
        "name": role.role_name,
        "role_name": role.role_name,
        "role_code": role.role_code,
        "description": role.description,
        "status": "active" if role.is_active and not role.is_deleted else "inactive",
        "is_active": role.is_active,
        "is_deleted": role.is_deleted,
        "permissions": list(role.permissions or []),
        "created_at": role.created_at,
        "updated_at": role.updated_at,
        "created_by": str(role.created_by) if role.created_by else None,
        "updated_by": str(role.updated_by) if role.updated_by else None,
    }


def _ensure_unique_name(db: Session, name: str, *, excluding: UUID | None = None) -> None:
    query = select(Role.id).where(
        func.lower(Role.role_name) == name.lower(),
        Role.is_active.is_(True),
        Role.is_deleted.is_(False),
    )
    if excluding is not None:
        query = query.where(Role.id != excluding)
    if db.scalar(query) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "An active role already uses this name")


def _code_for_name(db: Session, name: str, requested_code: str | None) -> str:
    if requested_code:
        if db.scalar(select(Role.id).where(Role.role_code == requested_code)) is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Role code already exists")
        return requested_code

    base = re.sub(r"[^A-Z0-9]+", "_", name.upper()).strip("_") or "ROLE"
    base = base[:50].rstrip("_") or "ROLE"
    candidate = base
    suffix = 2
    while db.scalar(select(Role.id).where(Role.role_code == candidate)) is not None:
        postfix = f"_{suffix}"
        candidate = f"{base[: 50 - len(postfix)].rstrip('_')}{postfix}"
        suffix += 1
    return candidate


def _is_role_unique_violation(error: IntegrityError) -> bool:
    message = str(error.orig).lower()
    constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", "")
    return constraint in {"uq_roles_role_code", "uq_roles_active_name_lower"} or any(
        name in message for name in ("uq_roles_role_code", "uq_roles_active_name_lower")
    )


def create_role(db: Session, actor_id: UUID, payload: RoleCreate) -> dict:
    try:
        if payload.status == "active":
            _ensure_unique_name(db, payload.name)
        role = Role(
            role_code=_code_for_name(db, payload.name, payload.role_code),
            role_name=payload.name,
            description=payload.description.strip() if payload.description else None,
            is_system_role=False,
            is_active=payload.status == "active",
            is_deleted=False,
            permissions=list(payload.permissions),
            created_by=actor_id,
            updated_by=actor_id,
        )
        db.add(role)
        db.flush()
        result = _role_payload(role)
        db.commit()
        return result
    except IntegrityError as error:
        db.rollback()
        if _is_role_unique_violation(error):
            raise HTTPException(
                status.HTTP_409_CONFLICT, "An active role already uses this name or code"
            ) from None
        raise
    except Exception:
        db.rollback()
        raise


def list_roles(
    db: Session, *, search: str | None, page: int, page_size: int
) -> dict:
    query = select(Role).where(*_visible_role_filter())
    if search and search.strip():
        query = query.where(Role.role_name.ilike(f"%{search.strip()}%"))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    roles = db.scalars(
        query.order_by(Role.role_name, Role.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [_role_payload(role) for role in roles],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }


def get_role(db: Session, role_id: UUID) -> dict:
    role = db.scalar(
        select(Role).where(Role.id == role_id, *_visible_role_filter())
    )
    if role is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Role not found")
    return _role_payload(role)


def update_role(db: Session, actor_id: UUID, role_id: UUID, payload: RoleUpdate) -> dict:
    role = db.scalar(
        select(Role).where(Role.id == role_id, *_visible_role_filter())
    )
    if role is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Role not found")
    try:
        if "name" in payload.model_fields_set and payload.name is not None:
            _ensure_unique_name(db, payload.name, excluding=role.id)
            role.role_name = payload.name
        if "description" in payload.model_fields_set:
            role.description = payload.description.strip() if payload.description else None
        if "permissions" in payload.model_fields_set:
            role.permissions = list(payload.permissions or [])
        if "status" in payload.model_fields_set and payload.status is not None:
            if payload.status == "inactive" and role.role_code == "SUPER_ADMIN":
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "The Super Admin role cannot be deactivated",
                )
            if payload.status == "active":
                _ensure_unique_name(db, role.role_name, excluding=role.id)
            role.is_active = payload.status == "active"
        role.updated_by = actor_id
        role.updated_at = datetime.now(UTC)
        db.flush()
        result = _role_payload(role)
        db.commit()
        return result
    except IntegrityError as error:
        db.rollback()
        if _is_role_unique_violation(error):
            raise HTTPException(
                status.HTTP_409_CONFLICT, "An active role already uses this name"
            ) from None
        raise
    except Exception:
        db.rollback()
        raise


