class ApplicationError(Exception):
    """Base error for domain and application failures."""

    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class IntegrationError(ApplicationError):
    """Raised when an external provider fails or returns unexpected data."""


class AuthenticationError(ApplicationError):
    """Raised when authentication with IG fails."""

    def __init__(self, detail: str = "Authentication failed") -> None:
        super().__init__(detail=detail, status_code=401)


class NotAuthenticatedError(ApplicationError):
    """Raised when an authenticated session is required."""

    def __init__(self, detail: str = "No active session") -> None:
        super().__init__(detail=detail, status_code=401)


class ExternalServiceError(IntegrationError):
    """Raised when an external provider is unavailable or times out."""

    def __init__(self, detail: str = "External service unavailable") -> None:
        super().__init__(detail=detail, status_code=502)
