"""Task data models"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

# Import run_mode types for type hints
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentos.core.task.run_mode import TaskMetadata


@dataclass
class Task:
    """Task: Root aggregate for traceability"""

    task_id: str  # ULID
    title: str
    status: str = "created"  # Free-form: created/planning/executing/succeeded/failed/canceled/orphan
    session_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Router fields (PR-2: Chat→Task Router Integration)
    route_plan_json: Optional[str] = None  # JSON serialized RoutePlan
    requirements_json: Optional[str] = None  # JSON serialized TaskRequirements
    selected_instance_id: Optional[str] = None  # Selected provider instance ID
    router_version: Optional[str] = None  # Router version used
    
    def is_orphan(self) -> bool:
        """Check if this is an orphan task"""
        return self.status == "orphan" or self.metadata.get("orphan", False)
    
    def get_run_mode(self) -> str:
        """Get run mode from metadata"""
        return self.metadata.get("run_mode", "assisted")
    
    def get_model_policy(self) -> Dict[str, str]:
        """Get model policy from metadata"""
        return self.metadata.get("model_policy", {})
    
    def get_current_stage(self) -> Optional[str]:
        """Get current stage from metadata"""
        return self.metadata.get("current_stage")
    
    def set_current_stage(self, stage: str) -> None:
        """Set current stage in metadata"""
        self.metadata["current_stage"] = stage
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "task_id": self.task_id,
            "title": self.title,
            "status": self.status,
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "created_by": self.created_by,
            "metadata": self.metadata,
        }
        # Add router fields if present
        if self.route_plan_json:
            result["route_plan_json"] = self.route_plan_json
        if self.requirements_json:
            result["requirements_json"] = self.requirements_json
        if self.selected_instance_id:
            result["selected_instance_id"] = self.selected_instance_id
        if self.router_version:
            result["router_version"] = self.router_version
        return result


@dataclass
class TaskContext:
    """Task execution context (passed through pipeline)"""
    
    task_id: str
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "task_id": self.task_id,
            "session_id": self.session_id,
            "metadata": self.metadata,
        }


@dataclass
class TaskLineageEntry:
    """Single lineage entry"""
    
    task_id: str
    kind: str  # nl_request|intent|coordinator_run|execution_request|commit|...
    ref_id: str
    phase: Optional[str] = None
    timestamp: Optional[str] = None  # Renamed from created_at for consistency
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Backward compatibility alias
    @property
    def created_at(self) -> Optional[str]:
        """Alias for timestamp (backward compatibility)"""
        return self.timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "task_id": self.task_id,
            "kind": self.kind,
            "ref_id": self.ref_id,
            "phase": self.phase,
            "created_at": self.timestamp,  # Keep created_at in dict for DB compatibility
            "metadata": self.metadata,
        }


@dataclass
class TaskTrace:
    """Task trace: Shallow output by default, expandable on demand"""

    task: Task
    timeline: List[TaskLineageEntry]  # Sorted by created_at
    agents: List[Dict[str, Any]] = field(default_factory=list)
    audits: List[Dict[str, Any]] = field(default_factory=list)

    # Expanded content (lazy loaded)
    _expanded: Dict[str, Any] = field(default_factory=dict)

    def expand(self, kind: str) -> Optional[Any]:
        """Get expanded content for a specific kind (lazy loaded)"""
        return self._expanded.get(kind)

    def set_expanded(self, kind: str, content: Any) -> None:
        """Set expanded content for a kind"""
        self._expanded[kind] = content

    def get_refs_by_kind(self, kind: str) -> List[str]:
        """Get all ref_ids for a specific kind"""
        return [entry.ref_id for entry in self.timeline if entry.kind == kind]

    def get_latest_ref(self, kind: str) -> Optional[str]:
        """Get the latest ref_id for a specific kind"""
        refs = self.get_refs_by_kind(kind)
        return refs[-1] if refs else None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (shallow)"""
        return {
            "task": self.task.to_dict(),
            "timeline": [entry.to_dict() for entry in self.timeline],
            "agents": self.agents,
            "audits": self.audits,
        }


# ============================================
# Multi-Repo Task Models (v18)
# ============================================


class RepoScopeType(str, Enum):
    """Repository scope type enumeration"""

    FULL = "full"  # Full repository access
    PATHS = "paths"  # Limited to specific paths (via path_filters)
    READ_ONLY = "read_only"  # Read-only access


