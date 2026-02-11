"""Normalize proposal + endpoint metadata into executable mapping json."""

from __future__ import annotations

from typing import Any, Dict

from .proposal_schema import MappingProposal


def _pick_path(proposal: MappingProposal, direct: str, role: str) -> str:
    if direct:
        return direct
    candidates = proposal.path_candidates.get(role) if isinstance(proposal.path_candidates, dict) else None
    if isinstance(candidates, list) and candidates:
        first = candidates[0]
        if hasattr(first, "path"):
            return str(first.path or "")
        if isinstance(first, dict):
            return str(first.get("path") or "")
    return ""


def normalize_mapping(
    *,
    endpoint_url: str,
    method: str,
    proposal: MappingProposal,
    headers: Dict[str, str] | None = None,
    query: Dict[str, str] | None = None,
) -> Dict[str, Any]:
    response: Dict[str, Any] = {
        "kind": proposal.response_kind,
    }
    time_path = _pick_path(proposal, proposal.time_path, "time")
    value_path = _pick_path(proposal, proposal.value_path, "value")
    points_path = _pick_path(proposal, str(proposal.points_path or ""), "points")
    summary_path = _pick_path(proposal, str(proposal.summary_path or ""), "summary")
    if time_path:
        response["time_path"] = time_path
    if value_path:
        response["value_path"] = value_path
    if points_path:
        response["points_path"] = points_path
    if summary_path:
        response["summary_path"] = summary_path

    mapping: Dict[str, Any] = {
        "method": (method or proposal.method or "GET").upper(),
        "url": endpoint_url,
        "response": response,
    }
    if headers:
        mapping["headers"] = headers
    if query:
        mapping["query"] = query
    return mapping
