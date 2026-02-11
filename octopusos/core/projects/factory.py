"""Project factory utilities for invariants (path normalization)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from octopusos.core.workspace.layout import WorkspaceLayout


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value


def ensure_project_path(
    project_id: str,
    name: Optional[str] = None,
    path: Optional[str] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """
    Deterministically generate and validate project.path.

    Rules:
    - If path is provided and non-empty: normalize and return.
    - If path is missing: generate from workspace_root/projects/<slug or project_id>.
    - Must never return empty.
    """
    if path and str(path).strip():
        normalized = Path(path).expanduser().resolve()
        result = str(normalized)
    else:
        slug = _slugify(name) if name else ""
        if not slug:
            slug = project_id
        root = workspace_root or Path.cwd()
        layout = WorkspaceLayout(root)
        result = str(layout.get_project_root(slug))

    if not result or not str(result).strip():
        raise ValueError("project.path cannot be empty")
    return result
