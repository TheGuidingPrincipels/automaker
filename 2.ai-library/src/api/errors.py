# src/api/errors.py
"""Standardized API error responses."""

from fastapi import HTTPException, status


class APIError:
    """Helper class for standardized API error responses."""

    @staticmethod
    def not_found(resource: str, identifier: str = "") -> HTTPException:
        """Return a 404 Not Found error."""
        detail = f"{resource} not found"
        if identifier:
            detail = f"{resource} not found: {identifier}"
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )

    @staticmethod
    def bad_request(message: str) -> HTTPException:
        """Return a 400 Bad Request error."""
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    @staticmethod
    def internal_error(message: str = "Internal server error") -> HTTPException:
        """Return a 500 Internal Server Error."""
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message,
        )

    @staticmethod
    def conflict(message: str) -> HTTPException:
        """Return a 409 Conflict error."""
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=message,
        )

    @staticmethod
    def service_unavailable(message: str) -> HTTPException:
        """Return a 503 Service Unavailable error."""
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=message,
        )

    @staticmethod
    def payload_too_large(message: str) -> HTTPException:
        """Return a 413 Payload Too Large error."""
        return HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=message,
        )
