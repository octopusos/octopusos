"""LLM-assisted mapping inference with deterministic fallback."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, Iterable, List, Tuple

from .proposal_schema import MappingProposal, SemanticPathCandidate


def _flatten_paths(payload: Any, prefix: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(payload, dict):
        for key, value in payload.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            yield path, value
            yield from _flatten_paths(value, path)
    elif isinstance(payload, list):
        for idx, value in enumerate(payload[:10]):
            path = f"{prefix}.{idx}" if prefix else str(idx)
            yield path, value
            yield from _flatten_paths(value, path)


def _build_semantic_index(sample_json: Dict[str, Any]) -> Dict[str, List[SemanticPathCandidate]]:
    roles: Dict[str, List[SemanticPathCandidate]] = {
        "time": [],
        "value": [],
        "points": [],
        "summary": [],
    }
    for path, value in _flatten_paths(sample_json):
        key_lower = path.lower()
        # time-like
        if any(token in key_lower for token in ("time", "timestamp", "date", "updated", "created")):
            roles["time"].append(SemanticPathCandidate(path=path, score=0.75, reason="time-like key"))
        # value-like
        if isinstance(value, (int, float)) and any(token in key_lower for token in ("value", "rate", "price", "close", "amount", "used", "remaining", "total")):
            roles["value"].append(SemanticPathCandidate(path=path, score=0.78, reason="numeric value-like key"))
        # series points-like
        if isinstance(value, list) and value and all(isinstance(v, (dict, int, float)) for v in value[:5]):
            roles["points"].append(SemanticPathCandidate(path=path, score=0.72, reason="list-like points container"))
        if isinstance(value, dict) and value and all(isinstance(v, dict) for v in value.values()):
            roles["points"].append(SemanticPathCandidate(path=path, score=0.7, reason="map-like points container"))
        # summary-like
        if isinstance(value, str) and any(token in key_lower for token in ("summary", "status", "desc", "message", "condition")):
            roles["summary"].append(SemanticPathCandidate(path=path, score=0.7, reason="summary-like text"))

    for role in roles:
        roles[role] = sorted(roles[role], key=lambda x: x.score, reverse=True)[:8]
    return roles


def _fallback_proposal(*, item_id: str, sample_json: Dict[str, Any], api_doc_text: str = "") -> MappingProposal:
    semantic = _build_semantic_index(sample_json)
    top = lambda role: (semantic.get(role) or [SemanticPathCandidate(path="", score=0.0)])[0].path
    doc_hint = (api_doc_text or "").lower()
    if item_id != "series" and any(token in doc_hint for token in ("historical", "history", "range", "timeseries", "time series", "过去", "历史", "区间")):
        item_id = "series"

    # Deterministic baseline: series for series item, point/table otherwise.
    if item_id == "series":
        points_path = top("points") or "data"
        return MappingProposal(
            response_kind="series",
            method="GET",
            points_path=points_path,
            time_path=top("time") or "key",
            value_path=top("value") or "{quote}.value",
            summary_path=top("summary") or "",
            semantic_roles={"time": "time-like", "value": "numeric value-like", "points": "series container"},
            path_candidates=semantic,
            reasoning="Fallback inference from semantic key-role analysis for series item.",
            confidence=0.72,
        )
    if any(isinstance(v, dict) for v in sample_json.values()):
        return MappingProposal(
            response_kind="table",
            method="GET",
            points_path=top("points") or "",
            time_path=top("time") or "",
            value_path=top("value") or "",
            summary_path=top("summary") or "",
            semantic_roles={"points": "object/list container"},
            path_candidates=semantic,
            reasoning="Fallback inference selected table/object snapshot from nested structure.",
            confidence=0.66,
        )
    return MappingProposal(
        response_kind="point",
        method="GET",
        time_path=top("time") or "meta.last_updated_at",
        value_path=top("value") or "data.{quote}.value",
        summary_path=top("summary") or "",
        semantic_roles={"time": "time-like", "value": "numeric value-like"},
        path_candidates=semantic,
        reasoning="Fallback inference from semantic key-role analysis for point item.",
        confidence=0.68,
    )


def _llm_infer(
    *,
    capability_id: str,
    item_id: str,
    sample_json: Dict[str, Any],
    request_json: Dict[str, Any] | None = None,
    api_doc_text: str = "",
) -> Tuple[MappingProposal | None, str]:
    semantic_index = _build_semantic_index(sample_json)
    prompt = (
        "Infer API response mapping semantics.\n"
        "Return strict JSON only with keys: "
        "response_kind,time_path,value_path,points_path,summary_path,method,reasoning,confidence,semantic_roles,path_candidates.\n"
        "response_kind must be one of point|series|table.\n"
        "Use semantic roles rather than hardcoded key assumptions.\n"
        f"capability_id={capability_id}\n"
        f"item_id={item_id}\n"
        f"semantic_index={json.dumps({k: [c.model_dump() for c in v] for k, v in semantic_index.items()}, ensure_ascii=False)}\n"
        f"request_sample_json={json.dumps(request_json or {}, ensure_ascii=False)}\n"
        f"response_sample_json={json.dumps(sample_json, ensure_ascii=False)}\n"
        f"api_doc_text={api_doc_text[:2000]}"
    )
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    try:
        from octopusos.core.chat.adapters import get_adapter

        adapter = get_adapter("ollama", "qwen2.5:14b")
        response, _ = adapter.generate(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=220,
            stream=False,
        )
        text = str(response or "").strip()
        match = re.search(r"\{[\s\S]*\}", text)
        payload = json.loads(match.group(0) if match else text)
        proposal = MappingProposal.model_validate(payload)
        if not proposal.path_candidates:
            proposal.path_candidates = semantic_index
        return proposal, prompt_hash
    except Exception:
        return None, prompt_hash


def infer_mapping_proposal(
    *,
    capability_id: str,
    item_id: str,
    sample_json: Dict[str, Any],
    request_json: Dict[str, Any] | None = None,
    api_doc_text: str = "",
) -> Tuple[MappingProposal, str, str]:
    llm_proposal, prompt_hash = _llm_infer(
        capability_id=capability_id,
        item_id=item_id,
        sample_json=sample_json,
        request_json=request_json,
        api_doc_text=api_doc_text,
    )
    if llm_proposal is not None:
        return llm_proposal, "qwen2.5:14b", prompt_hash
    return _fallback_proposal(item_id=item_id, sample_json=sample_json, api_doc_text=api_doc_text), "fallback", prompt_hash
