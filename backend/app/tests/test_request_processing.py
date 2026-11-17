import asyncio
import json
import logging
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.application import EvolvusFastAPI
from app.core.config import Settings
from app.core.cors import configure_cors
from app.core.exceptions import register_exception_handlers
from app.core.logging import JsonFormatter, current_request_id
from app.core.middleware import RequestProcessingMiddleware
from app.core.routing import ResponseContractRoute
from app.database.session import DatabaseNotConfiguredError, get_db
from app.main import app as main_app
from app.main import readiness_check
from app.utils.responses import api_json_response, success_response


def contract_app() -> FastAPI:
    app = FastAPI()
    app.router.route_class = ResponseContractRoute
    return app


def test_request_id_is_generated_and_response_headers_are_added() -> None:
    response = TestClient(main_app).get("/health")

    request_id = response.headers["x-request-id"]
    assert str(uuid.UUID(request_id)) == request_id
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["x-frame-options"] == "DENY"


def test_valid_existing_request_id_is_preserved() -> None:
    request_id = str(uuid.uuid4())
    response = TestClient(main_app).get("/health", headers={"X-Request-ID": request_id})

    assert response.headers["x-request-id"] == request_id


def test_invalid_or_oversized_request_id_is_replaced() -> None:
    client = TestClient(main_app)
    for invalid_id in ("not-a-uuid", "a" * 200):
        response = client.get("/health", headers={"X-Request-ID": invalid_id})
        generated_id = response.headers["x-request-id"]
        assert generated_id != invalid_id
        assert str(uuid.UUID(generated_id)) == generated_id


def test_request_logging_contains_safe_metadata_and_duration(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="app.core.middleware"):
        response = TestClient(main_app).get(
            "/health?token=query-secret",
            headers={"Authorization": "Bearer access-secret"},
        )

    record = next(
        record for record in caplog.records if record.name == "app.core.middleware"
    )
    assert record.request_id == response.headers["x-request-id"]
    assert record.http_method == "GET"
    assert record.path == "/health"
    assert record.status_code == 200
    assert record.duration_ms >= 0
    assert record.client_ip

    structured = json.loads(JsonFormatter().format(record))
    assert structured["timestamp"].endswith("+00:00")
    assert "query-secret" not in json.dumps(structured)
    assert "access-secret" not in json.dumps(structured)


def test_cors_allows_configured_frontend_origin_and_request_id_header() -> None:
    response = TestClient(main_app).options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "x-request-id",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "x-request-id" in response.headers["access-control-allow-headers"].lower()
    assert response.headers["x-request-id"]


def test_cors_rejects_wildcard_origins_with_credentials() -> None:
    with pytest.raises(ValueError, match="Wildcard CORS origins"):
        Settings(
            _env_file=None,
            cors_allowed_origins="*",
            cors_allow_credentials=True,
        )


