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
    detail = exc.detail
    errors = detail.get("errors") if isinstance(detail, dict) else None
    message = (
        detail.get("message", "Request failed")
        if isinstance(detail, dict)
        else detail if isinstance(detail, str) else "Request failed"
    )
    if exc.status_code >= 500:
        message = "An internal server error occurred"
    content = _error_body(message, exc.status_code)
    if isinstance(errors, dict):
        content["errors"] = errors
    return JSONResponse(
        status_code=exc.status_code,
        content=content,
        headers={**_response_headers(request), **(exc.headers or {})},
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.info("Request validation failed", extra={"request_id": _request_id(request)})
    status_code = 422
    errors: dict[str, str] = {}
    for error in exc.errors():
        field = next(
            (part for part in reversed(error.get("loc", ())) if isinstance(part, str)),
            "request",
        )
        message = str(error.get("msg", "Invalid value"))
        if message.startswith("Value error, "):
            message = message.removeprefix("Value error, ")
        error_type = str(error.get("type", ""))
        if field in {"company_email", "personal_email"}:
            label = "company" if field == "company_email" else "personal"
            message = f"Please enter a valid {label} email address."
        elif field in {"department_id", "role_id", "entity_id"} and error_type == "missing":
            label = field.removesuffix("_id").capitalize()
            message = f"Please select a {label.lower()}."
        elif field in {"department_id", "role_id", "entity_id"} and error_type.startswith("uuid"):
            label = field.removesuffix("_id").capitalize()
            message = f"Invalid {label.lower()} ID. Please provide a valid UUID."
        elif field == "pf_applicable" and error_type in {"bool_type", "bool_parsing"}:
            message = "PF applicable must be a boolean value (true or false)."
        elif field in {"joining_date", "start_date", "end_date"} and error_type != "value_error":
            label = field.replace("_", " ").capitalize()
            message = (
                f"Invalid {label.lower()}. Please provide a valid date "
                "in YYYY-MM-DD format."
            )
        errors[field] = message
    return JSONResponse(
        status_code=status_code,
        content={
            **_error_body(
                "Validation failed. Please correct the highlighted fields.",
                status_code,
            ),
            "errors": errors,
        },
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
