"""Helpers for the Evolvus360 JSON response contract."""

from typing import Any

from fastapi.responses import JSONResponse


def api_json_response(payload: dict[str, Any]) -> JSONResponse:
    """Build an HTTP response whose status matches the JSON statusCode field."""
    status_code = payload.get("statusCode")
    if (
        type(status_code) is not int
        or not 200 <= status_code <= 599
        or status_code in {204, 304}
    ):
        raise ValueError("Response payload requires a valid integer statusCode")
    return JSONResponse(status_code=status_code, content=payload)


def success_response(
    message: str,
    data: Any = None,
    status_code: int = 200,
) -> dict[str, Any]:
    return {"statusCode": status_code, "message": message, "data": data}


def error_response(message: str, status_code: int) -> dict[str, Any]:
    return {"statusCode": status_code, "message": message, "data": None}


def paginated_response(
    message: str,
    data: list[Any],
    page: int,
    size: int,
    total: int,
    status_code: int = 200,
) -> dict[str, Any]:
    if page < 1 or size < 1 or total < 0:
        raise ValueError("page and size must be positive; total cannot be negative")
    return {
        "statusCode": status_code,
        "message": message,
        "page": page,
        "size": size,
        "total": total,
        "data": data,
    }
