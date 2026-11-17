import ast
from collections.abc import Generator
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError, InvalidRequestError, OperationalError
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.core.exceptions import register_exception_handlers
from app.database import session as db_session
from app.database.session import RequestSession
from app.main import app as main_app
from app.utils.responses import (
    api_json_response,
    paginated_response,
    success_response,
)


class FakeSession:
    def __init__(self) -> None:
        self.rollback_calls = 0
        self.close_calls = 0
        self.commit_calls = 0

    def rollback(self) -> None:
        self.rollback_calls += 1

    def close(self) -> None:
        self.close_calls += 1

    def commit(self) -> None:
        self.commit_calls += 1


def test_success_response_has_standard_contract() -> None:
    assert success_response("Created", {"id": 1}, 201) == {
        "statusCode": 201,
        "message": "Created",
        "data": {"id": 1},
    }


def test_http_response_status_matches_json_status_code() -> None:
    app = FastAPI()
    payload = success_response("Created", {"id": 1}, status_code=201)
    app.add_api_route("/created", lambda: api_json_response(payload), methods=["GET"])

    response = TestClient(app).get("/created")
    assert response.status_code == response.json()["statusCode"] == 201


def test_http_response_rejects_invalid_status_code() -> None:
    with pytest.raises(ValueError, match="valid integer statusCode"):
        api_json_response({"statusCode": "200", "message": "bad", "data": None})


def test_application_success_routes_follow_response_contract() -> None:
    client = TestClient(main_app)
    for path in ("/", "/health"):
        response = client.get(path)
        assert response.status_code == response.json()["statusCode"] == 200
        assert set(response.json()) == {"statusCode", "message", "data"}


def test_paginated_response_has_consistent_pagination_fields() -> None:
    assert paginated_response("Fetched", [], page=2, size=25, total=51) == {
        "statusCode": 200,
        "message": "Fetched",
        "page": 2,
        "size": 25,
        "total": 51,
        "data": [],
    }


def test_http_exception_uses_standard_error_contract() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/missing")
    def missing() -> None:
        raise HTTPException(status_code=404, detail="Record not found")

    response = TestClient(app).get("/missing")
    assert response.status_code == 404
    assert response.json() == {
        "statusCode": 404,
        "message": "Record not found",
        "data": None,
    }


