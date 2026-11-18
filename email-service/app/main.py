"""Independent centralized email delivery API."""

import logging
import re
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes.emails import router as emails_router
from app.api.routes.health import router as health_router
from app.api.routes.templates import router as templates_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.routing import ResponseContractRoute
from app.utils.responses import error_response

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Evolvus360 Central Email Service",
    description=(
        "Independent service-to-service email delivery and template management."
    ),
    version="1.0.0",
)
app.router.route_class = ResponseContractRoute
app.include_router(health_router, prefix="/api/v1")
app.include_router(emails_router, prefix="/api/v1")
app.include_router(templates_router, prefix="/api/v1")


@app.middleware("http")
async def request_context(request: Request, call_next):
    supplied = request.headers.get("X-Request-ID", "")
    request_id = (
        supplied
        if re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", supplied)
        else str(uuid.uuid4())
    )
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
    if exc.status_code >= 500:
        detail = "Email service operation failed"
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(detail, exc.status_code),
        headers={"X-Request-ID": request.state.request_id},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    logger.info(
        "Request validation failed", extra={"request_id": request.state.request_id}
    )
    return JSONResponse(
        status_code=422,
        content=error_response("Request validation failed", 422),
        headers={"X-Request-ID": request.state.request_id},
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception):
    logger.exception(
        "Unhandled email service exception",
        extra={
            "request_id": request.state.request_id,
            "exception_type": type(exc).__name__,
        },
    )
    return JSONResponse(
        status_code=500,
        content=error_response("Email service operation failed", 500),
        headers={"X-Request-ID": request.state.request_id},
    )
