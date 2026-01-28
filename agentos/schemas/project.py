"""Project and Repository Schemas

Data models for multi-repository project management.
Maps to v18 schema (project_repos table).
"""

import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class RepoRole(str, Enum):
    """Repository role enumeration"""

    CODE = "code"  # Code repository (default)
    DOCS = "docs"  # Documentation repository
    INFRA = "infra"  # Infrastructure repository (Terraform, K8s, etc.)
    MONO_SUBDIR = "mono-subdir"  # Monorepo subdirectory


class RepoSpec(BaseModel):
    """Repository specification

    Maps to project_repos table in v18 schema.
    Represents a repository binding within a project.
    """

    repo_id: str = Field(..., description="Unique repository ID (ULID or UUID)")
    project_id: str = Field(..., description="Associated project ID")
    name: str = Field(..., description="User-friendly repository name (e.g., 'frontend', 'backend')")
    remote_url: Optional[str] = Field(None, description="Remote repository URL (for clone/pull)")
    default_branch: str = Field("main", description="Default branch name")
    workspace_relpath: str = Field(..., description="Relative path from project workspace (e.g., '.', 'services/api', '../shared')")
    role: RepoRole = Field(RepoRole.CODE, description="Repository role")
    is_writable: bool = Field(True, description="Whether the repository is writable")
    auth_profile: Optional[str] = Field(None, description="Authentication profile name (e.g., 'github-pat', 'gitlab-ssh')")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extended metadata (JSON)")

    @field_validator("metadata", mode="before")
    @classmethod
    def parse_metadata(cls, v: Any) -> Dict[str, Any]:
        """Parse metadata from JSON string if needed"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v or {}

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def parse_datetime(cls, v: Any) -> Optional[datetime]:
        """Parse datetime from string if needed"""
        if v is None:
            return None
        if isinstance(v, str):
            # Handle ISO format with or without 'Z'
            v = v.replace('Z', '+00:00')
            return datetime.fromisoformat(v)
        return v

    def is_default(self) -> bool:
        """Check if this is a default repository"""
        return self.name == "default"

    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to database-compatible dictionary"""
        return {
            "repo_id": self.repo_id,
            "project_id": self.project_id,
            "name": self.name,
            "remote_url": self.remote_url,
            "default_branch": self.default_branch,
            "workspace_relpath": self.workspace_relpath,
            "role": self.role.value,
            "is_writable": 1 if self.is_writable else 0,
            "auth_profile": self.auth_profile,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": json.dumps(self.metadata) if self.metadata else None,
        }

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "RepoSpec":
        """Create from database row (sqlite3.Row or dict)"""
        return cls(
            repo_id=row["repo_id"],
            project_id=row["project_id"],
            name=row["name"],
            remote_url=row.get("remote_url"),
            default_branch=row.get("default_branch", "main"),
            workspace_relpath=row["workspace_relpath"],
            role=RepoRole(row.get("role", "code")),
            is_writable=bool(row.get("is_writable", 1)),
            auth_profile=row.get("auth_profile"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
            metadata=row.get("metadata", "{}"),
        )


class Project(BaseModel):
    """Project with multi-repository support

    Represents a project that can bind to multiple repositories.
    Maintains backward compatibility with single-repo projects.
    """

    id: str = Field(..., description="Project ID")
    name: str = Field(..., description="Project name")
    path: Optional[str] = Field(None, description="Project path (legacy, for backward compatibility)")
    repos: List[RepoSpec] = Field(default_factory=list, description="Bound repositories")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extended metadata (JSON)")

    @field_validator("metadata", mode="before")
    @classmethod
    def parse_metadata(cls, v: Any) -> Dict[str, Any]:
        """Parse metadata from JSON string if needed"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v or {}

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def parse_datetime(cls, v: Any) -> Optional[datetime]:
        """Parse datetime from string if needed"""
        if v is None:
            return None
        if isinstance(v, str):
            v = v.replace('Z', '+00:00')
            return datetime.fromisoformat(v)
        return v

    def get_default_repo(self) -> Optional[RepoSpec]:
        """Get the default repository

        Returns:
            The default repository if exists, otherwise the first repo, or None

        Priority:
        1. Repo with name="default"
        2. First repo in the list
        3. None if no repos bound

        Note:
            For multi-repo projects, this method issues a deprecation warning
            when used with single-repo access patterns. Prefer explicit repo access.
        """
        if not self.repos:
            return None

        # Issue warning for multi-repo projects using single-repo API
        if self.is_multi_repo():
            import warnings
            warnings.warn(
                f"Project '{self.id}' has {len(self.repos)} repositories. "
                "Using get_default_repo() for multi-repo projects is deprecated. "
                "Consider explicit repository access via get_repo_by_name() or iterate over repos.",
                DeprecationWarning,
                stacklevel=2
            )

        # Try to find repo with name="default"
        for repo in self.repos:
            if repo.is_default():
                return repo

        # Fallback to first repo
        return self.repos[0]

    def get_repo_by_name(self, name: str) -> Optional[RepoSpec]:
        """Get repository by name

        Args:
            name: Repository name

        Returns:
            Repository spec or None if not found
        """
        for repo in self.repos:
            if repo.name == name:
                return repo
        return None

    def get_repo_by_id(self, repo_id: str) -> Optional[RepoSpec]:
        """Get repository by ID

        Args:
            repo_id: Repository ID

        Returns:
            Repository spec or None if not found
        """
        for repo in self.repos:
            if repo.repo_id == repo_id:
                return repo
        return None

    def is_multi_repo(self) -> bool:
        """Check if this is a multi-repository project"""
        return len(self.repos) > 1

    def is_single_repo(self) -> bool:
        """Check if this is a single-repository project (backward compatible)"""
        return len(self.repos) == 1

    def has_repos(self) -> bool:
        """Check if project has any repositories bound"""
        return len(self.repos) > 0

    # Backward compatibility properties
    @property
    def workspace_path(self) -> Optional[str]:
        """Get workspace path (backward compatible property)

        Returns:
            Workspace path of the default repository, or legacy path field

        Deprecated:
            For multi-repo projects, use get_default_repo().workspace_relpath
            or iterate over repos for explicit access.
        """
        if self.is_multi_repo():
            import warnings
            warnings.warn(
                "Accessing .workspace_path on multi-repo project is deprecated. "
                "Use get_default_repo().workspace_relpath or iterate over repos.",
                DeprecationWarning,
                stacklevel=2
            )

        default_repo = self.get_default_repo()
        if default_repo:
            return default_repo.workspace_relpath

        # Fallback to legacy path field
        return self.path

    @property
    def remote_url(self) -> Optional[str]:
        """Get remote URL (backward compatible property)

        Returns:
            Remote URL of the default repository

        Deprecated:
            For multi-repo projects, use get_default_repo().remote_url
        """
        if self.is_multi_repo():
            import warnings
            warnings.warn(
                "Accessing .remote_url on multi-repo project is deprecated. "
                "Use get_default_repo().remote_url or iterate over repos.",
                DeprecationWarning,
                stacklevel=2
            )

        default_repo = self.get_default_repo()
        if default_repo:
            return default_repo.remote_url

        return None

    @property
    def default_branch(self) -> str:
        """Get default branch (backward compatible property)

        Returns:
            Default branch of the default repository, defaults to 'main'

        Deprecated:
            For multi-repo projects, use get_default_repo().default_branch
        """
        if self.is_multi_repo():
            import warnings
            warnings.warn(
                "Accessing .default_branch on multi-repo project is deprecated. "
                "Use get_default_repo().default_branch or iterate over repos.",
                DeprecationWarning,
                stacklevel=2
            )

        default_repo = self.get_default_repo()
        if default_repo:
            return default_repo.default_branch

        return "main"
