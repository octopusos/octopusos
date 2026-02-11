"""Frontdesk Chat API (v3.1 MVP)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import BaseModel, Field

import re

from octopusos.core.frontdesk.intent import parse_frontdesk_request
from octopusos.core.frontdesk.agent_directory import list_registered_agents, resolve_agent_mentions, suggest_agents
from octopusos.core.dispatch import DispatchRepo, DispatchProposal, calculate_risk
from octopusos.core.frontdesk.message_repo import FrontdeskMessageRepo, FrontdeskMessageRecord, generate_message_id
from octopusos.core.db import registry_db
from octopusos.core.time import utc_now_ms, utc_now_iso
from octopusos.store.timestamp_utils import from_epoch_ms

router = APIRouter()


class FrontdeskAgentSuggestionItem(BaseModel):
    agent_id: str
    title: str
    score: float


class FrontdeskChatMeta(BaseModel):
    intent: str
    agents: list[str]
    raw_mentions: list[str] = Field(default_factory=list)
    agent_resolution: str
    reason_code: str
    agent_suggestions: list[FrontdeskAgentSuggestionItem] = Field(default_factory=list)
    scope: Dict[str, Any]
    task_id: Optional[str] = None
    updated_at: str
    proposal_id: Optional[str] = None
    next_actions: list[str] = Field(default_factory=list)


class FrontdeskChatResponseModel(BaseModel):
    message_id: str
    assistant_text: str
    evidence_refs: list[str]
    meta: FrontdeskChatMeta
    agent_resolution: str
    reason_code: str
    created_at: str


class FrontdeskOverviewAgentItem(BaseModel):
    agent_id: str
    status: str


class FrontdeskOverviewTasksSummary(BaseModel):
    done: int
    in_progress: int
    blocked: int


class FrontdeskOverviewResponseModel(BaseModel):
    agents: list[FrontdeskOverviewAgentItem]
    tasks_summary: FrontdeskOverviewTasksSummary
    top_blockers: list[Dict[str, Any]]


def _iso_from_ms(ms: int) -> str:
    dt = from_epoch_ms(ms)
    if dt is None:
        return utc_now_iso()
    return dt.isoformat().replace('+00:00', 'Z')


def _ensure_db_ready() -> None:
    conn = registry_db.get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS frontdesk_messages (
            id TEXT PRIMARY KEY,
            role TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            evidence_json TEXT NOT NULL,
            meta_json TEXT,
            scope_json TEXT,
            CHECK(role IN ('user', 'assistant', 'system')),
            CHECK(created_at > 0)
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_frontdesk_messages_created_at
        ON frontdesk_messages(created_at DESC)
        """
    )
    conn.commit()


def _build_assistant_text(intent: str, agents: List[str]) -> str:
    if intent == "TODO":
        if agents:
            return f"Pending TODO list requested for {', '.join(agents)}."
        return "Pending TODO list requested."
    if intent == "STATUS":
        if agents:
            return f"Status check requested for {', '.join(agents)}."
        return "Status check requested."
    if intent == "REPORT":
        return "Report summary requested."
    if intent == "BLOCKER":
        return "Blocker overview requested."
    if intent == "GLOBAL":
        return "Global overview requested."
    if intent in {"ASSIGN", "PRIORITIZE", "PAUSE", "RESUME", "RUN"}:
        return "Dispatch proposal created and queued for review."
    return "Frontdesk received your request."


