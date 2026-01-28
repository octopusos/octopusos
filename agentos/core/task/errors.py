"""
Task State Machine Errors

Custom exceptions for task state machine operations.
"""


class TaskStateError(Exception):
    """
    Base exception for task state machine errors

    Raised when a state machine operation fails due to invalid state,
    transition rules, or other state-related issues.
    """

    def __init__(self, message: str, task_id: str = None, **kwargs):
        """
        Initialize TaskStateError

        Args:
            message: Error message
            task_id: Optional task ID for context
            **kwargs: Additional error context
        """
        self.message = message
        self.task_id = task_id
        self.context = kwargs
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format error message with context"""
        parts = [self.message]
        if self.task_id:
            parts.append(f"(task_id: {self.task_id})")
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"[{context_str}]")
        return " ".join(parts)


class InvalidTransitionError(TaskStateError):
    """
    Exception raised when an invalid state transition is attempted

    This error is raised when attempting to transition a task from one state
    to another state that is not allowed by the state machine rules.
    """

    def __init__(
        self,
        from_state: str,
        to_state: str,
        task_id: str = None,
        reason: str = None
    ):
        """
        Initialize InvalidTransitionError

        Args:
            from_state: Current state
            to_state: Target state (invalid)
            task_id: Optional task ID
            reason: Optional reason for why transition is invalid
        """
        self.from_state = from_state
        self.to_state = to_state

        message = f"Invalid transition from '{from_state}' to '{to_state}'"
        if reason:
            message += f": {reason}"

        super().__init__(
            message=message,
            task_id=task_id,
            from_state=from_state,
            to_state=to_state
        )


class TaskNotFoundError(TaskStateError):
    """
    Exception raised when a task is not found in the database

    This error is raised when attempting to perform a state transition
    on a task that doesn't exist.
    """

    def __init__(self, task_id: str):
        """
        Initialize TaskNotFoundError

        Args:
            task_id: ID of the task that was not found
        """
        super().__init__(
            message=f"Task not found",
            task_id=task_id
        )


class TaskAlreadyInStateError(TaskStateError):
    """
    Exception raised when attempting to transition to the current state

    This is typically not an error condition, but can be used to signal
    that no action was taken because the task is already in the target state.
    """

    def __init__(self, task_id: str, state: str):
        """
        Initialize TaskAlreadyInStateError

        Args:
            task_id: Task ID
            state: Current state (same as target state)
        """
        super().__init__(
            message=f"Task is already in state '{state}'",
            task_id=task_id,
            state=state
        )
