"""Task-Driven Architecture: Task as the root aggregate for full traceability"""

from octopusos.core.task.models import Task, TaskContext, TaskTrace, TaskLineageEntry
from octopusos.core.task.manager import TaskManager
from octopusos.core.task.trace_builder import TraceBuilder
from octopusos.core.task.run_mode import RunMode, ModelPolicy, TaskMetadata
from octopusos.core.task.service import TaskService
from octopusos.core.task.state_machine import TaskStateMachine
from octopusos.core.task.states import TaskState
from octopusos.core.task.errors import (
    TaskStateError,
    InvalidTransitionError,
    TaskNotFoundError,
    TaskAlreadyInStateError,
)
from octopusos.core.task.rollback import TaskRollbackService, RollbackNotAllowedError
from octopusos.core.task.repo_context import (
    TaskRepoContext,
    ExecutionEnv,
    PathSecurityError,
)
from octopusos.core.task.task_repo_service import TaskRepoService, build_repo_contexts

__all__ = [
    # Models
    "Task",
    "TaskContext",
    "TaskTrace",
    "TaskLineageEntry",
    # Managers
    "TaskManager",
    "TraceBuilder",
    # State Machine
    "TaskService",
    "TaskStateMachine",
    "TaskState",
    # Rollback
    "TaskRollbackService",
    "RollbackNotAllowedError",
    # Errors
    "TaskStateError",
    "InvalidTransitionError",
    "TaskNotFoundError",
    "TaskAlreadyInStateError",
    # Run Mode
    "RunMode",
    "ModelPolicy",
    "TaskMetadata",
    # Multi-Repo Support (Phase 5.1)
    "TaskRepoContext",
    "ExecutionEnv",
    "PathSecurityError",
    "TaskRepoService",
    "build_repo_contexts",
]
