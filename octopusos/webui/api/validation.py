"""Validation constants and helpers for WebUI API."""

MAX_PAYLOAD_SIZE = 1 * 1024 * 1024  # 1 MB (L-3)
MAX_TITLE_LENGTH = 500  # L-4
MAX_CONTENT_LENGTH = 50000  # L-5 (50 KB)


def validate_title_length(title: str) -> None:
    if title is None:
        return
    if len(title) > MAX_TITLE_LENGTH:
        raise ValueError(f"Title exceeds maximum length ({MAX_TITLE_LENGTH})")


def validate_content_length(content: str) -> None:
    if content is None:
        return
    if len(content) > MAX_CONTENT_LENGTH:
        raise ValueError(f"Content exceeds maximum length ({MAX_CONTENT_LENGTH})")
