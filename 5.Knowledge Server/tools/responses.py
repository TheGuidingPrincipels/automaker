"""
Standard response models for MCP tools.

All tool functions should use success_response() and error_response()
for consistent response structures across the codebase.

Response format:
- Success: {"success": True, "message": "...", "data": {...}}
- Error: {"success": False, "message": "...", "error": {"type": "...", "message": "...", ...}}
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class ErrorType(str, Enum):
    """Error type classifications for MCP tool responses.

    Uses lowercase snake_case for consistency.
    """

    # Validation errors (400-level)
    VALIDATION_ERROR = "validation_error"
    INVALID_INPUT = "invalid_input"
    MISSING_REQUIRED = "missing_required"

    # Not found errors (404-level)
    NOT_FOUND = "not_found"
    CONCEPT_NOT_FOUND = "concept_not_found"
    RELATIONSHIP_NOT_FOUND = "relationship_not_found"
    PATH_NOT_FOUND = "path_not_found"

    # Duplicate/conflict errors (409-level)
    ALREADY_EXISTS = "already_exists"
    DUPLICATE_RELATIONSHIP = "duplicate_relationship"

    # Database errors (500-level)
    DATABASE_ERROR = "database_error"
    NEO4J_ERROR = "neo4j_error"
    CHROMADB_ERROR = "chromadb_error"
    EMBEDDING_ERROR = "embedding_error"

    # Internal errors (500-level)
    INTERNAL_ERROR = "internal_error"
    UNEXPECTED_ERROR = "unexpected_error"
    SERVICE_UNAVAILABLE = "service_unavailable"

    # Format errors (used by confidence service)
    INVALID_FORMAT = "invalid_format"


# User-friendly error messages
ERROR_MESSAGES: Dict[ErrorType, str] = {
    ErrorType.VALIDATION_ERROR: "The provided input is invalid. Please check your data and try again.",
    ErrorType.INVALID_INPUT: "Invalid input provided. Please check the format and try again.",
    ErrorType.MISSING_REQUIRED: "Required field is missing. Please provide all required information.",

    ErrorType.NOT_FOUND: "The requested resource was not found.",
    ErrorType.CONCEPT_NOT_FOUND: "The concept you're looking for doesn't exist or has been deleted.",
    ErrorType.RELATIONSHIP_NOT_FOUND: "The relationship you're looking for doesn't exist.",
    ErrorType.PATH_NOT_FOUND: "No connection path exists between the specified concepts.",

    ErrorType.ALREADY_EXISTS: "This resource already exists.",
    ErrorType.DUPLICATE_RELATIONSHIP: "This relationship already exists between these concepts.",

    ErrorType.DATABASE_ERROR: "Unable to access the knowledge base. Please try again in a moment.",
    ErrorType.NEO4J_ERROR: "Knowledge graph temporarily unavailable. Please try again.",
    ErrorType.CHROMADB_ERROR: "Vector search temporarily unavailable. Please try again.",
    ErrorType.EMBEDDING_ERROR: "Unable to generate semantic embedding. Please try again.",

    ErrorType.INTERNAL_ERROR: "An unexpected error occurred. Please try again.",
    ErrorType.UNEXPECTED_ERROR: "An unexpected error occurred. Please try again.",
    ErrorType.SERVICE_UNAVAILABLE: "Required service not initialized. MCP server may still be starting up.",

    ErrorType.INVALID_FORMAT: "The data format is invalid.",
}


@dataclass
class ErrorDetail:
    """Structured error information."""

    type: ErrorType
    message: str
    field: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class ToolResponse:
    """Standard response for all tool functions.

    Success response:
        ToolResponse(success=True, message="Created", data={"concept_id": "abc"})

    Error response:
        ToolResponse(
            success=False,
            message="Validation failed",
            error=ErrorDetail(type=ErrorType.VALIDATION_ERROR, message="Name required")
        )
    """

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[ErrorDetail] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for MCP response."""
        result: Dict[str, Any] = {
            "success": self.success,
            "message": self.message,
        }

        if self.data is not None:
            result["data"] = self.data

        if self.error is not None:
            result["error"] = {
                "type": self.error.type.value,
                "message": self.error.message,
            }
            if self.error.field is not None:
                result["error"]["field"] = self.error.field
            if self.error.details is not None:
                result["error"]["details"] = self.error.details

        return result


def success_response(message: str, **data: Any) -> Dict[str, Any]:
    """Create a success response dict.

    Args:
        message: Brief success message (e.g., "Created", "Updated", "Found")
        **data: Resource-specific data fields (wrapped in "data" key)

    Returns:
        Standardized success response:
        {"success": True, "message": "...", "data": {...}}

    Example:
        >>> success_response("Concept created", concept_id="abc-123")
        {"success": True, "message": "Concept created", "data": {"concept_id": "abc-123"}}
    """
    return ToolResponse(
        success=True,
        message=message,
        data=data if data else None
    ).to_dict()


