"""Error Handlers for v0.31 API - Project-Aware Task OS

Unified error handling middleware for v0.4 custom exceptions.
Returns structured JSON errors with reason_code, message, and hint.

Created for Task #4 Phase 3: RESTful API Implementation
"""

import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from agentos.core.project.errors import (
    ProjectError,
    ProjectNotFoundError,
    ProjectNameConflictError,
    ProjectHasTasksError,
    RepoError,
    RepoNotFoundError,
    RepoNameConflictError,
    RepoNotInProjectError,
    InvalidPathError,
    PathNotFoundError,
    SpecError,
    SpecNotFoundError,
    SpecAlreadyFrozenError,
    SpecIncompleteError,
    SpecValidationError,
    BindingError,
    BindingNotFoundError,
    BindingAlreadyExistsError,
    InvalidWorkdirError,
    BindingValidationError,
    ArtifactError,
    ArtifactNotFoundError,
    InvalidKindError,
    UnsafePathError,
    ArtifactPathNotFoundError,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Error Mapping
# ============================================================================

# Maps error classes to HTTP status codes
ERROR_STATUS_CODES = {
    # Project errors
    ProjectNotFoundError: 404,
    ProjectNameConflictError: 400,
    ProjectHasTasksError: 400,

    # Repo errors
    RepoNotFoundError: 404,
    RepoNameConflictError: 400,
    RepoNotInProjectError: 400,
    InvalidPathError: 400,
    PathNotFoundError: 400,

    # Spec errors
    SpecNotFoundError: 404,
    SpecAlreadyFrozenError: 400,
    SpecIncompleteError: 400,
    SpecValidationError: 400,

    # Binding errors
    BindingNotFoundError: 404,
    BindingAlreadyExistsError: 400,
    InvalidWorkdirError: 400,
    BindingValidationError: 400,

    # Artifact errors
    ArtifactNotFoundError: 404,
    InvalidKindError: 400,
    UnsafePathError: 400,
    ArtifactPathNotFoundError: 400,
}

# Maps error classes to helpful hints
ERROR_HINTS = {
    # Project errors
    ProjectNotFoundError: "Verify the project_id is correct. Use GET /api/projects to list all projects.",
    ProjectNameConflictError: "Choose a different project name. Names must be unique across all projects.",
    ProjectHasTasksError: "Archive the project instead, or use force=true to attempt deletion (may fail).",

    # Repo errors
    RepoNotFoundError: "Verify the repo_id is correct. Use GET /api/repos to list repositories.",
    RepoNameConflictError: "Choose a different repository name within this project.",
    RepoNotInProjectError: "The repository must belong to the same project as the task.",
    InvalidPathError: "Provide an absolute path (for repos) or relative path without '..' (for workdir).",
    PathNotFoundError: "Ensure the path exists on the filesystem before adding the repository.",

    # Spec errors
    SpecNotFoundError: "Create a spec for this task first using the spec service.",
    SpecAlreadyFrozenError: "Cannot modify a frozen spec. Create a new task instead.",
    SpecIncompleteError: "Ensure the spec has a title and at least one acceptance criterion.",
    SpecValidationError: "Check the spec fields for validation errors.",

    # Binding errors
    BindingNotFoundError: "Create a binding for this task first using POST /api/tasks/{id}/bind.",
    BindingAlreadyExistsError: "A binding already exists for this task. Use update instead.",
    InvalidWorkdirError: "Workdir must be a relative path without '..' components.",
    BindingValidationError: "Ensure project_id is set and spec is frozen before marking task ready.",

    # Artifact errors
    ArtifactNotFoundError: "Verify the artifact_id is correct.",
    InvalidKindError: "Kind must be one of: file, dir, url, log, report.",
    UnsafePathError: "Path contains unsafe characters or patterns.",
    ArtifactPathNotFoundError: "The artifact file or directory does not exist.",
}


# ============================================================================
# Exception Handlers
# ============================================================================


async def handle_project_error(request: Request, exc: ProjectError) -> JSONResponse:
    """Handle ProjectError and subclasses"""
    status_code = ERROR_STATUS_CODES.get(type(exc), 500)
    hint = ERROR_HINTS.get(type(exc), "Check the error message for details.")

    logger.warning(f"Project error: {exc.reason_code} - {exc.message}")

    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "reason_code": exc.reason_code,
            "message": exc.message,
            "hint": hint,
            "context": exc.context if hasattr(exc, 'context') else None,
        }
    )


