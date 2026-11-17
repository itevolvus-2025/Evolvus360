"""Structured application logging with request-scoped correlation context."""

import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)


def current_request_id() -> str | None:
    return request_id_context.get()


class JsonFormatter(logging.Formatter):
    """Emit a compact JSON record containing only approved log fields."""

    _allowed_fields = (
        "event",
        "http_method",
        "path",
        "status_code",
        "duration_ms",
        "client_ip",
        "exception_type",
    )

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = getattr(record, "request_id", None) or current_request_id()
        if request_id:
            payload["request_id"] = request_id
        for field in self._allowed_fields:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging(log_level: str = "INFO") -> None:
    """Configure root handlers to emit structured stdout logs."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    if not root_logger.handlers:
        root_logger.addHandler(logging.StreamHandler())
    for handler in root_logger.handlers:
        handler.setFormatter(JsonFormatter())
