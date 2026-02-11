from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


WorkStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]
WorkType = Literal["investigation", "repair", "summary", "recovery", "maintenance"]

TaskStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]
TaskRisk = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class WorkItem:
    work_id: str
    type: WorkType
    title: str
    status: WorkStatus
    priority: int
    scope_type: str
    scope_id: str
    source_card_id: Optional[str]
    created_at_ms: int
    updated_at_ms: int
    started_at_ms: Optional[int]
    finished_at_ms: Optional[int]
    summary: str
    detail_json: str
    evidence_ref_json: str


@dataclass(frozen=True)
class ExecTask:
    task_id: str
    work_id: Optional[str]
    card_id: Optional[str]
    task_type: str
    status: TaskStatus
    risk_level: TaskRisk
    requires_confirmation: bool
    created_at_ms: int
    updated_at_ms: int
    started_at_ms: Optional[int]
    finished_at_ms: Optional[int]
    input_json: str
    output_json: str
    error_json: Optional[str]
    evidence_paths_json: str
    idempotency_key: str


@dataclass(frozen=True)
class RunResult:
    ok: bool
    output_json: str
    evidence_paths: list[str]
    error_json: Optional[str] = None

