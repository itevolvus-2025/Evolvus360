from typing import Annotated

from fastapi import Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v1.router import api_router
from app.core.application import EvolvusFastAPI
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.routing import ResponseContractRoute
from app.database.session import get_db
from app.utils.responses import api_json_response, success_response

settings = get_settings()
configure_logging(settings.log_level)

app = EvolvusFastAPI(
    title="Evolvus360 API",
    description="Centralized HRMS Backend",
    version="1.0.0",
    settings=settings,
)
app.router.route_class = ResponseContractRoute
register_exception_handlers(app)
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root() -> JSONResponse:
    return api_json_response(success_response("Evolvus360 Backend is running", {}))


@app.get("/health")
async def health_check() -> JSONResponse:
    return api_json_response(
        success_response("Application is healthy", {"status": "healthy"})
    )


@app.get("/ready")
def readiness_check(db: Annotated[Session, Depends(get_db)]) -> JSONResponse:
    if db.get_bind().dialect.name == "postgresql":
        timeout_ms = settings.db_readiness_timeout_seconds * 1000
        db.execute(
            text("SELECT set_config('statement_timeout', :timeout, true)"),
            {"timeout": f"{timeout_ms}ms"},
        )
    db.execute(text("SELECT 1"))
    return api_json_response(
        success_response("Dependencies are ready", {"status": "ready"})
    )
