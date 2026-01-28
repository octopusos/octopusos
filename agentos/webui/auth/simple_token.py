"""
Simple Admin Token Authentication

Sprint B Task #7: Minimal Auth Gate

NOT a full authentication system. This is a single admin token
that protects write operations (start/stop, secrets management).

Future: Sprint C will add proper multi-user auth.
"""

import os
import logging
from typing import Optional
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

# Security scheme for Swagger docs
security_scheme = HTTPBearer(auto_error=False)


def get_admin_token() -> Optional[str]:
    """
    Get admin token from environment

    Returns None if not configured (auth disabled in dev)
    """
    return os.getenv("AGENTOS_ADMIN_TOKEN")


def verify_admin_token(token: str) -> bool:
    """
    Verify if provided token matches admin token

    Args:
        token: Bearer token from Authorization header

    Returns:
        True if token is valid, False otherwise
    """
    admin_token = get_admin_token()

    # If no admin token configured, auth is disabled (dev mode)
    if not admin_token:
        logger.debug("Admin token not configured, auth disabled")
        return True

    # Compare tokens (constant-time comparison would be better for production)
    return token == admin_token


def require_admin(credentials: Optional[HTTPAuthorizationCredentials] = None) -> bool:
    """
    FastAPI dependency to require admin token

    Usage:
        @router.post("/endpoint", dependencies=[Depends(require_admin)])

    Raises:
        HTTPException: 401 if token missing or invalid

    Returns:
        True if authenticated
    """
    admin_token = get_admin_token()

    # If no admin token configured, allow (dev mode)
    if not admin_token:
        logger.debug("Admin token not configured, allowing request (dev mode)")
        return True

    # Extract token from credentials
    if not credentials:
        logger.warning("Admin token required but not provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Set Authorization: Bearer <token> header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # Verify token (DO NOT log token value)
    if not verify_admin_token(token):
        logger.warning("Invalid admin token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug("Admin token verified successfully")
    return True


def extract_bearer_token(request: Request) -> Optional[str]:
    """
    Extract bearer token from Authorization header

    Args:
        request: FastAPI Request object

    Returns:
        Token string if present, None otherwise
    """
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return None

    # Format: "Bearer <token>"
    parts = auth_header.split()

    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]