def test_validation_error_uses_standard_error_contract() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/items/{item_id}")
    def read_item(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    response = TestClient(app).get("/items/not-an-int")
    assert response.status_code == 422
    assert response.json() == {
        "statusCode": 422,
        "message": "Request validation failed",
        "data": None,
    }


def test_unexpected_error_does_not_leak_internal_details() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/failure")
    def failure() -> None:
        raise RuntimeError("secret database detail")

    response = TestClient(app, raise_server_exceptions=False).get("/failure")
    assert response.status_code == 500
    assert response.json() == {
        "statusCode": 500,
        "message": "An internal server error occurred",
        "data": None,
    }
    assert "secret database detail" not in response.text


def test_database_connection_error_returns_sanitized_503() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/database-failure")
    def database_failure() -> None:
        raise OperationalError(
            "connection", {}, RuntimeError("password=internal-secret")
        )

    response = TestClient(app, raise_server_exceptions=False).get("/database-failure")
    assert response.status_code == 503
    assert response.json() == {
        "statusCode": 503,
        "message": "A required service is temporarily unavailable",
        "data": None,
    }
    assert "internal-secret" not in response.text


def test_database_error_returns_standard_sanitized_500() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/database-operation-failure")
    def database_operation_failure() -> None:
        raise IntegrityError("query", {}, RuntimeError("sensitive SQL detail"))

    response = TestClient(app, raise_server_exceptions=False).get(
        "/database-operation-failure"
    )
    assert response.status_code == response.json()["statusCode"] == 500
    assert response.json() == {
        "statusCode": 500,
        "message": "A database operation failed",
        "data": None,
    }
    assert "sensitive SQL detail" not in response.text


def test_db_dependency_closes_session_after_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeSession()
    monkeypatch.setattr(db_session, "SessionLocal", lambda: fake)
    dependency: Generator = db_session.get_db()

    assert next(dependency) is fake
    with pytest.raises(StopIteration):
        next(dependency)

    assert fake.rollback_calls == 0
    assert fake.close_calls == 1
    assert fake.commit_calls == 0


def test_db_dependency_rolls_back_and_closes_after_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeSession()
    monkeypatch.setattr(db_session, "SessionLocal", lambda: fake)
    dependency: Generator = db_session.get_db()

    assert next(dependency) is fake
    with pytest.raises(RuntimeError, match="service failed"):
        dependency.throw(RuntimeError("service failed"))

    assert fake.rollback_calls == 1
    assert fake.close_calls == 1
    assert fake.commit_calls == 0


def test_db_dependency_rolls_back_real_database_transaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE rollback_check (value INTEGER)")
    factory = sessionmaker(bind=engine, class_=RequestSession)
    monkeypatch.setattr(db_session, "SessionLocal", factory)
    dependency = db_session.get_db()
    request_session = next(dependency)
    request_session.execute(text("INSERT INTO rollback_check VALUES (1)"))

    with pytest.raises(RuntimeError, match="request failed"):
        dependency.throw(RuntimeError("request failed"))

    with engine.connect() as connection:
        assert connection.scalar(text("SELECT COUNT(*) FROM rollback_check")) == 0
    engine.dispose()


def test_db_dependency_closes_even_if_rollback_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeSession()

    def fail_rollback() -> None:
        raise RuntimeError("rollback failed")

    fake.rollback = fail_rollback  # type: ignore[method-assign]
    monkeypatch.setattr(db_session, "SessionLocal", lambda: fake)
    dependency: Generator = db_session.get_db()

    assert next(dependency) is fake
    with pytest.raises(RuntimeError, match="request failed"):
        dependency.throw(RuntimeError("request failed"))

    assert fake.close_calls == 1


def test_request_session_rejects_a_second_commit() -> None:
    db = RequestSession()
    db.commit()
    with pytest.raises(InvalidRequestError, match="committed only once"):
        db.commit()
    db.close()


def test_request_session_allows_savepoints_before_service_commit() -> None:
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE savepoint_check (value INTEGER)")

    db = RequestSession(bind=engine)
    with db.begin_nested():
        db.execute(text("INSERT INTO savepoint_check VALUES (1)"))
    db.commit()

    with engine.connect() as connection:
        assert connection.scalar(text("SELECT COUNT(*) FROM savepoint_check")) == 1
    db.close()
    engine.dispose()


def test_request_session_guards_commits_from_transaction_contexts() -> None:
    engine = create_engine("sqlite:///:memory:")
    db = RequestSession(bind=engine)
    with db.begin():
        pass

    with pytest.raises(InvalidRequestError, match="committed only once"):
        db.commit()

    db.close()
    engine.dispose()


def test_db_dependency_creates_a_distinct_session_per_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sessions = [FakeSession(), FakeSession()]
    monkeypatch.setattr(db_session, "SessionLocal", lambda: sessions.pop(0))

    first_request = db_session.get_db()
    first_session = next(first_request)
    with pytest.raises(StopIteration):
        next(first_request)

    second_request = db_session.get_db()
    second_session = next(second_request)
    with pytest.raises(StopIteration):
        next(second_request)

    assert first_session is not second_session
    assert first_session.close_calls == second_session.close_calls == 1


def test_repositories_do_not_commit_transactions() -> None:
    repository_dir = Path(__file__).resolve().parents[1] / "repositories"
    violations: list[str] = []
    for source_path in repository_dir.glob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in {"commit", "begin", "begin_nested"}:
                    violations.append(f"{source_path.name}:{node.lineno}")
    assert not violations, f"Repository code must not manage transactions: {violations}"


def test_transaction_management_is_confined_to_service_layer() -> None:
    app_dir = Path(__file__).resolve().parents[1]
    violations: list[str] = []
    for source_path in app_dir.rglob("*.py"):
        relative_path = source_path.relative_to(app_dir)
        if relative_path.parts[0] in {"services", "tests"}:
            continue
        if relative_path == Path("database/session.py"):
            continue
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in {"commit", "begin", "begin_nested"}:
                    violations.append(f"{relative_path}:{node.lineno}")
    assert not violations, f"Transaction management belongs in services: {violations}"


def test_pool_settings_are_loaded_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DB_POOL_SIZE", "4")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "6")
    monkeypatch.setenv("DB_POOL_TIMEOUT", "7")
    monkeypatch.setenv("DB_POOL_RECYCLE", "8")
    monkeypatch.setenv("DB_POOL_PRE_PING", "false")

    settings = Settings(_env_file=None)

    assert settings.db_pool_size == 4
    assert settings.db_max_overflow == 6
    assert settings.db_pool_timeout == 7
    assert settings.db_pool_recycle == 8
    assert settings.db_pool_pre_ping is False


def test_engine_uses_configured_pool_and_is_reused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = SimpleNamespace(
        database_url="postgresql+psycopg://localhost/test_db",
        db_pool_size=4,
        db_max_overflow=6,
        db_pool_timeout=7,
        db_pool_recycle=8,
        db_pool_pre_ping=True,
        db_connect_timeout_seconds=3,
    )
    monkeypatch.setattr(db_session, "get_settings", lambda: settings)
    real_create_engine = db_session.create_engine
    engine_options = {}

    def capture_create_engine(url, **options):
        engine_options.update(options)
        return real_create_engine(url, **options)

    monkeypatch.setattr(db_session, "create_engine", capture_create_engine)
    db_session.get_session_factory.cache_clear()
    db_session.get_engine.cache_clear()

    try:
        engine = db_session.get_engine()
        assert db_session.get_engine() is engine
        factory = db_session.get_session_factory()
        assert db_session.get_session_factory() is factory
        assert issubclass(factory.class_, RequestSession)
        assert isinstance(factory(), RequestSession)
        assert factory.kw["autocommit"] is False
        assert engine.pool.size() == 4
        assert engine.pool._max_overflow == 6
        assert engine.pool._timeout == 7
        assert engine.pool._recycle == 8
        assert engine.pool._pre_ping is True
        assert engine_options["connect_args"]["connect_timeout"] == 3
    finally:
        db_session.get_session_factory.cache_clear()
        engine.dispose()
        db_session.get_engine.cache_clear()


def test_engine_requires_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        db_session,
        "get_settings",
        lambda: SimpleNamespace(database_url=None),
    )
    db_session.get_engine.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="DATABASE_URL must be configured"):
            db_session.get_engine()
    finally:
        db_session.get_engine.cache_clear()