async def handle_repo_error(request: Request, exc: RepoError) -> JSONResponse:
    """Handle RepoError and subclasses"""
    status_code = ERROR_STATUS_CODES.get(type(exc), 500)
    hint = ERROR_HINTS.get(type(exc), "Check the error message for details.")

    logger.warning(f"Repo error: {exc.reason_code} - {exc.message}")

    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "reason_code": exc.reason_code,
            "message": exc.message,
            "hint": hint,
            "context": exc.context if hasattr(exc, 'context') else None,
        }
    )


async def handle_spec_error(request: Request, exc: SpecError) -> JSONResponse:
    """Handle SpecError and subclasses"""
    status_code = ERROR_STATUS_CODES.get(type(exc), 500)
    hint = ERROR_HINTS.get(type(exc), "Check the error message for details.")

    logger.warning(f"Spec error: {exc.reason_code} - {exc.message}")

    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "reason_code": exc.reason_code,
            "message": exc.message,
            "hint": hint,
            "context": exc.context if hasattr(exc, 'context') else None,
        }
    )


async def handle_binding_error(request: Request, exc: BindingError) -> JSONResponse:
    """Handle BindingError and subclasses"""
    status_code = ERROR_STATUS_CODES.get(type(exc), 500)
    hint = ERROR_HINTS.get(type(exc), "Check the error message for details.")

    logger.warning(f"Binding error: {exc.reason_code} - {exc.message}")

    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "reason_code": exc.reason_code,
            "message": exc.message,
            "hint": hint,
            "context": exc.context if hasattr(exc, 'context') else None,
        }
    )


async def handle_artifact_error(request: Request, exc: ArtifactError) -> JSONResponse:
    """Handle ArtifactError and subclasses"""
    status_code = ERROR_STATUS_CODES.get(type(exc), 500)
    hint = ERROR_HINTS.get(type(exc), "Check the error message for details.")

    logger.warning(f"Artifact error: {exc.reason_code} - {exc.message}")

    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "reason_code": exc.reason_code,
            "message": exc.message,
            "hint": hint,
            "context": exc.context if hasattr(exc, 'context') else None,
        }
    )


# ============================================================================
# Registration Function
# ============================================================================


def register_v31_error_handlers(app: FastAPI) -> None:
    """Register v0.31 error handlers with FastAPI app

    Args:
        app: FastAPI application instance

    Usage:
        from agentos.webui.api.error_handlers_v31 import register_v31_error_handlers

        app = FastAPI()
        register_v31_error_handlers(app)
    """
    # Register handlers for each error class
    app.add_exception_handler(ProjectError, handle_project_error)
    app.add_exception_handler(RepoError, handle_repo_error)
    app.add_exception_handler(SpecError, handle_spec_error)
    app.add_exception_handler(BindingError, handle_binding_error)
    app.add_exception_handler(ArtifactError, handle_artifact_error)

    logger.info("v0.31 error handlers registered successfully")


# ============================================================================
# Error Response Helper
# ============================================================================


def create_error_response(
    reason_code: str,
    message: str,
    hint: str = None,
    context: dict = None
) -> dict:
    """Create standardized error response

    Args:
        reason_code: Error code (e.g., "PROJECT_NOT_FOUND")
        message: Human-readable error message
        hint: Optional hint for resolution
        context: Optional context dictionary

    Returns:
        Standardized error response dict

    Example:
        return JSONResponse(
            status_code=404,
            content=create_error_response(
                reason_code="PROJECT_NOT_FOUND",
                message="Project not found",
                hint="Verify the project_id is correct",
                context={"project_id": "proj_123"}
            )
        )
    """
    return {
        "success": False,
        "reason_code": reason_code,
        "message": message,
        "hint": hint,
        "context": context,
    }
