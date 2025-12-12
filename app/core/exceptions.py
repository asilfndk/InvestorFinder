"""
Custom exceptions for the application.
Provides a hierarchy of exceptions for different error scenarios.
"""

from typing import Optional, Dict, Any


class AppException(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        message: str,
        code: str = "UNKNOWN_ERROR",
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        self.original_error = original_error
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details
            }
        }


class ConfigurationError(AppException):
    """Raised when there's a configuration issue."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR",
            details=details
        )


class LLMProviderError(AppException):
    """Raised when there's an error with the LLM provider."""

    def __init__(
        self,
        message: str,
        provider: str,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            code="LLM_PROVIDER_ERROR",
            details={"provider": provider, **(details or {})},
            original_error=original_error
        )


class SearchProviderError(AppException):
    """Raised when there's an error with the search provider."""

    def __init__(
        self,
        message: str,
        provider: str,
        query: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            code="SEARCH_PROVIDER_ERROR",
            details={"provider": provider, "query": query, **(details or {})},
            original_error=original_error
        )


class ScraperError(AppException):
    """Raised when there's an error with web scraping."""

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            code="SCRAPER_ERROR",
            details={"url": url, **(details or {})},
            original_error=original_error
        )


class RateLimitError(AppException):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="RATE_LIMIT_ERROR",
            details={"retry_after": retry_after, **(details or {})}
        )


class ValidationError(AppException):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details={"field": field, **(details or {})}
        )


class AuthenticationError(AppException):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            details=details
        )


class ResourceNotFoundError(AppException):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"{resource_type} with id '{resource_id}' not found",
            code="RESOURCE_NOT_FOUND",
            details={"resource_type": resource_type,
                     "resource_id": resource_id, **(details or {})}
        )
