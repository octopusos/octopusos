"""Agent directory helpers backed by content_registry."""

from __future__ import annotations

import difflib
import json
import re
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from octopusos.core.db import registry_db


def _title_from_agent_id(agent_id: str) -> str:
    words = [w for w in re.split(r"[_\-\s]+", agent_id) if w]
    if not words:
        return agent_id
    return " ".join(word.capitalize() for word in words)


def list_registered_agents(
    *,
    status: Optional[str] = None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    conn = registry_db.get_db()

    where = ["type = 'agent'"]
    params: List[Any] = []
    if status:
        where.append("status = ?")
        params.append(status)
    where_sql = " AND ".join(where)
    params.append(limit)

    try:
        rows = conn.execute(
            f"""
            SELECT id, version, status, metadata, spec
            FROM content_registry
            WHERE {where_sql}
            ORDER BY id ASC
            LIMIT ?
            """,
            params,
        ).fetchall()
    except sqlite3.OperationalError:
        # content_registry may not exist on uninitialized/partial DBs.
        return []

    agents: List[Dict[str, Any]] = []
    for row in rows:
        metadata = {}
        spec = {}
        try:
            metadata = json.loads(row["metadata"] or "{}")
        except Exception:
            metadata = {}
        try:
            spec = json.loads(row["spec"] or "{}")
        except Exception:
            spec = {}

        agent_id = str(row["id"])
        roles = spec.get("metadata", {}).get("real_world_roles") or metadata.get("real_world_roles") or []
        title = roles[0] if roles else _title_from_agent_id(agent_id)
        responsibilities = spec.get("responsibilities") or []

        agents.append(
            {
                "agent_id": agent_id,
                "title": title,
                "category": spec.get("category") or metadata.get("category") or "unknown",
                "version": row["version"],
                "lifecycle": row["status"],
                "responsibilities": responsibilities[:5],
            }
        )
    return agents


def resolve_agent_mentions(mentions: List[str]) -> Tuple[List[str], str, str]:
    if not mentions:
        return [], "none", "NO_MENTION"

    known = {agent["agent_id"].lower() for agent in list_registered_agents(limit=500)}
    ordered_unique_mentions = list(dict.fromkeys(name.lower() for name in mentions))
    resolved = [name for name in ordered_unique_mentions if name in known]

    if not resolved:
        return [], "unresolved", "AGENT_NOT_FOUND"
    if len(resolved) != len(ordered_unique_mentions):
        return resolved, "partial", "AGENT_PARTIAL_FOUND"
    return resolved, "resolved", "AGENT_FOUND"


def _normalize_token(value: str) -> str:
    return re.sub(r"[_\-\s]+", "", value.lower()).strip()


def suggest_agents(
    query: str,
    agents: List[Dict[str, Any]],
    limit: int = 5,
    min_score: float = 0.6,
) -> List[Dict[str, Any]]:
    """Suggest closest agent candidates for an unresolved mention."""
    q = query.strip().lstrip("@").lower()
    if not q:
        return []

    q_norm = _normalize_token(q)
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for agent in agents:
        agent_id = str(agent.get("agent_id", "")).strip()
        if not agent_id:
            continue

        title = str(agent.get("title", "")).strip()
        agent_norm = _normalize_token(agent_id)
        title_norm = _normalize_token(title)

        score = 0.0
        if q_norm == agent_norm or (title_norm and q_norm == title_norm):
            score = 1.0
        elif agent_norm.startswith(q_norm) or (title_norm and title_norm.startswith(q_norm)):
            score = 0.92
        elif q_norm in agent_norm or (title_norm and q_norm in title_norm):
            score = 0.82
        else:
            ratio_id = difflib.SequenceMatcher(None, q_norm, agent_norm).ratio()
            ratio_title = difflib.SequenceMatcher(None, q_norm, title_norm).ratio() if title_norm else 0.0
            score = max(ratio_id, ratio_title)

        if score >= min_score:
            scored.append(
                (
                    score,
                    {
                        "agent_id": agent_id,
                        "title": title or _title_from_agent_id(agent_id),
                        "score": round(score, 3),
                    },
                )
            )

    scored.sort(key=lambda item: (item[0], item[1]["agent_id"]), reverse=True)
    deduped: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for _, item in scored:
        if item["agent_id"] in seen:
            continue
        seen.add(item["agent_id"])
        deduped.append(item)
        if len(deduped) >= limit:
            break
    return deduped
