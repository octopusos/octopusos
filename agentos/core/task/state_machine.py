"""
Task State Machine

Core state machine implementation for task lifecycle management.
Provides state transition validation, execution, and history tracking.
"""

import json
import sqlite3
from typing import Dict, Set, Tuple, Optional, Any
from datetime import datetime, timezone
from pathlib import Path
import logging

from agentos.core.task.states import TaskState, ALL_STATES, TERMINAL_STATES
from agentos.core.task.errors import (
    TaskStateError,
    InvalidTransitionError,
    TaskNotFoundError,
    TaskAlreadyInStateError,
)
from agentos.core.task.models import Task
from agentos.store import get_db

logger = logging.getLogger(__name__)


# State Transition Table
# Maps (from_state, to_state) -> (is_allowed, optional_reason)
TRANSITION_TABLE: Dict[Tuple[TaskState, TaskState], Tuple[bool, Optional[str]]] = {
    # From DRAFT
    (TaskState.DRAFT, TaskState.APPROVED): (True, "Task approved for execution"),
    (TaskState.DRAFT, TaskState.CANCELED): (True, "Task canceled during draft"),

    # From APPROVED
    (TaskState.APPROVED, TaskState.QUEUED): (True, "Task queued for execution"),
    (TaskState.APPROVED, TaskState.CANCELED): (True, "Task canceled after approval"),

    # From QUEUED
    (TaskState.QUEUED, TaskState.RUNNING): (True, "Task execution started"),
    (TaskState.QUEUED, TaskState.CANCELED): (True, "Task canceled while queued"),

    # From RUNNING
    (TaskState.RUNNING, TaskState.VERIFYING): (True, "Task execution completed, verification started"),
    (TaskState.RUNNING, TaskState.FAILED): (True, "Task execution failed"),
    (TaskState.RUNNING, TaskState.CANCELED): (True, "Task canceled during execution"),

    # From VERIFYING
    (TaskState.VERIFYING, TaskState.VERIFIED): (True, "Task verification completed"),
    (TaskState.VERIFYING, TaskState.FAILED): (True, "Task verification failed"),
    (TaskState.VERIFYING, TaskState.CANCELED): (True, "Task canceled during verification"),

    # From VERIFIED
    (TaskState.VERIFIED, TaskState.DONE): (True, "Task marked as done"),

    # From FAILED (optional retry)
    (TaskState.FAILED, TaskState.QUEUED): (True, "Task queued for retry"),
}


