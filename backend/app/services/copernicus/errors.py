class CopernicusError(Exception):
    """Base class for Copernicus Data Space / Sentinel Hub failures."""


class CopernicusNotConfigured(CopernicusError):
    """COPERNICUS_CLIENT_ID / COPERNICUS_CLIENT_SECRET are not set."""


class CopernicusAuthError(CopernicusError):
    """The identity service rejected the client credentials."""


class CopernicusUnavailable(CopernicusError):
    """Network failure or timeout talking to Copernicus Data Space."""


class CopernicusRateLimited(CopernicusError):
    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class CopernicusInvalidResponse(CopernicusError):
    """Sentinel Hub answered 2xx but the body is empty or not the expected format."""


class CopernicusRequestError(CopernicusError):
    """Sentinel Hub returned an error response for a request."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(f"Sentinel Hub error {status_code}: {message}")
        self.status_code = status_code
        self.message = message
