"""Normalize endpoint JSON responses to the shared statusCode envelope."""

import json
from collections.abc import Callable
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from fastapi.routing import APIRoute

from app.utils.responses import error_response, success_response


class ResponseContractRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Any]:
        original = super().get_route_handler()

        async def handler(request: Request) -> Response:
            response = await original(request)
            if not isinstance(response, JSONResponse):
                return response
            try:
                content = json.loads(response.body)
            except (TypeError, ValueError):
                return response
            code = response.status_code
            if isinstance(content, dict) and {"statusCode", "message", "data"} <= set(
                content
            ):
                content["statusCode"] = code
            elif code >= 500:
                content = error_response("A service operation failed", code)
            elif code >= 400:
                content = error_response("Request failed", code)
            else:
                content = success_response("Operation successful", content, code)
            return JSONResponse(content=content, status_code=code)

        return handler
