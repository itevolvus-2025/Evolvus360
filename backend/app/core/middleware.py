"""Lightweight ASGI middleware for request IDs, logging, and security headers."""

import logging
import time
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import request_id_context
from app.core.response_headers import security_headers

logger = logging.getLogger(__name__)
_REQUEST_ID_HEADER = b"x-request-id"


def _validated_request_id(scope: Scope) -> str:
    value: str | None = None
    for name, raw_value in scope.get("headers", []):
        if name.lower() == _REQUEST_ID_HEADER:
            if len(raw_value) != 36:
                break
            try:
                candidate = raw_value.decode("ascii")
                parsed = uuid.UUID(candidate)
                if str(parsed) == candidate.lower():
                    value = str(parsed)
            except (UnicodeDecodeError, ValueError, AttributeError):
                pass
            break
    return value or str(uuid.uuid4())


class RequestProcessingMiddleware:
    """Attach request context and observe response messages without buffering."""

    def __init__(self, app: ASGIApp, *, enable_hsts: bool = False) -> None:
        self.app = app
        self.enable_hsts = enable_hsts

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _validated_request_id(scope)
        scope.setdefault("state", {})["request_id"] = request_id
        context_token = request_id_context.set(request_id)
        started_at = time.perf_counter()
        status_code: int | None = None
        logged = False
        client = scope.get("client")
        client_ip = str(client[0]) if client else None

        def log_request(exception_type: str | None = None) -> None:
            nonlocal logged
            if logged:
                return
            logged = True
            logger.info(
                "http_request",
                extra={
                    "event": "http_request",
                    "request_id": request_id,
                    "http_method": scope.get("method", ""),
                    "path": scope.get("path", ""),
                    "status_code": status_code or 500,
                    "duration_ms": round((time.perf_counter() - started_at) * 1000, 3),
                    "client_ip": client_ip,
                    "exception_type": exception_type,
                },
            )

        async def send_with_request_headers(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_headers = [
                    (name, value)
                    for name, value in message.get("headers", [])
                    if name.lower()
                    not in {
                        _REQUEST_ID_HEADER,
                        b"x-content-type-options",
                        b"referrer-policy",
                        b"x-frame-options",
                        b"strict-transport-security",
                    }
                ]
                response_headers.append(
                    (_REQUEST_ID_HEADER, request_id.encode("ascii"))
                )
                generated_headers = security_headers(
                    is_https=scope.get("scheme") == "https",
                    enable_hsts=self.enable_hsts,
                )
                response_headers.extend(
                    (name.lower().encode("ascii"), value.encode("latin-1"))
                    for name, value in generated_headers.items()
                )
                message = {**message, "headers": response_headers}

            await send(message)
            if message["type"] == "http.response.body" and not message.get(
                "more_body", False
            ):
                log_request()

        try:
            await self.app(scope, receive, send_with_request_headers)
        except Exception as exc:
            if status_code is None:
                status_code = 500
            log_request(type(exc).__name__)
            raise
        finally:
            log_request()
            request_id_context.reset(context_token)
