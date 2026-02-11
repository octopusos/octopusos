"""Provider models and path validation helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple


def is_safe_path(path: str, allowed_dirs: Iterable[Path]) -> Tuple[bool, str]:
    """Validate that path resolves under one of the allowed directories.

    Returns (is_safe, error_message).
    """
    try:
        target = Path(path).expanduser().resolve()
    except Exception as exc:
        return False, f"Invalid path: {exc}"

    allowed = [Path(p).expanduser().resolve() for p in allowed_dirs]
    for base in allowed:
        try:
            if target.is_relative_to(base):
                return True, ""
        except Exception:
            continue

    return False, "Path is outside allowed directories."
