"""
Response Sanitization Middleware

Prevents accidental leakage of sensitive data in API responses.
Masks API keys, tokens, and other credentials.

v0.3.2 Closeout - Security hardening
"""

import re
import logging
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)

# Patterns that indicate sensitive fields
SENSITIVE_FIELD_PATTERNS = [
    r'.*api[_-]?key.*',
    r'.*token.*',
    r'.*secret.*',
    r'.*password.*',
    r'.*credential.*',
    r'.*auth.*key.*',
]

# Patterns for detecting API key-like strings in values
API_KEY_PATTERNS = [
    r'sk-[a-zA-Z0-9]{48,}',  # OpenAI-style keys
    r'sk-ant-[a-zA-Z0-9-]{48,}',  # Anthropic-style keys
    r'[a-zA-Z0-9]{32,}',  # Generic long alphanumeric strings
]


def is_sensitive_field(field_name: str) -> bool:
    """
    Check if a field name indicates sensitive data

    Args:
        field_name: Field name to check (case-insensitive)

    Returns:
        True if field appears to contain sensitive data
    """
    field_lower = field_name.lower()

    for pattern in SENSITIVE_FIELD_PATTERNS:
        if re.match(pattern, field_lower):
            return True

    return False


def looks_like_api_key(value: str) -> bool:
    """
    Check if a string value looks like an API key

    Args:
        value: String to check

    Returns:
        True if value matches API key patterns
    """
    if not isinstance(value, str) or len(value) < 20:
        return False

    for pattern in API_KEY_PATTERNS:
        if re.match(pattern, value):
            return True

    return False


def mask_value(value: str) -> str:
    """
    Mask a sensitive value

    Shows first/last few characters for debugging while hiding middle.

    Examples:
        sk-1234567890abcdef... -> sk-****cdef
        sk-ant-1234567890... -> sk-ant-****7890
    """
    if not value or len(value) < 8:
        return "****"

    # Special handling for known key formats
    if value.startswith("sk-ant-"):
        return f"sk-ant-****{value[-4:]}"
    elif value.startswith("sk-"):
        return f"sk-****{value[-4:]}"
    else:
        # Generic masking
        return f"****{value[-4:]}"


def mask_sensitive_fields(data: Any, depth: int = 0, max_depth: int = 10) -> Any:
    """
    Recursively mask sensitive fields in data structures

    Args:
        data: Data to sanitize (dict, list, or primitive)
        depth: Current recursion depth
        max_depth: Maximum recursion depth to prevent infinite loops

    Returns:
        Sanitized copy of data
    """
    # Prevent infinite recursion
    if depth > max_depth:
        return data

    # Handle dictionaries
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            # Check if field name is sensitive
            if is_sensitive_field(key):
                if isinstance(value, str):
                    result[key] = mask_value(value)
                elif isinstance(value, (dict, list)):
                    # Recurse into nested structures even for sensitive field names
                    result[key] = mask_sensitive_fields(value, depth + 1, max_depth)
                else:
                    result[key] = "****"
            # Check if value looks like an API key
            elif isinstance(value, str) and looks_like_api_key(value):
                result[key] = mask_value(value)
            # Recurse into nested structures
            elif isinstance(value, (dict, list)):
                result[key] = mask_sensitive_fields(value, depth + 1, max_depth)
            else:
                result[key] = value
        return result

    # Handle lists
    elif isinstance(data, list):
        return [mask_sensitive_fields(item, depth + 1, max_depth) for item in data]

    # Handle primitives
    else:
        return data


def sanitize_response(response_data: Union[Dict, List, Any]) -> Union[Dict, List, Any]:
    """
    Sanitize API response data

    Main entry point for response sanitization.
    Should be called on all API responses before returning to client.

    Args:
        response_data: Response data to sanitize

    Returns:
        Sanitized copy of response data

    Example:
        ```python
        @router.get("/api/providers/status")
        async def get_status():
            data = {"providers": [...], "api_key": "sk-secret"}
            return sanitize_response(data)
        ```
    """
    try:
        return mask_sensitive_fields(response_data)
    except Exception as e:
        logger.error(f"Failed to sanitize response: {e}")
        # On error, return the data as-is but log the failure
        # Better to potentially leak than to crash the response
        return response_data
