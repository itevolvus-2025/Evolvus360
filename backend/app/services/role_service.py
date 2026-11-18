"""Role configuration persistence operations."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.hrms import Menu, Role, RoleMenu
from app.schemas.menu import MenuResponse, RoleCreate


def create_role(db: Session, payload: RoleCreate) -> dict:
    try:
        code = payload.role_code.strip().upper()
        if db.scalar(select(Role.id).where(Role.role_code == code)):
            raise HTTPException(status.HTTP_409_CONFLICT, "Role code already exists")
        menu_ids = list(dict.fromkeys(payload.menu_ids))
        menus = (
            db.scalars(select(Menu).where(Menu.id.in_(menu_ids))).all()
            if menu_ids
            else []
        )
        if len(menus) != len(menu_ids):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "One or more menus were not found",
            )
        role = Role(
            role_code=code,
            role_name=payload.role_name.strip(),
            description=payload.description,
            is_active=True,
        )
        db.add(role)
        db.flush()
        db.add_all(RoleMenu(role_id=role.id, menu_id=menu.id) for menu in menus)
        result = {
            "id": str(role.id),
            "role_code": role.role_code,
            "role_name": role.role_name,
            "menus": [
                MenuResponse.model_validate(menu)
                for menu in sorted(
                    menus, key=lambda item: (item.seq_no, item.menu_name)
                )
            ],
        }
        db.commit()
        return result
    except BaseException:
        db.rollback()
        raise
