"""Project management module

Handles multi-repository project bindings and workspace management.
"""

from .compat import (
    SingleRepoCompatAdapter,
    check_compatibility_warnings,
    ensure_default_repo,
    get_project_workspace_path,
    migrate_project_to_multi_repo,
)
from .repository import (
    ProjectRepository,
    RepoContext,
    RepoRegistry,
)

__all__ = [
    "ProjectRepository",
    "RepoContext",
    "RepoRegistry",
    # Compatibility layer
    "SingleRepoCompatAdapter",
    "get_project_workspace_path",
    "ensure_default_repo",
    "check_compatibility_warnings",
    "migrate_project_to_multi_repo",
]
