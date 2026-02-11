"""Row utilities for safe access across sqlite3.Row and dict-like objects."""

from __future__ import annotations

from typing import Any, Mapping


def row_to_dict(row: Any) -> Mapping[str, Any]:
    """Normalize sqlite3.Row to a dict for safe .get access.

    If row already behaves like a mapping, it is returned unchanged.
    """
    if row is None:
        return {}
    if hasattr(row, "keys"):
        return dict(row)
    if isinstance(row, dict):
        return row
    return {"value": row}
