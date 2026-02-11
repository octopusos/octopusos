"""Compatibility endpoints for external facts policy management."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict

from fastapi import APIRouter, Body, Query

from octopusos.core.capabilities.external_facts.policy_store import ExternalFactsPolicyStore
from octopusos.core.capabilities.external_facts.types import SourcePolicy

router = APIRouter(prefix="/api/compat/external-facts", tags=["compat"])

_policy_store = ExternalFactsPolicyStore()


def _normalize_csv(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


@router.get("/policy")
async def get_policy(
    mode: str = Query(default="chat"),
    kind: str = Query(default="weather"),
):
    policy = _policy_store.get(mode=mode, kind=kind)
    return {
        "ok": True,
        "data": {
            "mode": mode.lower(),
            "kind": kind.lower(),
            "policy": asdict(policy),
        },
        "source": "compat",
    }


@router.put("/policy")
async def put_policy(
    payload: Dict[str, Any] = Body(...),
):
    mode = str(payload.get("mode") or "chat").lower()
    kind = str(payload.get("kind") or "weather").lower()
    current = _policy_store.get(mode=mode, kind=kind)

    policy = SourcePolicy(
        prefer_structured=bool(payload.get("prefer_structured", current.prefer_structured)),
        allow_search_fallback=bool(payload.get("allow_search_fallback", current.allow_search_fallback)),
        max_sources=max(1, int(payload.get("max_sources", current.max_sources))),
        require_freshness_seconds=payload.get("require_freshness_seconds", current.require_freshness_seconds),
        source_whitelist=_normalize_csv(payload.get("source_whitelist", current.source_whitelist)),
        source_blacklist=_normalize_csv(payload.get("source_blacklist", current.source_blacklist)),
        min_confidence=str(payload.get("min_confidence", current.min_confidence)).lower(),  # type: ignore[arg-type]
    )
    if policy.require_freshness_seconds not in (None, ""):
        policy.require_freshness_seconds = int(policy.require_freshness_seconds)
    if policy.min_confidence not in {"high", "medium", "low"}:
        policy.min_confidence = current.min_confidence

    _policy_store.upsert(mode=mode, kind=kind, policy=policy)
    return {
        "ok": True,
        "data": {
            "mode": mode,
            "kind": kind,
            "policy": asdict(policy),
        },
        "source": "compat",
    }


@router.get("/policy/list")
async def list_policies():
    return {
        "ok": True,
        "data": _policy_store.list(),
        "source": "compat",
    }
