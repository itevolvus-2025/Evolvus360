"""Environment-driven CORS setup for FastAPI applications."""

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp

from app.core.config import Settings


def cors_options(settings: Settings) -> dict[str, object]:
    return {
        "allow_origins": settings.cors_origins,
        "allow_methods": settings.cors_methods,
        "allow_headers": settings.cors_headers,
        "allow_credentials": settings.cors_allow_credentials,
        "expose_headers": ["X-Request-ID"],
    }


def configure_cors(app: FastAPI, settings: Settings) -> None:
    app.add_middleware(CORSMiddleware, **cors_options(settings))


def wrap_cors(app: ASGIApp, settings: Settings) -> ASGIApp:
    return CORSMiddleware(app, **cors_options(settings))