def _extract_task_id(text: str) -> Optional[str]:
    match = re.search(r"\b(T-\d+|task[_-]?\d+)\b", text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def _extract_priority(text: str) -> Optional[str]:
    match = re.search(r"\bP([0-3])\b", text, re.IGNORECASE)
    if match:
        return f"P{match.group(1)}"
    return None


def _build_dispatch_payload(intent: str, text: str, agents: List[str]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"raw_text": text}
    task_id = _extract_task_id(text)
    priority = _extract_priority(text)

    if task_id:
        payload["task_id"] = task_id
    if priority:
        payload["to_priority"] = priority

    if agents:
        payload["agents"] = agents

    return payload


def _proposal_type_for_intent(intent: str) -> Optional[str]:
    mapping = {
        "ASSIGN": "reassign_task",
        "PRIORITIZE": "reprioritize_task",
        "PAUSE": "pause_agent",
        "RESUME": "resume_agent",
        "RUN": "run_pipeline",
    }
    return mapping.get(intent)


@router.post("/api/frontdesk/chat")
def frontdesk_chat(payload: Dict[str, Any] = Body(...)) -> FrontdeskChatResponseModel:
    _ensure_db_ready()
    text = payload.get("text", "")
    if not isinstance(text, str) or not text.strip():
        raise HTTPException(status_code=400, detail="text is required")

    scope = payload.get("scope") or {"type": "global"}
    if not isinstance(scope, dict) or "type" not in scope:
        scope = {"type": "global"}

    parsed = parse_frontdesk_request(text, payload.get("mentions"))
    intent = parsed["intent"]
    raw_mentions = parsed["mentions"]
    agents, agent_resolution, reason_code = resolve_agent_mentions(raw_mentions)
    agent_suggestions: list[Dict[str, Any]] = []
    if raw_mentions and reason_code in {"AGENT_NOT_FOUND", "AGENT_PARTIAL_FOUND"}:
        directory = list_registered_agents(limit=500)
        resolved_set = set(agents)
        unresolved_mentions = [mention for mention in raw_mentions if mention not in resolved_set]
        by_agent_id: dict[str, Dict[str, Any]] = {}
        for mention in unresolved_mentions:
            for item in suggest_agents(mention, directory, limit=5):
                current = by_agent_id.get(item["agent_id"])
                if current is None or float(item.get("score", 0.0)) > float(current.get("score", 0.0)):
                    by_agent_id[item["agent_id"]] = item
        agent_suggestions = sorted(
            by_agent_id.values(),
            key=lambda item: (float(item.get("score", 0.0)), item["agent_id"]),
            reverse=True,
        )[:5]

    now_ms = utc_now_ms()
    now_iso = _iso_from_ms(now_ms)

    repo = FrontdeskMessageRepo()

    user_message = FrontdeskMessageRecord(
        id=generate_message_id(),
        role="user",
        text=text,
        created_at=now_ms,
        evidence_refs=[],
        meta={
            "intent": intent,
            "agents": agents,
            "raw_mentions": raw_mentions,
            "agent_resolution": agent_resolution,
            "reason_code": reason_code,
            "agent_suggestions": agent_suggestions,
            "scope": scope,
        },
        scope=scope,
    )
    repo.create(user_message)

    proposal_id = None
    next_actions = []
    assistant_text = _build_assistant_text(intent, agents)

    if intent in {"ASSIGN", "PRIORITIZE", "PAUSE", "RESUME", "RUN"}:
        dispatch_repo = DispatchRepo()
        dispatch_repo.ensure_tables()

        proposal_type = _proposal_type_for_intent(intent)
        payload_data = _build_dispatch_payload(intent, text, agents)
        risk_level = calculate_risk(proposal_type or "reassign_task", payload_data)
        proposal_id = f"dp_{now_ms}_{proposal_type}"

        proposal = DispatchProposal(
            proposal_id=proposal_id,
            source="frontdesk",
            proposal_type=proposal_type or "reassign_task",
            status="pending",
            risk_level=risk_level,
            scope=scope,
            payload=payload_data,
            reason=payload.get("reason") or "Frontdesk proposal",
            evidence_refs=[],
            requested_by=payload.get("requested_by") or "frontdesk",
            requested_at=now_ms,
            reviewed_by=None,
            reviewed_at=None,
            review_comment=None,
            execution_ref=None,
            created_at=now_ms,
            updated_at=now_ms,
        )

        dispatch_repo.create_proposal(proposal)
        dispatch_repo.append_audit(
            proposal_id,
            "create",
            proposal.requested_by,
            {
                "status_before": None,
                "status_after": "pending",
                "evidence_refs": proposal.evidence_refs,
            },
        )
        next_actions = ["open_review_queue", "approve_proposal"]
        assistant_text = f"Dispatch proposal {proposal_id} created. Awaiting review."

    assistant_meta = {
        "intent": intent,
        "agents": agents,
        "raw_mentions": raw_mentions,
        "agent_resolution": agent_resolution,
        "reason_code": reason_code,
        "agent_suggestions": agent_suggestions,
        "scope": scope,
        "task_id": None,
        "updated_at": now_iso,
        "proposal_id": proposal_id,
        "next_actions": next_actions,
    }

    assistant_message_id = generate_message_id()
    assistant_message = FrontdeskMessageRecord(
        id=assistant_message_id,
        role="assistant",
        text=assistant_text,
        created_at=now_ms,
        evidence_refs=[],
        meta=assistant_meta,
        scope=scope,
    )
    repo.create(assistant_message)

    return FrontdeskChatResponseModel(
        message_id=assistant_message_id,
        assistant_text=assistant_text,
        evidence_refs=[],
        meta=assistant_meta,
        agent_resolution=agent_resolution,
        reason_code=reason_code,
        created_at=now_iso,
    )


@router.get("/api/frontdesk/history")
def frontdesk_history(limit: int = Query(200, ge=1, le=500)):
    _ensure_db_ready()
    repo = FrontdeskMessageRepo()
    records = repo.list_recent(limit)

    messages = [
        {
            "id": record.id,
            "role": record.role,
            "text": record.text,
            "created_at": _iso_from_ms(record.created_at),
            "evidence_refs": record.evidence_refs or [],
            "meta": record.meta or {},
        }
        for record in records
    ]

    return {"messages": messages}


@router.get("/api/frontdesk/overview")
def frontdesk_overview() -> FrontdeskOverviewResponseModel:
    _ensure_db_ready()
    agents = [
        {"agent_id": agent["agent_id"], "status": agent["lifecycle"]}
        for agent in list_registered_agents(limit=500)
    ]
    return FrontdeskOverviewResponseModel(
        agents=agents,
        tasks_summary=FrontdeskOverviewTasksSummary(done=0, in_progress=0, blocked=0),
        top_blockers=[],
    )
