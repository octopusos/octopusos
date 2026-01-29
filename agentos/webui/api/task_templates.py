"""
Task Templates API

POST /api/task-templates - Create a new template
GET /api/task-templates - List all templates
GET /api/task-templates/{template_id} - Get template details
PUT /api/task-templates/{template_id} - Update a template
DELETE /api/task-templates/{template_id} - Delete a template
POST /api/task-templates/{template_id}/tasks - Create a task from template
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
import logging

from agentos.core.task.template_service import TemplateService
from agentos.core.task.models import TaskTemplate, Task

logger = logging.getLogger(__name__)

router = APIRouter()


class TemplateCreateRequest(BaseModel):
    """Request model for creating a template"""

    name: str = Field(..., min_length=1, max_length=100, description="Template name (1-100 characters)")
    title_template: str = Field(..., min_length=1, max_length=500, description="Task title template")
    description: Optional[str] = Field(None, description="Template description")
    created_by_default: Optional[str] = Field(None, description="Default creator for tasks")
    metadata_template: Optional[Dict[str, Any]] = Field(None, description="Metadata template")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name is not empty after stripping whitespace"""
        if not v.strip():
            raise ValueError("Template name cannot be empty or contain only whitespace")
        return v.strip()

    @field_validator("title_template")
    @classmethod
    def validate_title_template(cls, v: str) -> str:
        """Validate title template is not empty after stripping whitespace"""
        if not v.strip():
            raise ValueError("Title template cannot be empty or contain only whitespace")
        return v.strip()


