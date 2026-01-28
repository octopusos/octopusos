"""
Skills API - Skills registry

GET /api/skills - List available skills
GET /api/skills/{name} - Get skill details
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

router = APIRouter()


class Skill(BaseModel):
    """Skill model"""
    name: str
    version: str
    description: str
    input_schema: Dict[str, Any] = {}
    output_schema: Dict[str, Any] = {}
    executable: bool = True
    last_execution: Optional[str] = None
    metadata: Dict[str, Any] = {}


# Placeholder skills (TODO: integrate with actual skill registry)
_skills: Dict[str, Skill] = {
    "chat": Skill(
        name="chat",
        version="1.0.0",
        description="Chat with LLM",
        input_schema={"type": "object", "properties": {"message": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"response": {"type": "string"}}},
        executable=True,
    ),
    "task": Skill(
        name="task",
        version="1.0.0",
        description="Execute task",
        input_schema={"type": "object", "properties": {"title": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"task_id": {"type": "string"}}},
        executable=True,
    ),
}


@router.get("")
async def list_skills() -> List[Skill]:
    """List all available skills"""
    return list(_skills.values())


@router.get("/{name}")
async def get_skill(name: str) -> Skill:
    """Get skill details by name"""
    if name not in _skills:
        raise HTTPException(status_code=404, detail="Skill not found")

    return _skills[name]