def test_cors_uses_configured_origins_and_credentials() -> None:
    settings = Settings(
        _env_file=None,
        cors_allowed_origins="https://web.example,https://admin.example",
        cors_allowed_methods="GET,POST",
        cors_allowed_headers="Authorization,Content-Type",
        cors_allow_credentials=True,
    )
    app = FastAPI()
    configure_cors(app, settings)

    @app.get("/resource")
    def resource() -> dict[str, bool]:
        return {"ok": True}

    response = TestClient(app).options(
        "/resource",
        headers={
            "Origin": "https://admin.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://admin.example"
    assert response.headers["access-control-allow-credentials"] == "true"
    assert response.headers["access-control-allow-methods"] == "GET, POST"


def test_hsts_is_only_added_for_https_when_enabled() -> None:
    app = contract_app()
    app.add_middleware(RequestProcessingMiddleware, enable_hsts=True)

    @app.get("/secure")
    def secure() -> JSONResponse:
        return api_json_response(success_response("ok", {}))

    http_response = TestClient(app, base_url="http://testserver").get("/secure")
    https_response = TestClient(app, base_url="https://testserver").get("/secure")

    assert "strict-transport-security" not in http_response.headers
    assert https_response.headers["strict-transport-security"] == "max-age=31536000"


def test_streaming_response_body_is_not_wrapped_or_buffered() -> None:
    app = contract_app()
    app.add_middleware(RequestProcessingMiddleware)

    @app.get("/stream")
    def stream() -> StreamingResponse:
        return StreamingResponse(
            iter([b"part-one", b"part-two"]), media_type="text/plain"
        )

    response = TestClient(app).get("/stream")

    assert response.content == b"part-onepart-two"
    assert response.headers["content-type"].startswith("text/plain")
    assert response.headers["x-request-id"]


def test_file_response_is_not_wrapped() -> None:
    app = contract_app()
    app.add_middleware(RequestProcessingMiddleware)

    @app.get("/download")
    def download() -> FileResponse:
        return FileResponse(Path(__file__), media_type="text/plain")

    response = TestClient(app).get("/download")

    assert response.content == Path(__file__).read_bytes()
    assert response.headers["x-request-id"]


def test_error_response_contract_status_and_request_id_header() -> None:
    response = TestClient(main_app).get("/route-that-does-not-exist")

    assert response.status_code == response.json()["statusCode"] == 404
    assert response.json() == {
        "statusCode": 404,
        "message": "Not Found",
        "data": None,
    }
    assert response.headers["x-request-id"]


def test_unexpected_error_also_has_request_id_and_safe_headers() -> None:
    app = contract_app()
    register_exception_handlers(app)
    app.add_middleware(RequestProcessingMiddleware)

    @app.get("/failure")
    def failure() -> None:
        raise RuntimeError("authorization=very-secret")

    response = TestClient(app, raise_server_exceptions=False).get("/failure")

    assert response.status_code == response.json()["statusCode"] == 500
    assert response.headers["x-request-id"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "very-secret" not in response.text


def test_cors_and_request_tracking_wrap_generic_server_errors() -> None:
    settings = Settings(
        _env_file=None,
        cors_allowed_origins="https://frontend.example",
    )
    app = EvolvusFastAPI(settings=settings)
    register_exception_handlers(app)
    app.router.route_class = ResponseContractRoute

    @app.get("/failure")
    def failure() -> None:
        raise RuntimeError("internal failure")

    response = TestClient(app, raise_server_exceptions=False).get(
        "/failure", headers={"Origin": "https://frontend.example"}
    )

    assert response.status_code == response.json()["statusCode"] == 500
    assert response.headers["access-control-allow-origin"] == "https://frontend.example"
    assert response.headers["x-request-id"]
    assert response.headers["x-frame-options"] == "DENY"


def test_json_response_is_wrapped_once_and_status_code_is_aligned() -> None:
    app = contract_app()

    @app.get("/raw")
    def raw() -> dict[str, str]:
        return {"value": "payload"}

    @app.get("/already-wrapped")
    def already_wrapped() -> JSONResponse:
        return api_json_response(success_response("ok", {"value": "payload"}))

    @app.get("/mismatched")
    def mismatched() -> JSONResponse:
        return JSONResponse(
            status_code=201,
            content={"statusCode": 200, "message": "created", "data": {}},
        )

    @app.get("/sensitive-error")
    def sensitive_error() -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "statusCode": 500,
                "message": "database password=hidden",
                "data": {"sql": "SELECT secret"},
            },
        )

    client = TestClient(app)
    raw_response = client.get("/raw")
    wrapped_response = client.get("/already-wrapped")
    mismatched_response = client.get("/mismatched")
    error_response = client.get("/sensitive-error")

    assert raw_response.json() == {
        "statusCode": 200,
        "message": "Operation successful",
        "data": {"value": "payload"},
    }
    assert wrapped_response.json() == {
        "statusCode": 200,
        "message": "ok",
        "data": {"value": "payload"},
    }
    assert mismatched_response.status_code == mismatched_response.json()["statusCode"]
    assert mismatched_response.json()["statusCode"] == 201
    assert error_response.status_code == error_response.json()["statusCode"] == 500
    assert error_response.json() == {
        "statusCode": 500,
        "message": "An internal server error occurred",
        "data": None,
    }


def test_concurrent_requests_keep_request_context_isolated() -> None:
    app = contract_app()
    app.add_middleware(RequestProcessingMiddleware)

    @app.get("/context")
    async def context(request: Request) -> JSONResponse:
        before_wait = current_request_id()
        await asyncio.sleep(0.005)
        after_wait = current_request_id()
        return api_json_response(
            success_response(
                "context",
                {
                    "before": before_wait,
                    "after": after_wait,
                    "state": request.state.request_id,
                },
            )
        )

    async def send_requests() -> list[tuple[str, dict[str, str | None]]]:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            responses = await asyncio.gather(
                *(client.get("/context") for _ in range(16))
            )
        return [
            (response.headers["x-request-id"], response.json()["data"])
            for response in responses
        ]

    results = asyncio.run(send_requests())
    ids = [request_id for request_id, _ in results]
    assert len(ids) == len(set(ids)) == 16
    for request_id, data in results:
        assert data == {
            "before": request_id,
            "after": request_id,
            "state": request_id,
        }
    assert current_request_id() is None


def test_request_context_is_available_to_sync_services() -> None:
    app = contract_app()
    app.add_middleware(RequestProcessingMiddleware)

    @app.get("/sync-context")
    def sync_context() -> dict[str, str | None]:
        return {"request_id": current_request_id()}

    response = TestClient(app).get("/sync-context")

    assert response.json()["data"]["request_id"] == response.headers["x-request-id"]


def test_health_endpoint_does_not_require_database() -> None:
    response = TestClient(main_app).get("/health")
    assert response.status_code == response.json()["statusCode"] == 200
    assert response.json()["data"] == {"status": "healthy"}


def test_readiness_endpoint_checks_database_connectivity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    factory = sessionmaker(bind=engine, class_=Session)

    def test_database_session():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setitem(main_app.dependency_overrides, get_db, test_database_session)
    try:
        response = TestClient(main_app).get("/ready")
    finally:
        engine.dispose()

    assert response.status_code == response.json()["statusCode"] == 200
    assert response.json()["data"] == {"status": "ready"}


def test_postgres_readiness_applies_a_statement_timeout() -> None:
    class PostgresLikeSession:
        def __init__(self) -> None:
            self.statements: list[tuple[str, dict[str, str] | None]] = []

        def get_bind(self):
            return SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))

        def execute(self, statement, parameters=None):
            self.statements.append((str(statement), parameters))

    db = PostgresLikeSession()
    response = readiness_check(db)  # type: ignore[arg-type]

    assert response.status_code == 200
    assert "set_config('statement_timeout'" in db.statements[0][0]
    assert db.statements[0][1] == {"timeout": "3000ms"}
    assert db.statements[1][0] == "SELECT 1"


def test_readiness_returns_sanitized_unavailable_when_database_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_database():
        raise DatabaseNotConfiguredError("internal database URL detail")

    monkeypatch.setitem(main_app.dependency_overrides, get_db, missing_database)
    response = TestClient(main_app).get("/ready")

    assert response.status_code == response.json()["statusCode"] == 503
    assert response.json() == {
        "statusCode": 503,
        "message": "A required service is temporarily unavailable",
        "data": None,
    }
    assert "internal database URL detail" not in response.text
