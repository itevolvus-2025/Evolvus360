"""Role management API, soft-delete, and authorization tests."""

from collections.abc import Generator
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import Column, MetaData, Table, Uuid, create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.dependencies import _permission_codes, _role_codes, get_current_user
from app.database.session import get_db
from app.main import app
from app.models.hrms import Role, UserRole
from app.schemas.auth import TokenResponse
from app.schemas.role import RoleCreate, RoleUpdate
from app.services import auth_service, employee_service, role_service


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    user_table = Table(
        "users", MetaData(), Column("id", Uuid(as_uuid=True), primary_key=True)
    )
    user_table.create(engine)
    Role.__table__.create(engine)
    UserRole.__table__.create(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _actor(session: Session, email: str = "admin@example.test") -> SimpleNamespace:
    del session
    return SimpleNamespace(id=uuid4(), email=email)


def test_role_create_duplicate_list_search_and_pagination(db_session: Session) -> None:
    actor = _actor(db_session)
    original_permissions = ["usermgmt", "leavemgmt", "attendancemgmt", "leaverequest"]
    created = role_service.create_role(
        db_session,
        actor.id,
        RoleCreate(
            name="HR Manager",
            description="People ops",
            permissions=original_permissions,
            status="active",
        ),
    )
    assert created["name"] == "HR Manager"
    assert created["is_deleted"] is False
    assert created["created_by"] == str(actor.id)
    assert created["updated_by"] == str(actor.id)
    assert created["role_code"] == "HR_MANAGER"
    assert created["permissions"] == original_permissions
    assert role_service.get_role(db_session, UUID(created["id"]))["permissions"] == original_permissions

    with pytest.raises(HTTPException) as duplicate:
        role_service.create_role(db_session, actor.id, RoleCreate(name="hr MANAGER"))
    assert duplicate.value.status_code == 409

    role_service.create_role(db_session, actor.id, RoleCreate(name="HR Assistant"))
    role_service.create_role(db_session, actor.id, RoleCreate(name="Finance Manager"))
    first_page = role_service.list_roles(db_session, search="hr", page=1, page_size=1)
    second_page = role_service.list_roles(db_session, search="hr", page=2, page_size=1)
    assert first_page["pagination"]["total"] == 2
    assert len(first_page["items"]) == len(second_page["items"]) == 1
    assert first_page["items"][0]["id"] != second_page["items"][0]["id"]


def test_get_update_and_duplicate_update(db_session: Session) -> None:
    actor = _actor(db_session)
    role_id = UUID(
        role_service.create_role(
            db_session, actor.id, RoleCreate(name="Recruiter")
        )["id"]
    )
    role = db_session.get(Role, role_id)
    assert role is not None
    role_service.create_role(db_session, actor.id, RoleCreate(name="Analyst"))
    fetched = role_service.get_role(db_session, role_id)
    assert fetched["name"] == "Recruiter"
    updated = role_service.update_role(
        db_session,
        actor.id,
        role_id,
        RoleUpdate(name="Talent Partner", description="Hiring"),
    )
    assert updated["name"] == "Talent Partner"
    assert updated["description"] == "Hiring"
    assert updated["updated_by"] == str(actor.id)
    assert updated["permissions"] == []

    with pytest.raises(HTTPException) as duplicate:
        role_service.update_role(
            db_session,
            actor.id,
            role_id,
            RoleUpdate(name="Analyst"),
        )
    assert duplicate.value.status_code == 409
    with pytest.raises(HTTPException) as missing:
        role_service.get_role(db_session, uuid4())
    assert missing.value.status_code == 404


def test_status_update_deactivates_and_keeps_assignments(db_session: Session) -> None:
    actor = _actor(db_session)
    employee = _actor(db_session, "employee@example.test")
    role_id = UUID(
        role_service.create_role(
            db_session, actor.id, RoleCreate(name="Payroll Viewer")
        )["id"]
    )
    db_session.add(UserRole(user_id=employee.id, role_id=role_id, assigned_by_user_id=actor.id))
    db_session.commit()

    result = role_service.update_role(
        db_session, actor.id, role_id, RoleUpdate(status="inactive")
    )
    stored = db_session.get(Role, role_id)
    assert result["status"] == "inactive"
    assert stored is not None
    assert stored.is_deleted is False
    assert stored.is_active is False
    assert stored.updated_by == actor.id
    assert db_session.scalar(
        select(UserRole.id).where(UserRole.user_id == employee.id, UserRole.role_id == role_id)
    ) is not None
    listed = role_service.list_roles(
        db_session, search=None, page=1, page_size=10
    )["items"]
    assert listed[0]["status"] == "inactive"
    assert role_service.get_role(db_session, role_id)["status"] == "inactive"
    replacement = role_service.create_role(
        db_session, actor.id, RoleCreate(name="Payroll Viewer")
    )
    assert replacement["role_code"] == "PAYROLL_VIEWER_2"
    reactivated = role_service.update_role(
        db_session, actor.id, role_id, RoleUpdate(status="active")
    )
    assert reactivated["status"] == "active"


def test_super_admin_cannot_be_deactivated(db_session: Session) -> None:
    actor = _actor(db_session)
    super_admin_role = Role(
        role_code="SUPER_ADMIN",
        role_name="Super Admin",
        is_system_role=True,
        is_active=True,
    )
    db_session.add(super_admin_role)
    db_session.commit()
    with pytest.raises(HTTPException) as error:
        role_service.update_role(
            db_session, actor.id, super_admin_role.id, RoleUpdate(status="inactive")
        )
    assert error.value.status_code == 409
    assert db_session.get(Role, super_admin_role.id).is_deleted is False


def test_deleted_role_does_not_grant_roles_or_permissions() -> None:
    deleted_role = SimpleNamespace(
        role_code="SUPER_ADMIN",
        is_active=True,
        is_deleted=True,
        permission_assignments=[
            SimpleNamespace(
                permission=SimpleNamespace(permission_code="roles.manage")
            )
        ],
    )
    user = SimpleNamespace(
        role_assignments=[SimpleNamespace(role=deleted_role)]
    )
    assert _role_codes(user) == set()
    assert _permission_codes(user) == set()

    active_role = SimpleNamespace(
        role_code="HR",
        is_active=True,
        is_deleted=False,
        permissions=["UserMgmt"],
        permission_assignments=[
            SimpleNamespace(
                permission=SimpleNamespace(permission_code="legacy-table-key")
            )
        ],
    )
    active_user = SimpleNamespace(
        role_assignments=[SimpleNamespace(role=active_role)]
    )
    assert _permission_codes(active_user) == {"UserMgmt"}


def test_deactivated_roles_cannot_be_assigned(db_session: Session) -> None:
    actor = _actor(db_session)
    role_id = UUID(
        role_service.create_role(
            db_session, actor.id, RoleCreate(name="Old Role")
        )["id"]
    )
    role_service.update_role(
        db_session, actor.id, role_id, RoleUpdate(status="inactive")
    )

    class FakeSession:
        def __init__(self) -> None:
            self.statements = []

        def scalar(self, statement):
            self.statements.append(statement)
            return SimpleNamespace(id=uuid4()) if len(self.statements) < 3 else None

    fake_db = FakeSession()
    with pytest.raises(HTTPException) as error:
        employee_service._resolve_masters(
            fake_db, actor, uuid4(), uuid4(), uuid4(), role_id
        )
    assert error.value.status_code == 422
    role_query = str(fake_db.statements[-1])
    assert "roles.is_deleted" in role_query


def test_role_permission_update_preserves_omitted_and_accepts_empty(db_session: Session) -> None:
    actor = _actor(db_session)
    initial = ["KeyCase", "leaverequest"]
    role_id = UUID(
        role_service.create_role(
            db_session, actor.id, RoleCreate(name="Permission Owner", permissions=initial)
        )["id"]
    )
    unchanged = role_service.update_role(
        db_session, actor.id, role_id, RoleUpdate(description="Updated only")
    )
    assert unchanged["permissions"] == initial

    replacement = ["DifferentKey", "leaverequest"]
    changed = role_service.update_role(
        db_session, actor.id, role_id, RoleUpdate(permissions=replacement)
    )
    assert changed["permissions"] == replacement
    cleared = role_service.update_role(
        db_session, actor.id, role_id, RoleUpdate(permissions=[])
    )
    assert cleared["permissions"] == []


def test_role_routes_require_super_admin_and_reject_audit_input(
    db_session: Session,
) -> None:
    with pytest.raises(ValidationError):
        RoleCreate(name="Auditor", created_by=str(uuid4()))

    regular_user = SimpleNamespace(
        id=uuid4(),
        role_assignments=[
            SimpleNamespace(
                role=SimpleNamespace(
                    role_code="HR", is_active=True, is_deleted=False
                )
            )
        ],
    )
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: regular_user
    try:
        with TestClient(app) as client:
            assert client.get("/api/v1/roles").status_code == 403
            assert client.post("/api/v1/roles", json={"name": "Auditor"}).status_code == 403
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    with TestClient(app) as client:
        unauthenticated = client.get("/api/v1/roles")
    assert unauthenticated.status_code == 401


def test_role_api_create_list_details_update_and_change_status(db_session: Session) -> None:
    actor = SimpleNamespace(
        id=uuid4(),
        role_assignments=[
            SimpleNamespace(
                role=SimpleNamespace(
                    role_code="SUPER_ADMIN", is_active=True, is_deleted=False
                )
            )
        ],
    )
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: actor
    try:
        with TestClient(app) as client:
            created = client.post(
                "/api/v1/roles",
                json={
                    "name": "API Manager",
                    "description": "HR",
                    "permissions": ["usermgmt", "leavemgmt"],
                    "status": "active",
                },
            )
            assert created.status_code == 201
            role_id = created.json()["data"]["id"]
            assert created.json()["data"]["name"] == "API Manager"
            assert created.json()["data"]["permissions"] == ["usermgmt", "leavemgmt"]

            listed = client.get("/api/v1/roles?search=api&page=1&page_size=5")
            assert listed.status_code == 200
            assert len(listed.json()["data"]["items"]) == 1
            assert listed.json()["data"]["items"][0]["permissions"] == [
                "usermgmt",
                "leavemgmt",
            ]
            assert client.get(f"/api/v1/roles/{role_id}").status_code == 200
            details = client.get(f"/api/v1/roles/{role_id}").json()["data"]
            assert details["permissions"] == ["usermgmt", "leavemgmt"]

            updated = client.put(
                f"/api/v1/roles/{role_id}", json={"description": "Updated"}
            )
            assert updated.status_code == 200
            assert updated.json()["data"]["description"] == "Updated"
            assert updated.json()["data"]["permissions"] == ["usermgmt", "leavemgmt"]

            cleared = client.put(
                f"/api/v1/roles/{role_id}", json={"permissions": []}
            )
            assert cleared.status_code == 200
            assert cleared.json()["data"]["permissions"] == []

            deactivated = client.put(
                f"/api/v1/roles/{role_id}", json={"status": "inactive"}
            )
            assert deactivated.status_code == 200
            assert deactivated.json()["data"]["status"] == "inactive"
            assert deactivated.json()["data"]["is_deleted"] is False
            listed = client.get("/api/v1/roles?search=api")
            assert listed.json()["data"]["items"][0]["status"] == "inactive"
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


def test_login_bundle_merges_role_json_permissions_and_preserves_response_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_role = SimpleNamespace(
        id=uuid4(),
        role_code="HR",
        role_name="HR Manager",
        is_active=True,
        is_deleted=False,
        permissions=["usermgmt", "LeaveMgmt"],
    )
    second_role = SimpleNamespace(
        id=uuid4(),
        role_code="RECRUITER",
        role_name="Recruiter",
        is_active=True,
        is_deleted=False,
        permissions=["LeaveMgmt", "recruitment", "usermgmt"],
    )
    inactive_role = SimpleNamespace(
        id=uuid4(),
        role_code="INACTIVE",
        role_name="Inactive",
        is_active=False,
        is_deleted=False,
        permissions=["inactive-key"],
    )
    deleted_role = SimpleNamespace(
        id=uuid4(),
        role_code="DELETED",
        role_name="Deleted",
        is_active=True,
        is_deleted=True,
        permissions=["deleted-key"],
    )
    user = SimpleNamespace(
        id=uuid4(),
        email="login@example.com",
        first_name="Lee",
        last_name="User",
        role_assignments=[
            SimpleNamespace(role=role)
            for role in (first_role, second_role, inactive_role, deleted_role)
        ],
    )

    class FakeSession:
        added = None

        def add(self, row):
            self.added = row

    monkeypatch.setattr(auth_service, "create_access_token", lambda *_args: ("access", 900))
    monkeypatch.setattr(auth_service, "new_opaque_token", lambda: "refresh-token")
    monkeypatch.setattr(auth_service, "hash_token", lambda value: f"hash:{value}")
    result = auth_service._issue_bundle(FakeSession(), user)

    expected = ["usermgmt", "LeaveMgmt", "recruitment"]
    assert result["access_token"] == "access"
    assert result["refresh_token"] == "refresh-token"
    assert result["user"]["permissions"] == expected
    assert result["permissions"] == expected
    assert TokenResponse.model_validate(result).permissions == expected
    assert result["user"]["roles"] == [
        {"id": str(first_role.id), "name": "HR Manager", "code": "HR"},
        {"id": str(second_role.id), "name": "Recruiter", "code": "RECRUITER"},
    ]
    assert "permission_assignments" not in auth_service._permissions_for_roles.__code__.co_names


def test_login_bundle_returns_empty_permissions_without_active_roles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = SimpleNamespace(
        id=uuid4(),
        email="norole@example.com",
        first_name="No",
        last_name="Role",
        role_assignments=[],
    )

    class FakeSession:
        def add(self, _row):
            pass

    monkeypatch.setattr(auth_service, "create_access_token", lambda *_args: ("access", 900))
    monkeypatch.setattr(auth_service, "new_opaque_token", lambda: "refresh-token")
    monkeypatch.setattr(auth_service, "hash_token", lambda value: f"hash:{value}")
    result = auth_service._issue_bundle(FakeSession(), user)
    assert result["permissions"] == []
