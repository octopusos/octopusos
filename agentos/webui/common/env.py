"""
Environment detection utilities for WebUI

Helps isolate mock data to development environments only.
"""

import os
from fastapi import HTTPException


def is_dev() -> bool:
    """Check if running in development mode

    Returns:
        True if AGENTOS_ENV is dev/development/local, False otherwise
    """
    env = os.getenv("AGENTOS_ENV", "development").lower()
    return env in ("dev", "development", "local")


def require_dev(feature: str) -> None:
    """Raise error if not in development mode

    Args:
        feature: Name of the feature requiring database integration

    Raises:
        HTTPException: 503 if not in development mode
    """
    if not is_dev():
        current_env = os.getenv("AGENTOS_ENV", "production")
        raise HTTPException(
            status_code=503,
            detail=f"{feature} requires database integration (mock data disabled in {current_env} environment)"
        )
