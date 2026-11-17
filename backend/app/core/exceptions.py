"""Central FastAPI exception handlers with safe public error messages."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.core.response_headers import security_headers
from app.database.session import DatabaseNotConfiguredError
from app.utils.responses import error_response

logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str | None:
    value = getattr(request.state, "request_id", None)
    return str(value) if value else None


def _error_body(message: str, status_code: int) -> dict[str, Any]:
    return error_response(message, status_code)


def _response_headers(request: Request) -> dict[str, str]:
    headers = security_headers(
        is_https=request.url.scheme == "https",
        enable_hsts=get_settings().enable_hsts,
    )
    request_id = _request_id(request)
    if request_id:
        headers["X-Request-ID"] = request_id
    return headers


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    if exc.status_code >= 500:
        message = "An internal server error occurred"
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(message, exc.status_code),
        headers={**_response_headers(request), **(exc.headers or {})},
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.info("Request validation failed", extra={"request_id": _request_id(request)})
    status_code = 422
    return JSONResponse(
        status_code=status_code,
        content=_error_body("Request validation failed", status_code),
        headers=_response_headers(request),
    )


async def database_unavailable_handler(
    request: Request,
    exc: OperationalError | SQLAlchemyTimeoutError | DatabaseNotConfiguredError,
) -> JSONResponse:
    logger.error(
        "Database connection is unavailable",
        extra={
            "request_id": _request_id(request),
            "exception_type": type(exc).__name__,
        },
    )
    status_code = 503
    return JSONResponse(
        status_code=status_code,
        content=_error_body(
            "A required service is temporarily unavailable", status_code
        ),
        headers=_response_headers(request),
    )


async def database_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    logger.error(
        "Database operation failed",
        extra={
            "request_id": _request_id(request),
            "exception_type": type(exc).__name__,
        },
    )
    status_code = 500
    return JSONResponse(
        status_code=status_code,
        content=_error_body("A database operation failed", status_code),
        headers=_response_headers(request),
    )


async def unexpected_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.error(
        "Unhandled application error",
        extra={
            "request_id": _request_id(request),
            "exception_type": type(exc).__name__,
        },
    )
    status_code = 500
    return JSONResponse(
        status_code=status_code,
        content=_error_body("An internal server error occurred", status_code),
        headers=_response_headers(request),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(OperationalError, database_unavailable_handler)
    app.add_exception_handler(SQLAlchemyTimeoutError, database_unavailable_handler)
    app.add_exception_handler(DatabaseNotConfiguredError, database_unavailable_handler)
    app.add_exception_handler(SQLAlchemyError, database_exception_handler)
    app.add_exception_handler(Exception, unexpected_exception_handler)
