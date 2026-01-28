"""
API Response Contracts - Unified response format for AgentOS WebUI

This module defines the standard API response contract and utility functions
for consistent error handling and authentication across all API endpoints.

Created for Agent-API-Contract (Wave1-A1)

Standard Response Format:
{
    "ok": bool,           # Operation success status
    "data": Any,          # Actual response data
    "error": str | None,  # Human-readable error message
    "hint": str | None,   # User-actionable hint for fixing the error
    "reason_code": str | None  # Machine-readable error code
}

Reason Codes:
- AUTH_REQUIRED: Missing or invalid authentication token
- AUTH_FORBIDDEN: Authenticated but insufficient permissions
- INVALID_INPUT: Validation error in request parameters
- NOT_FOUND: Requested resource does not exist
- CONFLICT: Resource conflict (e.g., duplicate entry)
- INTERNAL_ERROR: Unexpected server error
- SERVICE_UNAVAILABLE: Downstream service unavailable
- RATE_LIMITED: Too many requests
- BAD_STATE: Operation not allowed in current state
"""

import os
import logging
from typing import Any, Dict, Optional, TypeVar, Generic
from pydantic import BaseModel, Field
from fastapi import HTTPException, Header

logger = logging.getLogger(__name__)

# Type variable for generic response data
T = TypeVar('T')


# ============================================
# Reason Code Enumeration
# ============================================

class ReasonCode:
    """Standard reason codes for API errors

    These codes are machine-readable and help clients handle errors programmatically.
    """

    # Authentication & Authorization
    AUTH_REQUIRED = "AUTH_REQUIRED"
    AUTH_FORBIDDEN = "AUTH_FORBIDDEN"

    # Input Validation
    INVALID_INPUT = "INVALID_INPUT"
    INVALID_TASK_ID = "INVALID_TASK_ID"
    INVALID_REPO_ID = "INVALID_REPO_ID"
    INVALID_SESSION_ID = "INVALID_SESSION_ID"

    # Resource Errors
    NOT_FOUND = "NOT_FOUND"
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    REPO_NOT_FOUND = "REPO_NOT_FOUND"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"

    # State & Conflict
    CONFLICT = "CONFLICT"
    BAD_STATE = "BAD_STATE"
    TASK_NOT_READY = "TASK_NOT_READY"

    # Service Errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    DATABASE_ERROR = "DATABASE_ERROR"
    SERVER_MISCONFIGURED = "SERVER_MISCONFIGURED"

    # Rate Limiting
    RATE_LIMITED = "RATE_LIMITED"


# ============================================
# Response Models
# ============================================

class ApiError(BaseModel):
    """Standard API error response

    Contains both human-readable messages and machine-readable codes.
    """

    error: str = Field(..., description="Human-readable error message")
    reason_code: str = Field(..., description="Machine-readable error code")
    hint: Optional[str] = Field(None, description="User-actionable hint for fixing the error")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")

    class Config:
        schema_extra = {
            "example": {
                "error": "Task not found",
                "reason_code": "TASK_NOT_FOUND",
                "hint": "Check the task_id and ensure the task exists",
                "details": {"task_id": "01HQ7XYZ..."}
            }
        }


class ApiResponse(BaseModel, Generic[T]):
    """Standard API response wrapper

    All new API endpoints should return responses in this format.
    """

    ok: bool = Field(..., description="Operation success status")
    data: Optional[T] = Field(None, description="Response data (present if ok=true)")
    error: Optional[str] = Field(None, description="Error message (present if ok=false)")
    hint: Optional[str] = Field(None, description="User-actionable hint")
    reason_code: Optional[str] = Field(None, description="Machine-readable error code")

    class Config:
        schema_extra = {
            "example": {
                "ok": True,
                "data": {"task_id": "01HQ7XYZ...", "status": "running"},
                "error": None,
                "hint": None,
                "reason_code": None
            }
        }


# ============================================
# Utility Functions
# ============================================

def success(data: Any) -> Dict[str, Any]:
    """Create a success response

    Args:
        data: Response data

    Returns:
        Standard success response dictionary

    Example:
        return success({"task_id": "123", "status": "running"})
    """
    return {
        "ok": True,
        "data": data,
        "error": None,
        "hint": None,
        "reason_code": None,
    }


def error(
    message: str,
    reason_code: str = ReasonCode.INTERNAL_ERROR,
    hint: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    http_status: int = 500,
) -> HTTPException:
    """Create an error response with HTTPException

    Args:
        message: Human-readable error message
        reason_code: Machine-readable error code
        hint: User-actionable hint (optional)
        details: Additional error details (optional)
        http_status: HTTP status code (default: 500)

    Returns:
        HTTPException with standard error format

    Example:
        raise error(
            "Task not found",
            reason_code=ReasonCode.TASK_NOT_FOUND,
            hint="Check the task_id and ensure the task exists",
            http_status=404
        )
    """
    error_detail = {
        "ok": False,
        "data": None,
        "error": message,
        "hint": hint,
        "reason_code": reason_code,
    }

    if details:
        error_detail["details"] = details

    return HTTPException(status_code=http_status, detail=error_detail)


