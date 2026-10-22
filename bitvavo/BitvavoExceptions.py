"""Error definitions."""

from __future__ import annotations

from typing import Any

# Bitvavo errorCodes (all returned with HTTP 403) that mean the API key, secret,
# signature, key permissions or account state prevent the call.
# https://docs.bitvavo.com/docs/errors/
AUTH_ERROR_CODES = frozenset(range(300, 323)) | frozenset(range(511, 515))
# 105: REST rate limit exceeded (temporary ban), 112: too many websocket messages
RATE_LIMIT_ERROR_CODES = frozenset({105, 112})


class BitvavoException(Exception):
    """Raised when an API error occurs.

    ``status_code`` is the HTTP status (``None`` for connection errors) and
    ``message`` the (decoded) response body. ``error_code``/``error`` hold the
    Bitvavo ``errorCode``/``error`` fields when the body contains them.
    """

    def __init__(self, status_code: int | None, message: Any) -> None:
        """Initialize."""
        super().__init__(status_code, message)
        self.status_code = status_code
        self.message = message
        self.error_code: int | None = None
        self.error: str | None = None
        if isinstance(message, dict):
            code = message.get("errorCode")
            self.error_code = code if isinstance(code, int) else None
            self.error = message.get("error")

    def __str__(self) -> str:  # pragma: no cover
        return f"Error(code={self.status_code}): {self.message}"


class BitvavoAuthError(BitvavoException):
    """Raised when the API key/secret is invalid or lacks permissions."""


class BitvavoRateLimitError(BitvavoException):
    """Raised when the rate limit is exceeded or the client is temporarily banned."""


class BitvavoConnectionError(BitvavoException):
    """Raised when the API cannot be reached or a request times out."""

    def __init__(self, message: Any) -> None:
        """Initialize."""
        super().__init__(None, message)


def exception_for_response(status_code: int, body: Any) -> BitvavoException:
    """Return the most specific exception for an error response."""
    exc = BitvavoException(status_code, body)
    if exc.error_code in RATE_LIMIT_ERROR_CODES or status_code == 429:
        return BitvavoRateLimitError(status_code, body)
    if status_code in (401, 403) or exc.error_code in AUTH_ERROR_CODES:
        return BitvavoAuthError(status_code, body)
    return exc
