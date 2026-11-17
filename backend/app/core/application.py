"""FastAPI application type with outer request and CORS response processing."""

from typing import Any

from fastapi import FastAPI
from starlette.types import ASGIApp

from app.core.config import Settings
from app.core.cors import wrap_cors
from app.core.middleware import RequestProcessingMiddleware


class EvolvusFastAPI(FastAPI):
    """Keep tracking and CORS outside FastAPI's server-error response layer."""

    def __init__(self, *args: Any, settings: Settings, **kwargs: Any) -> None:
        self._evolvus_settings = settings
        super().__init__(*args, **kwargs)

    def build_middleware_stack(self) -> ASGIApp:
        application = super().build_middleware_stack()
        application = wrap_cors(application, self._evolvus_settings)
        return RequestProcessingMiddleware(
            application,
            enable_hsts=self._evolvus_settings.enable_hsts,
        )
