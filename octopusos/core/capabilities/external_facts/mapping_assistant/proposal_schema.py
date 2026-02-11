"""Schema for LLM-generated endpoint mapping proposals."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Dict, List, Literal, Optional


class SemanticPathCandidate(BaseModel):
    path: str
    score: float = Field(default=0.5, ge=0.0, le=1.0)
    reason: str = ""


class MappingProposal(BaseModel):
    response_kind: Literal["point", "series", "table"]
    time_path: str = ""
    value_path: str = ""
    points_path: Optional[str] = None
    summary_path: Optional[str] = None
    method: str = "GET"
    reasoning: str = Field(default="", max_length=300)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    semantic_roles: Dict[str, str] = Field(default_factory=dict)
    path_candidates: Dict[str, List[SemanticPathCandidate]] = Field(default_factory=dict)