def test_production_settings_require_strong_secret_and_disable_debug() -> None:
    with pytest.raises(ValueError, match="SECRET_KEY must be"):
        Settings(
            _env_file=None,
            app_env="production",
            secret_key="too-short",
            database_url="postgresql+psycopg://db-host/app",
        )

    with pytest.raises(ValueError, match="DEBUG must be disabled"):
        Settings(
            _env_file=None,
            app_env="production",
            secret_key="a-strong-random-secret-value-1234567890",
            database_url="postgresql+psycopg://db-host/app",
            debug=True,
        )


def test_production_settings_default_debug_to_false() -> None:
    settings = Settings(
        _env_file=None,
        app_env="production",
        secret_key="a-strong-random-secret-value-1234567890",
        database_url="postgresql+psycopg://db-host/app",
    )
    assert settings.debug is False


def test_settings_load_dotenv_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("DB_POOL_SIZE", raising=False)
    monkeypatch.delenv("DB_POOL_PRE_PING", raising=False)
    env_file = Path(__file__).with_name("settings_test.env")
    env_file.write_text(
        "APP_NAME=Test Evolvus\nDB_POOL_SIZE=3\nDB_POOL_PRE_PING=False\n",
        encoding="utf-8",
    )
    try:
        settings = Settings(_env_file=env_file)
    finally:
        env_file.unlink(missing_ok=True)

    assert settings.app_name == "Test Evolvus"
    assert settings.db_pool_size == 3
    assert settings.db_pool_pre_ping is False


def test_env_example_has_configuration_and_gitignore_excludes_env() -> None:
    backend_dir = Path(__file__).resolve().parents[2]
    env_example = backend_dir / ".env.example"
    gitignore = backend_dir / ".gitignore"
    keys = {
        line.split("=", maxsplit=1)[0]
        for line in env_example.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#") and "=" in line
    }

    assert {
        "APP_NAME",
        "APP_ENV",
        "DEBUG",
        "SECRET_KEY",
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "REFRESH_TOKEN_EXPIRE_DAYS",
        "DATABASE_URL",
        "DB_POOL_SIZE",
        "DB_MAX_OVERFLOW",
        "DB_POOL_TIMEOUT",
        "DB_POOL_RECYCLE",
        "DB_POOL_PRE_PING",
        "DB_CONNECT_TIMEOUT_SECONDS",
        "DB_READINESS_TIMEOUT_SECONDS",
        "CORS_ALLOWED_ORIGINS",
        "CORS_ALLOWED_METHODS",
        "CORS_ALLOWED_HEADERS",
        "CORS_ALLOW_CREDENTIALS",
        "ENABLE_HSTS",
        "FRONTEND_URL",
        "LOG_LEVEL",
    } <= keys
    assert ".env" in gitignore.read_text(encoding="utf-8").splitlines()
    assert "postgres:password" not in env_example.read_text(encoding="utf-8")
    assert "replace-with-a-secure-random-secret" not in env_example.read_text(
        encoding="utf-8"
    )