def error_response(
    error_type: ErrorType,
    message: str,
    field: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    user_friendly: bool = True
) -> Dict[str, Any]:
    """Create an error response dict.

    Args:
        error_type: The type of error (from ErrorType enum)
        message: Technical error message
        field: Optional field name that caused the error
        details: Optional additional error details
        user_friendly: If True, use user-friendly message for response message

    Returns:
        Standardized error response:
        {"success": False, "message": "...", "error": {"type": "...", "message": "..."}}
    """
    response_message = ERROR_MESSAGES.get(error_type, message) if user_friendly else message

    return ToolResponse(
        success=False,
        message=response_message,
        error=ErrorDetail(
            type=error_type,
            message=message,
            field=field,
            details=details
        )
    ).to_dict()


def validation_error(
    message: str,
    field: Optional[str] = None,
    invalid_value: Any = None
) -> Dict[str, Any]:
    """Create a validation error response.

    Args:
        message: Description of the validation error
        field: Name of the field that failed validation
        invalid_value: The invalid value that was provided

    Returns:
        Standardized validation error response

    Example:
        >>> validation_error("Name cannot be empty", field="name", invalid_value="")
    """
    details = None
    if invalid_value is not None:
        # Truncate long values to keep response compact
        value_str = str(invalid_value)
        truncated = value_str[:50] + "..." if len(value_str) > 50 else value_str
        details = {"invalid_value": truncated}

    return error_response(
        ErrorType.VALIDATION_ERROR,
        message,
        field=field,
        details=details
    )


def not_found_error(resource_type: str, resource_id: Optional[str] = None) -> Dict[str, Any]:
    """Create a not found error response.

    Args:
        resource_type: Type of resource (e.g., "concept", "relationship")
        resource_id: Optional ID of the resource that wasn't found

    Returns:
        Standardized not found error response

    Example:
        >>> not_found_error("Concept", "abc-123")
    """
    # Map resource types to specific error types
    error_type_map = {
        "concept": ErrorType.CONCEPT_NOT_FOUND,
        "relationship": ErrorType.RELATIONSHIP_NOT_FOUND,
        "path": ErrorType.PATH_NOT_FOUND,
    }

    error_type = error_type_map.get(resource_type.lower(), ErrorType.NOT_FOUND)
    message = f"{resource_type} not found" + (f": {resource_id}" if resource_id else "")

    details = {"resource_type": resource_type}
    if resource_id:
        details["resource_id"] = resource_id

    return error_response(error_type, message, details=details)


def database_error(
    service_name: Optional[str] = None,
    operation: Optional[str] = None
) -> Dict[str, Any]:
    """Create a database error response.

    Args:
        service_name: Name of the database service (e.g., "neo4j", "chromadb")
        operation: Operation that failed (e.g., "query", "write")

    Returns:
        Standardized database error response
    """
    # Map service names to specific error types
    error_type_map = {
        "neo4j": ErrorType.NEO4J_ERROR,
        "chromadb": ErrorType.CHROMADB_ERROR,
        "embedding": ErrorType.EMBEDDING_ERROR,
    }

    error_type = error_type_map.get(
        service_name.lower() if service_name else "",
        ErrorType.DATABASE_ERROR
    )

    message = "Database operation failed"
    if service_name:
        message = f"{service_name} operation failed"
    if operation:
        message += f": {operation}"

    details: Dict[str, Any] = {}
    if service_name:
        details["service"] = service_name
    if operation:
        details["operation"] = operation

    return error_response(error_type, message, details=details if details else None)


def internal_error(message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create an internal error response for unexpected errors.

    Args:
        message: Technical error message
        details: Optional additional error details

    Returns:
        Standardized internal error response
    """
    return error_response(ErrorType.INTERNAL_ERROR, message, details=details)


def service_unavailable_error(service_name: str) -> Dict[str, Any]:
    """Create a service unavailable error response.

    Args:
        service_name: Name of the unavailable service

    Returns:
        Standardized service unavailable error response
    """
    return error_response(
        ErrorType.SERVICE_UNAVAILABLE,
        f"{service_name} service is not available",
        details={"service": service_name}
    )


def parse_pydantic_validation_error(validation_error_exc: Exception) -> Dict[str, Any]:
    """Parse a Pydantic validation error into a standardized error response.

    Args:
        validation_error_exc: Pydantic ValidationError exception

    Returns:
        Standardized error response with field-level details
    """
    error_str = str(validation_error_exc)

    # Common Pydantic error patterns
    if "Field required" in error_str:
        return validation_error(
            message="Required field is missing",
            field=None
        )
    elif "cannot be empty" in error_str.lower():
        return validation_error(
            message="Field cannot be empty",
            field=None
        )
    elif "min_length" in error_str.lower():
        return validation_error(
            message="Field is too short",
            field=None
        )
    elif "max_length" in error_str.lower():
        return validation_error(
            message="Field is too long",
            field=None
        )
    else:
        return validation_error(message=error_str)
