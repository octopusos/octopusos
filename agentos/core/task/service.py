"""
Task Service Layer

Provides high-level task operations that enforce state machine transitions.
All task status changes MUST go through this service layer to ensure
proper state machine validation and audit logging.

Key Principles:
1. All state changes go through TaskStateMachine.transition()
2. No direct status updates allowed (except in legacy migration paths)
3. All transitions are audited with actor, reason, and metadata
4. Service methods map to specific business operations

Created for Task #3: S3 - Enforce state machine at core/task API
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

try:
    from ulid import ULID
except ImportError:
    import uuid
    class ULID:
        @staticmethod
        def from_datetime(dt):
            return str(uuid.uuid4())

from agentos.core.task.models import Task, TaskLineageEntry, TaskTrace
from agentos.core.task.states import TaskState, is_valid_state
from agentos.core.task.errors import (
    TaskStateError,
    InvalidTransitionError,
    TaskNotFoundError,
)
from agentos.core.task.state_machine import TaskStateMachine
from agentos.core.task.manager import TaskManager
from agentos.store import get_db

logger = logging.getLogger(__name__)


class TaskService:
    """
    Task Service Layer

    Enforces state machine transitions for all task operations.
    Provides business-level operations with proper state validation.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize Task Service

        Args:
            db_path: Optional path to database (defaults to store default)
        """
        self.db_path = db_path
        self.task_manager = TaskManager(db_path=db_path)
        self.state_machine = TaskStateMachine(db_path=db_path)

    # =========================================================================
    # TASK CREATION (State: DRAFT)
    # =========================================================================

    def create_draft_task(
        self,
        title: str,
        session_id: Optional[str] = None,
        created_by: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        route_plan_json: Optional[str] = None,
        requirements_json: Optional[str] = None,
        selected_instance_id: Optional[str] = None,
        router_version: Optional[str] = None,
    ) -> Task:
        """
        Create a new draft task

        All new tasks MUST start in DRAFT state.
        This enforces the state machine rule that tasks can only be created as drafts.

        Args:
            title: Task title
            session_id: Optional session ID
            created_by: Optional creator identifier
            metadata: Optional metadata
            route_plan_json: Optional route plan JSON
            requirements_json: Optional requirements JSON
            selected_instance_id: Optional selected instance ID
            router_version: Optional router version

        Returns:
            Task object in DRAFT state
        """
        task_id = str(ULID.from_datetime(datetime.now(timezone.utc)))
        now = datetime.now(timezone.utc).isoformat()

        # Auto-generate session_id if not provided
        auto_created_session = False
        if not session_id:
            timestamp = int(datetime.now(timezone.utc).timestamp())
            session_id = f"auto_{task_id[:8]}_{timestamp}"
            auto_created_session = True

        # Enhance metadata with execution context
        if metadata is None:
            metadata = {}

        if "execution_context" not in metadata:
            metadata["execution_context"] = {
                "created_method": "task_service",
                "created_at": now,
            }

        # Create task in DRAFT state
        task = Task(
            task_id=task_id,
            title=title,
            status=TaskState.DRAFT.value,  # ENFORCED: All tasks start as DRAFT
            session_id=session_id,
            created_at=now,
            updated_at=now,
            created_by=created_by,
            metadata=metadata,
            route_plan_json=route_plan_json,
            requirements_json=requirements_json,
            selected_instance_id=selected_instance_id,
            router_version=router_version,
        )

        conn = self.task_manager._get_conn()
        try:
            cursor = conn.cursor()

            # If we auto-created session_id, create the session record first
            if auto_created_session:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO task_sessions (session_id, channel, metadata, created_at, last_activity)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        "auto",
                        json.dumps({"auto_created": True, "task_id": task_id}),
                        now,
                        now,
                    ),
                )

            cursor.execute(
                """
                INSERT INTO tasks (
                    task_id, title, status, session_id, created_at, updated_at, created_by, metadata,
                    route_plan_json, requirements_json, selected_instance_id, router_version
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.task_id,
                    task.title,
                    task.status,
                    task.session_id,
                    task.created_at,
                    task.updated_at,
                    task.created_by,
                    json.dumps(task.metadata) if task.metadata else None,
                    task.route_plan_json,
                    task.requirements_json,
                    task.selected_instance_id,
                    task.router_version,
                ),
            )

            # Record creation audit
            cursor.execute(
                """
                INSERT INTO task_audits (task_id, level, event_type, payload, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    "info",
                    "TASK_CREATED",
                    json.dumps({
                        "actor": created_by or "system",
                        "state": TaskState.DRAFT.value,
                        "reason": "Task created in draft state",
                    }),
                    now
                )
            )

            conn.commit()
            logger.info(f"Created draft task: {task_id} (session: {session_id})")

            # Auto-route task after creation (if routing service is available)
            try:
                from agentos.core.task.routing_service import TaskRoutingService
                import asyncio
                routing_service = TaskRoutingService()
                task_spec = {
                    "task_id": task.task_id,
                    "title": task.title,
                    "metadata": task.metadata or {},
                }
                asyncio.run(routing_service.route_new_task(task.task_id, task_spec))
            except Exception as e:
                logger.exception(f"Task routing failed for task {task.task_id}: {e}")

            return task
        finally:
            conn.close()

    # =========================================================================
    # STATE TRANSITIONS (Using State Machine)
    # =========================================================================

    def approve_task(
        self,
        task_id: str,
        actor: str,
        reason: str = "Task approved for execution",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Task:
        """
        Approve a draft task

        Transition: DRAFT -> APPROVED

        Args:
            task_id: Task ID
            actor: Who is approving the task
            reason: Reason for approval
            metadata: Optional metadata for the transition

        Returns:
            Updated task in APPROVED state

        Raises:
            InvalidTransitionError: If task is not in DRAFT state
        """
        return self.state_machine.transition(
            task_id=task_id,
            to=TaskState.APPROVED.value,
            actor=actor,
            reason=reason,
            metadata=metadata
        )

    def queue_task(
        self,
        task_id: str,
        actor: str = "system",
        reason: str = "Task queued for execution",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Task:
        """
        Queue an approved task for execution

        Transition: APPROVED -> QUEUED

        Args:
            task_id: Task ID
            actor: Who is queuing the task
            reason: Reason for queuing
            metadata: Optional metadata for the transition

        Returns:
            Updated task in QUEUED state

        Raises:
            InvalidTransitionError: If task is not in APPROVED state
        """
        return self.state_machine.transition(
            task_id=task_id,
            to=TaskState.QUEUED.value,
            actor=actor,
            reason=reason,
            metadata=metadata
        )

    def start_task(
        self,
        task_id: str,
        actor: str = "runner",
        reason: str = "Task execution started",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Task:
        """
        Start executing a queued task

        Transition: QUEUED -> RUNNING

        Args:
            task_id: Task ID
            actor: Who is starting the task (usually "runner")
            reason: Reason for starting
            metadata: Optional metadata for the transition

        Returns:
            Updated task in RUNNING state

        Raises:
            InvalidTransitionError: If task is not in QUEUED state
        """
        return self.state_machine.transition(
            task_id=task_id,
            to=TaskState.RUNNING.value,
            actor=actor,
            reason=reason,
            metadata=metadata
        )

    def complete_task_execution(
        self,
        task_id: str,
        actor: str = "runner",
        reason: str = "Task execution completed, starting verification",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Task:
        """
        Mark a running task as completed (enter verification)

        Transition: RUNNING -> VERIFYING

        Args:
            task_id: Task ID
            actor: Who is completing the task
            reason: Reason for completion
            metadata: Optional metadata for the transition

        Returns:
            Updated task in VERIFYING state

        Raises:
            InvalidTransitionError: If task is not in RUNNING state
        """
        return self.state_machine.transition(
            task_id=task_id,
            to=TaskState.VERIFYING.value,
            actor=actor,
            reason=reason,
            metadata=metadata
        )

    def verify_task(
        self,
        task_id: str,
        actor: str = "verifier",
        reason: str = "Task verification completed",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Task:
        """
        Verify a task after execution

        Transition: VERIFYING -> VERIFIED

        Args:
            task_id: Task ID
            actor: Who is verifying the task
            reason: Reason for verification
            metadata: Optional metadata for the transition

        Returns:
            Updated task in VERIFIED state

        Raises:
            InvalidTransitionError: If task is not in VERIFYING state
        """
        return self.state_machine.transition(
            task_id=task_id,
            to=TaskState.VERIFIED.value,
            actor=actor,
            reason=reason,
            metadata=metadata
        )

    def mark_task_done(
        self,
        task_id: str,
        actor: str,
        reason: str = "Task marked as done",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Task:
        """
        Mark a verified task as done

        Transition: VERIFIED -> DONE

        Args:
            task_id: Task ID
            actor: Who is marking the task as done
            reason: Reason for marking done
            metadata: Optional metadata for the transition

        Returns:
            Updated task in DONE state

        Raises:
            InvalidTransitionError: If task is not in VERIFIED state
        """
        return self.state_machine.transition(
            task_id=task_id,
            to=TaskState.DONE.value,
            actor=actor,
            reason=reason,
            metadata=metadata
        )

    def fail_task(
        self,
        task_id: str,
        actor: str,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Task:
        """
        Mark a task as failed

        Transitions: RUNNING -> FAILED, VERIFYING -> FAILED

        Args:
            task_id: Task ID
            actor: Who is marking the task as failed
            reason: Reason for failure
            metadata: Optional metadata for the transition

        Returns:
            Updated task in FAILED state

        Raises:
            InvalidTransitionError: If task is not in a state that can fail
        """
        return self.state_machine.transition(
            task_id=task_id,
            to=TaskState.FAILED.value,
            actor=actor,
            reason=reason,
            metadata=metadata
        )

    def cancel_task(
        self,
        task_id: str,
        actor: str,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Task:
        """
        Cancel a task

        Transitions: DRAFT -> CANCELED, APPROVED -> CANCELED, QUEUED -> CANCELED, RUNNING -> CANCELED

        Args:
            task_id: Task ID
            actor: Who is canceling the task
            reason: Reason for cancellation
            metadata: Optional metadata for the transition

        Returns:
            Updated task in CANCELED state

        Raises:
            InvalidTransitionError: If task is in a terminal state
        """
        return self.state_machine.transition(
            task_id=task_id,
            to=TaskState.CANCELED.value,
            actor=actor,
            reason=reason,
            metadata=metadata
        )

    def retry_failed_task(
        self,
        task_id: str,
        actor: str,
        reason: str = "Task queued for retry",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Task:
        """
        Retry a failed task

        Transition: FAILED -> QUEUED

        Args:
            task_id: Task ID
            actor: Who is retrying the task
            reason: Reason for retry
            metadata: Optional metadata for the transition

        Returns:
            Updated task in QUEUED state

        Raises:
            InvalidTransitionError: If task is not in FAILED state
        """
        return self.state_machine.transition(
            task_id=task_id,
            to=TaskState.QUEUED.value,
            actor=actor,
            reason=reason,
            metadata=metadata
        )

    # =========================================================================
    # QUERY OPERATIONS (No State Changes)
    # =========================================================================

    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get task by ID

        Args:
            task_id: Task ID

        Returns:
            Task object or None
        """
        return self.task_manager.get_task(task_id)

    def list_tasks(
        self,
        limit: int = 100,
        offset: int = 0,
        status_filter: Optional[str] = None,
        orphan_only: bool = False,
    ) -> List[Task]:
        """
        List tasks

        Args:
            limit: Maximum number of tasks
            offset: Offset for pagination
            status_filter: Filter by status
            orphan_only: Show only orphan tasks

        Returns:
            List of tasks
        """
        return self.task_manager.list_tasks(
            limit=limit,
            offset=offset,
            status_filter=status_filter,
            orphan_only=orphan_only
        )

    def get_valid_transitions(self, task_id: str) -> List[str]:
        """
        Get valid transitions for a task

        Args:
            task_id: Task ID

        Returns:
            List of valid target states

        Raises:
            TaskNotFoundError: If task doesn't exist
        """
        task = self.get_task(task_id)
        if not task:
            raise TaskNotFoundError(task_id)

        return list(self.state_machine.get_valid_transitions(task.status))

    def get_transition_history(self, task_id: str) -> list:
        """
        Get state transition history for a task

        Args:
            task_id: Task ID

        Returns:
            List of transition records (most recent first)
        """
        return self.state_machine.get_transition_history(task_id)

    # =========================================================================
    # LINEAGE AND AUDIT (Delegated to TaskManager)
    # =========================================================================

    def add_lineage(
        self,
        task_id: str,
        kind: str,
        ref_id: str,
        phase: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add lineage entry to task"""
        self.task_manager.add_lineage(task_id, kind, ref_id, phase, metadata)

    def get_lineage(self, task_id: str) -> List[TaskLineageEntry]:
        """Get all lineage entries for a task"""
        return self.task_manager.get_lineage(task_id)

    def get_trace(self, task_id: str) -> Optional[TaskTrace]:
        """Get task trace (shallow by default)"""
        return self.task_manager.get_trace(task_id)

    def add_audit(
        self,
        task_id: str,
        event_type: str,
        level: str = "info",
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add audit event"""
        self.task_manager.add_audit(task_id, event_type, level, payload)

    # =========================================================================
    # GUARDIAN INTEGRATION (Read-only overlay)
    # =========================================================================

    def get_guardian_reviews(self, task_id: str) -> List[Any]:
        """
        获取某个 Task 的所有 Guardian 验收记录

        这是一个只读叠加层，不影响 Task 状态机。
        Guardian 是验收事实记录器，独立于 Task 状态。

        Args:
            task_id: Task ID

        Returns:
            List of GuardianReview objects

        Example:
            ```python
            service = TaskService()
            reviews = service.get_guardian_reviews("task_123")
            for review in reviews:
                print(f"{review.verdict}: {review.confidence}")
            ```
        """
        try:
            from agentos.core.guardian import GuardianService
            guardian_service = GuardianService(db_path=self.db_path)
            return guardian_service.get_reviews_by_target("task", task_id)
        except ImportError:
            logger.warning("Guardian module not available")
            return []
        except Exception as e:
            logger.error(f"Failed to get guardian reviews for task {task_id}: {e}")
            return []
