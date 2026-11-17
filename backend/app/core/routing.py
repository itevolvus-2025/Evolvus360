"""FastAPI route adapter that normalizes JSON responses exactly once."""

import json
from collections.abc import Callable
from typing import Any

from fastapi import Request
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.routing import APIRoute

from app.utils.responses import error_response, success_response


def _normalized_json_response(response: Response) -> Response:
    if isinstance(response, (FileResponse, StreamingResponse)):
        return response
    media_type = response.media_type or ""
    if media_type != "application/json" and not media_type.endswith("+json"):
        return response
    body = getattr(response, "body", None)
    if body is None:
        return response
    try:
        content = json.loads(body)
    except (TypeError, ValueError):
        return response

    status_code = response.status_code
    if (
        isinstance(content, dict)
        and isinstance(content.get("message"), str)
        and "data" in content
        and type(content.get("statusCode")) is int
    ):
        if status_code >= 500:
            content = error_response("An internal server error occurred", status_code)
        else:
            if content["statusCode"] == status_code:
                return response
            content["statusCode"] = status_code
    elif status_code >= 500:
        content = error_response("An internal server error occurred", status_code)
    elif status_code >= 400:
        content = error_response("Request failed", status_code)
    else:
        content = success_response("Operation successful", content, status_code)

    normalized = JSONResponse(
        content=content,
        status_code=status_code,
        background=response.background,
    )
    preserved_headers = [
        (name, value)
        for name, value in response.raw_headers
        if name.lower() not in {b"content-length", b"content-type"}
    ]
    normalized.raw_headers = preserved_headers + normalized.raw_headers
    return normalized


class ResponseContractRoute(APIRoute):
    """Normalize ordinary JSON responses while leaving streams and files intact."""

    def get_route_handler(self) -> Callable[[Request], Any]:
        original_handler = super().get_route_handler()

        async def contract_handler(request: Request) -> Response:
            response = await original_handler(request)
            if not isinstance(response, (FileResponse, StreamingResponse)):
                return _normalized_json_response(response)
            return response

        return contract_handler