class TemplateUpdateRequest(BaseModel):
    """Request model for updating a template"""

    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Template name")
    title_template: Optional[str] = Field(None, min_length=1, max_length=500, description="Task title template")
    description: Optional[str] = Field(None, description="Template description")
    created_by_default: Optional[str] = Field(None, description="Default creator for tasks")
    metadata_template: Optional[Dict[str, Any]] = Field(None, description="Metadata template")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate name is not empty if provided"""
        if v is not None and not v.strip():
            raise ValueError("Template name cannot be empty or contain only whitespace")
        return v.strip() if v else None

    @field_validator("title_template")
    @classmethod
    def validate_title_template(cls, v: Optional[str]) -> Optional[str]:
        """Validate title template is not empty if provided"""
        if v is not None and not v.strip():
            raise ValueError("Title template cannot be empty or contain only whitespace")
        return v.strip() if v else None


class CreateTaskFromTemplateRequest(BaseModel):
    """Request model for creating a task from a template"""

    title_override: Optional[str] = Field(None, description="Override template title")
    created_by_override: Optional[str] = Field(None, description="Override default creator")
    metadata_override: Optional[Dict[str, Any]] = Field(None, description="Merge with template metadata")


class TemplateSummary(BaseModel):
    """Template summary for list view"""

    template_id: str
    name: str
    description: Optional[str]
    title_template: str
    use_count: int
    created_at: str
    updated_at: str


@router.post("")
async def create_template(request: TemplateCreateRequest) -> TaskTemplate:
    """
    Create a new task template

    Args:
        request: TemplateCreateRequest with template details

    Returns:
        Created TaskTemplate object

    Example:
        POST /api/task-templates
        {
            "name": "Bug Fix Template",
            "title_template": "Fix bug in module",
            "description": "Standard bug fix workflow",
            "created_by_default": "developer@example.com",
            "metadata_template": {"priority": "medium", "type": "bug"}
        }

    Raises:
        HTTPException: 400 for validation errors, 500 for server errors
    """
    try:
        service = TemplateService()
        template = service.create_template(
            name=request.name,
            title_template=request.title_template,
            description=request.description,
            created_by_default=request.created_by_default,
            metadata_template=request.metadata_template,
            created_by=None,  # TODO: Get from authentication context
        )
        return template

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create template: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create template: {str(e)}")


@router.get("")
async def list_templates(
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    order_by: str = Query("created_at", description="Order by field (created_at, name, use_count)"),
) -> List[TemplateSummary]:
    """
    List all task templates

    Args:
        limit: Maximum number of results (1-200)
        offset: Offset for pagination
        order_by: Order by field (created_at, name, use_count, updated_at)

    Returns:
        List of template summaries

    Example:
        GET /api/task-templates?limit=10&order_by=use_count
    """
    try:
        service = TemplateService()
        templates = service.list_templates(limit=limit, offset=offset, order_by=order_by)

        summaries = [
            TemplateSummary(
                template_id=t.template_id,
                name=t.name,
                description=t.description,
                title_template=t.title_template,
                use_count=t.use_count,
                created_at=t.created_at or "",
                updated_at=t.updated_at or "",
            )
            for t in templates
        ]

        return summaries

    except Exception as e:
        logger.error(f"Failed to list templates: {str(e)}", exc_info=True)
        # Return empty list on error
        return []


@router.get("/{template_id}")
async def get_template(template_id: str) -> TaskTemplate:
    """
    Get template details by ID

    Args:
        template_id: Template ID

    Returns:
        TaskTemplate details

    Example:
        GET /api/task-templates/01HQZX1Y2Z3A4B5C6D7E8F9G0H

    Raises:
        HTTPException: 404 if template not found
    """
    service = TemplateService()
    template = service.get_template(template_id)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return template


@router.put("/{template_id}")
async def update_template(template_id: str, request: TemplateUpdateRequest) -> TaskTemplate:
    """
    Update a template

    Args:
        template_id: Template ID
        request: TemplateUpdateRequest with fields to update

    Returns:
        Updated TaskTemplate object

    Example:
        PUT /api/task-templates/01HQZX1Y2Z3A4B5C6D7E8F9G0H
        {
            "name": "Updated Bug Fix Template",
            "description": "Updated description"
        }

    Raises:
        HTTPException: 404 if not found, 400 for validation errors, 500 for server errors
    """
    try:
        service = TemplateService()
        template = service.update_template(
            template_id=template_id,
            name=request.name,
            title_template=request.title_template,
            description=request.description,
            created_by_default=request.created_by_default,
            metadata_template=request.metadata_template,
        )

        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        return template

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update template: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update template: {str(e)}")


@router.delete("/{template_id}")
async def delete_template(template_id: str) -> Dict[str, Any]:
    """
    Delete a template

    Args:
        template_id: Template ID

    Returns:
        Success message

    Example:
        DELETE /api/task-templates/01HQZX1Y2Z3A4B5C6D7E8F9G0H

    Raises:
        HTTPException: 404 if not found, 500 for server errors
    """
    try:
        service = TemplateService()
        success = service.delete_template(template_id)

        if not success:
            raise HTTPException(status_code=404, detail="Template not found")

        return {"ok": True, "message": f"Template {template_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete template: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete template: {str(e)}")


@router.post("/{template_id}/tasks")
async def create_task_from_template(
    template_id: str,
    request: CreateTaskFromTemplateRequest,
) -> Task:
    """
    Create a task from a template

    Args:
        template_id: Template ID
        request: CreateTaskFromTemplateRequest with optional overrides

    Returns:
        Created Task object

    Example:
        POST /api/task-templates/01HQZX1Y2Z3A4B5C6D7E8F9G0H/tasks
        {
            "title_override": "Fix authentication bug",
            "created_by_override": "user@example.com",
            "metadata_override": {"priority": "high"}
        }

    Raises:
        HTTPException: 404 if template not found, 400 for validation errors, 500 for server errors
    """
    try:
        service = TemplateService()
        task = service.create_task_from_template(
            template_id=template_id,
            title_override=request.title_override,
            created_by_override=request.created_by_override,
            metadata_override=request.metadata_override,
        )
        return task

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create task from template: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create task from template: {str(e)}")
