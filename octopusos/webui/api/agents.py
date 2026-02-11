"""Agents discovery API backed by content_registry."""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from octopusos.core.frontdesk.agent_directory import list_registered_agents

router = APIRouter()


class AgentItem(BaseModel):
    agent_id: str
    title: str
    category: str
    version: str
    lifecycle: str
    responsibilities: list[str]


class AgentsListResponse(BaseModel):
    source: str
    total: int
    agents: list[AgentItem]


@router.get("/api/agents")
def list_agents(
    status: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
) -> AgentsListResponse:
    agents = list_registered_agents(status=status, limit=limit)
    return AgentsListResponse(
        source="content_registry",
        total=len(agents),
        agents=agents,
    )