class TaskStateMachine:
    """
    Task State Machine

    Manages task state transitions with validation, persistence, and audit trail.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize Task State Machine

        Args:
            db_path: Optional path to database (defaults to store default)
        """
        self.db_path = db_path
        self._transition_table = TRANSITION_TABLE

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection"""
        if self.db_path:
            conn = sqlite3.connect(str(self.db_path))
        else:
            conn = get_db()
        conn.row_factory = sqlite3.Row
        return conn

    def can_transition(self, frm: str, to: str) -> bool:
        """
        Check if a transition is allowed

        Args:
            frm: Source state
            to: Target state

        Returns:
            True if transition is allowed, False otherwise
        """
        try:
            from_state = TaskState(frm)
            to_state = TaskState(to)
        except ValueError:
            return False

        # Same state is always allowed (idempotent)
        if from_state == to_state:
            return True

        # Check transition table
        return self._transition_table.get((from_state, to_state), (False, None))[0]

    def validate_or_raise(self, frm: str, to: str) -> None:
        """
        Validate a transition or raise an exception

        Args:
            frm: Source state
            to: Target state

        Raises:
            InvalidTransitionError: If transition is not allowed
            ValueError: If states are invalid
        """
        # Validate states exist
        try:
            from_state = TaskState(frm)
            to_state = TaskState(to)
        except ValueError as e:
            raise InvalidTransitionError(
                from_state=frm,
                to_state=to,
                reason=f"Invalid state value: {str(e)}"
            )

        # Same state is allowed
        if from_state == to_state:
            return

        # Check transition table
        allowed, reason = self._transition_table.get(
            (from_state, to_state),
            (False, "No transition rule defined")
        )

        if not allowed:
            raise InvalidTransitionError(
                from_state=frm,
                to_state=to,
                reason=reason or "Transition not allowed"
            )

    def transition(
        self,
        task_id: str,
        to: str,
        actor: str,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Task:
        """
        Execute a state transition

        This method:
        1. Loads the current task state
        2. Validates the transition
        3. Updates the task state
        4. Records the transition in audit log
        5. Returns the updated task

        Args:
            task_id: Task ID
            to: Target state
            actor: Who/what is performing the transition (user, system, etc.)
            reason: Human-readable reason for transition
            metadata: Optional metadata for the transition

        Returns:
            Updated Task object

        Raises:
            TaskNotFoundError: If task doesn't exist
            InvalidTransitionError: If transition is not allowed
            TaskStateError: For other state machine errors
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        try:
            # Load current task
            cursor.execute(
                "SELECT task_id, title, status, session_id, created_at, updated_at, created_by, metadata "
                "FROM tasks WHERE task_id = ?",
                (task_id,)
            )
            row = cursor.fetchone()

            if not row:
                raise TaskNotFoundError(task_id)

            # Parse current state
            current_state = row["status"]

            # Validate transition
            self.validate_or_raise(current_state, to)

            # Check if already in target state
            if current_state == to:
                logger.debug(f"Task {task_id} already in state '{to}', no transition needed")
                # Return current task without changes
                task_metadata = json.loads(row["metadata"]) if row["metadata"] else {}
                return Task(
                    task_id=row["task_id"],
                    title=row["title"],
                    status=row["status"],
                    session_id=row["session_id"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    created_by=row["created_by"],
                    metadata=task_metadata,
                )

            # Perform transition
            now = datetime.now(timezone.utc).isoformat()

            # Update task state
            cursor.execute(
                "UPDATE tasks SET status = ?, updated_at = ? WHERE task_id = ?",
                (to, now, task_id)
            )

            # Record transition in audit log
            audit_payload = {
                "from_state": current_state,
                "to_state": to,
                "actor": actor,
                "reason": reason,
                "transition_metadata": metadata or {},
            }

            cursor.execute(
                """
                INSERT INTO task_audits (task_id, level, event_type, payload, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    "info",
                    f"STATE_TRANSITION_{to.upper()}",
                    json.dumps(audit_payload),
                    now
                )
            )

            conn.commit()

            # Load and return updated task
            cursor.execute(
                "SELECT task_id, title, status, session_id, created_at, updated_at, created_by, metadata "
                "FROM tasks WHERE task_id = ?",
                (task_id,)
            )
            row = cursor.fetchone()
            task_metadata = json.loads(row["metadata"]) if row["metadata"] else {}

            logger.info(
                f"Task {task_id} transitioned from '{current_state}' to '{to}' "
                f"by {actor}: {reason}"
            )

            return Task(
                task_id=row["task_id"],
                title=row["title"],
                status=row["status"],
                session_id=row["session_id"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                created_by=row["created_by"],
                metadata=task_metadata,
            )

        except (InvalidTransitionError, TaskNotFoundError):
            conn.rollback()
            raise
        except Exception as e:
            conn.rollback()
            logger.error(f"Error during state transition for task {task_id}: {str(e)}")
            raise TaskStateError(
                f"Failed to transition task: {str(e)}",
                task_id=task_id
            )
        finally:
            conn.close()

    def get_valid_transitions(self, from_state: str) -> Set[str]:
        """
        Get all valid transitions from a given state

        Args:
            from_state: Source state

        Returns:
            Set of valid target states
        """
        try:
            state = TaskState(from_state)
        except ValueError:
            return set()

        valid_targets = set()
        for (frm, to), (allowed, _) in self._transition_table.items():
            if frm == state and allowed:
                valid_targets.add(to.value)

        return valid_targets

    def get_transition_history(self, task_id: str) -> list:
        """
        Get state transition history for a task

        Args:
            task_id: Task ID

        Returns:
            List of transition records (most recent first)
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT audit_id, task_id, level, event_type, payload, created_at
                FROM task_audits
                WHERE task_id = ? AND event_type LIKE 'STATE_TRANSITION_%'
                ORDER BY created_at DESC
                """,
                (task_id,)
            )

            history = []
            for row in cursor.fetchall():
                payload = json.loads(row["payload"]) if row["payload"] else {}
                history.append({
                    "audit_id": row["audit_id"],
                    "task_id": row["task_id"],
                    "level": row["level"],
                    "event_type": row["event_type"],
                    "from_state": payload.get("from_state"),
                    "to_state": payload.get("to_state"),
                    "actor": payload.get("actor"),
                    "reason": payload.get("reason"),
                    "metadata": payload.get("transition_metadata", {}),
                    "created_at": row["created_at"],
                })

            return history

        finally:
            conn.close()

    def is_terminal_state(self, state: str) -> bool:
        """
        Check if a state is terminal

        Args:
            state: State to check

        Returns:
            True if terminal, False otherwise
        """
        try:
            return TaskState(state) in TERMINAL_STATES
        except ValueError:
            return False
