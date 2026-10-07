from __future__ import annotations


class WebError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def provider_code(code: str) -> str:
    return {
        "authentication": "provider_authentication_failed",
        "rate_limit": "provider_rate_limited",
        "timeout": "provider_timeout",
    }.get(code, code)
