"""MCP preflight report models."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class PreflightCheck(BaseModel):
    """Single preflight check result."""

    name: str
    ok: bool
    details: str = ""


class PreflightAction(BaseModel):
    """Planned action required to satisfy preflight checks."""

    type: str
    tool: str
    method: str
    commands: List[str] = Field(default_factory=list)
    details: str = ""


class PreflightReport(BaseModel):
    """Standard preflight output contract for MCP server enablement."""

    ok: bool
    checks: List[PreflightCheck] = Field(default_factory=list)
    planned_actions: List[PreflightAction] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
