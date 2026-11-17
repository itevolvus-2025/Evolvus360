"""Shared security response headers for normal and exception responses."""


def security_headers(*, is_https: bool, enable_hsts: bool) -> dict[str, str]:
    headers = {
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "X-Frame-Options": "DENY",
    }
    if is_https and enable_hsts:
        headers["Strict-Transport-Security"] = "max-age=31536000"
    return headers
