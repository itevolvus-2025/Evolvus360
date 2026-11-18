"""Shared API response envelope."""

from typing import Any


def success_response(message: str, data: Any = None, status_code: int = 200) -> dict:
    return {"statusCode": status_code, "message": message, "data": data}


def error_response(message: str, status_code: int) -> dict:
    return {"statusCode": status_code, "message": message, "data": None}