class DependencyType(str, Enum):
    """Task dependency type enumeration"""

    BLOCKS = "blocks"  # Blocking dependency (must wait for completion)
    REQUIRES = "requires"  # Required dependency (can run in parallel, needs artifacts)
    SUGGESTS = "suggests"  # Suggested dependency (weak, non-blocking)


class ArtifactRefType(str, Enum):
    """Artifact reference type enumeration"""

    COMMIT = "commit"  # Git commit SHA
    BRANCH = "branch"  # Git branch name
    PR = "pr"  # Pull Request number
    PATCH = "patch"  # Patch file path or content
    FILE = "file"  # File path
    TAG = "tag"  # Git tag


@dataclass
class TaskRepoScope:
    """Task repository scope

    Maps to task_repo_scope table in v18 schema.
    Defines which repositories a task can access and how.
    """

    scope_id: Optional[int] = None
    task_id: str = ""
    repo_id: str = ""
    scope: RepoScopeType = RepoScopeType.FULL
    path_filters: List[str] = field(default_factory=list)
    created_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "scope_id": self.scope_id,
            "task_id": self.task_id,
            "repo_id": self.repo_id,
            "scope": self.scope.value if isinstance(self.scope, RepoScopeType) else self.scope,
            "path_filters": json.dumps(self.path_filters) if self.path_filters else None,
            "created_at": self.created_at,
            "metadata": json.dumps(self.metadata) if self.metadata else None,
        }

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "TaskRepoScope":
        """Create from database row"""
        path_filters_raw = row.get("path_filters")
        path_filters = json.loads(path_filters_raw) if path_filters_raw else []

        metadata_raw = row.get("metadata")
        metadata = json.loads(metadata_raw) if metadata_raw else {}

        return cls(
            scope_id=row.get("scope_id"),
            task_id=row["task_id"],
            repo_id=row["repo_id"],
            scope=RepoScopeType(row.get("scope", "full")),
            path_filters=path_filters,
            created_at=row.get("created_at"),
            metadata=metadata,
        )


@dataclass
class TaskDependency:
    """Task dependency relationship

    Maps to task_dependency table in v18 schema.
    Defines dependencies between tasks (including cross-repo dependencies).
    """

    dependency_id: Optional[int] = None
    task_id: str = ""
    depends_on_task_id: str = ""
    dependency_type: DependencyType = DependencyType.BLOCKS
    reason: Optional[str] = None
    created_at: Optional[str] = None
    created_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "dependency_id": self.dependency_id,
            "task_id": self.task_id,
            "depends_on_task_id": self.depends_on_task_id,
            "dependency_type": self.dependency_type.value if isinstance(self.dependency_type, DependencyType) else self.dependency_type,
            "reason": self.reason,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "metadata": json.dumps(self.metadata) if self.metadata else None,
        }

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "TaskDependency":
        """Create from database row"""
        metadata_raw = row.get("metadata")
        metadata = json.loads(metadata_raw) if metadata_raw else {}

        return cls(
            dependency_id=row.get("dependency_id"),
            task_id=row["task_id"],
            depends_on_task_id=row["depends_on_task_id"],
            dependency_type=DependencyType(row.get("dependency_type", "blocks")),
            reason=row.get("reason"),
            created_at=row.get("created_at"),
            created_by=row.get("created_by"),
            metadata=metadata,
        )


@dataclass
class TaskArtifactRef:
    """Task artifact reference

    Maps to task_artifact_ref table in v18 schema.
    Records cross-repo artifact references (commits, PRs, patches, files, etc.).
    """

    artifact_id: Optional[int] = None
    task_id: str = ""
    repo_id: str = ""
    ref_type: ArtifactRefType = ArtifactRefType.COMMIT
    ref_value: str = ""
    summary: Optional[str] = None
    created_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "artifact_id": self.artifact_id,
            "task_id": self.task_id,
            "repo_id": self.repo_id,
            "ref_type": self.ref_type.value if isinstance(self.ref_type, ArtifactRefType) else self.ref_type,
            "ref_value": self.ref_value,
            "summary": self.summary,
            "created_at": self.created_at,
            "metadata": json.dumps(self.metadata) if self.metadata else None,
        }

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "TaskArtifactRef":
        """Create from database row"""
        metadata_raw = row.get("metadata")
        metadata = json.loads(metadata_raw) if metadata_raw else {}

        return cls(
            artifact_id=row.get("artifact_id"),
            task_id=row["task_id"],
            repo_id=row["repo_id"],
            ref_type=ArtifactRefType(row.get("ref_type", "commit")),
            ref_value=row["ref_value"],
            summary=row.get("summary"),
            created_at=row.get("created_at"),
            metadata=metadata,
        )