def error_response(
    message: str,
    reason_code: str = ReasonCode.INTERNAL_ERROR,
    hint: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create an error response dictionary (without raising HTTPException)

    Use this when you need to return an error response without raising an exception.

    Args:
        message: Human-readable error message
        reason_code: Machine-readable error code
        hint: User-actionable hint (optional)
        details: Additional error details (optional)

    Returns:
        Standard error response dictionary

    Example:
        return error_response(
            "Task not found",
            reason_code=ReasonCode.TASK_NOT_FOUND,
            hint="Check the task_id and ensure the task exists"
        )
    """
    response = {
        "ok": False,
        "data": None,
        "error": message,
        "hint": hint,
        "reason_code": reason_code,
    }

    if details:
        response["details"] = details

    return response


# ============================================
# Authentication & Authorization
# ============================================

def validate_admin_token(
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token")
) -> bool:
    """Validate admin token for protected endpoints

    This is a basic token-based authentication mechanism.
    In production, replace with proper JWT/OAuth2.

    Args:
        x_admin_token: Admin token from request header

    Returns:
        True if valid, raises HTTPException if invalid

    Raises:
        HTTPException: 401 if token is missing or invalid

    Example:
        @router.post("/admin/tasks/{task_id}/cancel")
        async def cancel_task(
            task_id: str,
            _: bool = Depends(validate_admin_token)
        ):
            # Protected endpoint - requires admin token
            pass
    """
    import secrets

    expected_token = os.getenv("AGENTOS_ADMIN_TOKEN")

    # No default fallback - admin token MUST be configured
    if not expected_token:
        raise error(
            "Admin operations disabled",
            reason_code=ReasonCode.SERVER_MISCONFIGURED,
            hint="Set AGENTOS_ADMIN_TOKEN environment variable to enable admin operations",
            http_status=503,
        )

    if not x_admin_token:
        raise error(
            "Admin token required",
            reason_code=ReasonCode.AUTH_REQUIRED,
            hint="Include X-Admin-Token header in your request",
            http_status=401,
        )

    # Use constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(x_admin_token, expected_token):
        raise error(
            "Invalid admin token",
            reason_code=ReasonCode.AUTH_FORBIDDEN,
            hint="Check your admin token and try again",
            http_status=403,
        )

    return True


def validate_user_token(
    x_user_token: Optional[str] = Header(None, alias="X-User-Token")
) -> Optional[str]:
    """Validate user token and extract user ID

    This is a basic token-based authentication mechanism.
    In production, replace with proper JWT/OAuth2.

    Args:
        x_user_token: User token from request header

    Returns:
        User ID if valid, None if token not required

    Raises:
        HTTPException: 401 if token is invalid

    Example:
        @router.post("/tasks/{task_id}/approve")
        async def approve_task(
            task_id: str,
            user_id: str = Depends(validate_user_token)
        ):
            # Protected endpoint - requires user token
            pass
    """
    require_auth = os.getenv("AGENTOS_REQUIRE_USER_AUTH", "false").lower() == "true"

    if not require_auth:
        # Auth not required - return default user
        return "default_user"

    if not x_user_token:
        raise error(
            "User token required",
            reason_code=ReasonCode.AUTH_REQUIRED,
            hint="Include X-User-Token header in your request",
            http_status=401,
        )

    # TODO: Implement proper token validation (JWT decode, session lookup, etc.)
    # For now, just return the token as user_id
    return x_user_token


# ============================================
# Common Error Helpers
# ============================================

def not_found_error(
    resource_type: str,
    resource_id: str,
    hint: Optional[str] = None
) -> HTTPException:
    """Helper for NOT_FOUND errors

    Args:
        resource_type: Type of resource (e.g., "Task", "Repository")
        resource_id: Resource identifier
        hint: User-actionable hint (optional)

    Returns:
        HTTPException with 404 status

    Example:
        raise not_found_error("Task", task_id, "Ensure the task exists")
    """
    return error(
        f"{resource_type} not found: {resource_id}",
        reason_code=f"{resource_type.upper()}_NOT_FOUND",
        hint=hint or f"Check the {resource_type.lower()}_id and ensure the {resource_type.lower()} exists",
        http_status=404,
    )


def validation_error(
    message: str,
    hint: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """Helper for INVALID_INPUT errors

    Args:
        message: Error message
        hint: User-actionable hint (optional)
        details: Validation error details (optional)

    Returns:
        HTTPException with 400 status

    Example:
        raise validation_error(
            "Invalid task_id format",
            hint="task_id must be a valid ULID",
            details={"task_id": task_id}
        )
    """
    return error(
        message,
        reason_code=ReasonCode.INVALID_INPUT,
        hint=hint,
        details=details,
        http_status=400,
    )


def bad_state_error(
    message: str,
    hint: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """Helper for BAD_STATE errors

    Args:
        message: Error message
        hint: User-actionable hint (optional)
        details: State information (optional)

    Returns:
        HTTPException with 409 status

    Example:
        raise bad_state_error(
            "Task is not in a runnable state",
            hint="Task must be in APPROVED or QUEUED state to run",
            details={"current_state": task.status}
        )
    """
    return error(
        message,
        reason_code=ReasonCode.BAD_STATE,
        hint=hint,
        details=details,
        http_status=409,
    )
