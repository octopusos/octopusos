from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from octopusos.core.chat.intents.db_intent import parse_db_intent
from octopusos.core.chat.ui_contracts import validate_ui_contract
from octopusos.skills.registry import SkillRegistry
from octopusos.skills.runtime.loader import SkillLoader
from octopusos.skills.runtime.invoke import SkillInvoker

# Frozen rule (governance critical):
# - Confirmation replay MUST use pending_action snapshot (action_id + parameters digest + token)
# - Never re-parse NL into a new db action on confirm path
# - Confirm executes only when pending_action exists in current session context


def _json_digest(payload: Dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


def _build_message_from_dbops_result(result: Dict[str, Any]) -> str:
    status = str(result.get("status") or "")
    if status == "pending_confirmation":
        cp = result.get("confirm_payload") or {}
        risk = cp.get("risk")
        why = cp.get("why_this_instance")
        impact = cp.get("estimated_impact") or {}
        rollback = cp.get("rollback_possible")
        tb = cp.get("telephone_book_entry")
        token = cp.get("confirm_token")
        return (
            f"DB operation requires confirmation.\n"
            f"risk={risk}\n"
            f"why_this_instance={why}\n"
            f"estimated_rows={impact.get('estimated_rows')}\n"
            f"rollback_possible={rollback}\n"
            f"rollback_entry={tb}\n"
            f"confirm_token={token}\n"
            f"Reply with 'confirm' to continue or 'cancel' to abort."
        )

    if status in {"success", "already_executed"}:
        result_block = result.get("result") or {}
        return (
            f"DB operation {status}. "
            f"instance={result_block.get('selected_instance_id')} "
            f"why={result_block.get('why_this_instance')}"
        )

    if status == "blocked":
        err = result.get("error") or {}
        return f"DB operation blocked: {err.get('message')} ({err.get('details')})"

    return "DB operation response received."


def _build_confirm_ui_contract(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if result.get("status") != "pending_confirmation":
        return None
    cp = result.get("confirm_payload") or {}
    ui = {
        "kind": "confirm_card",
        "version": "1",
        "title": "Database Operation Confirmation",
        "sections": [
            {"title": "Risk", "items": [str(cp.get("risk"))]},
            {"title": "Why This Instance", "items": [str(cp.get("why_this_instance"))]},
            {"title": "Estimated Impact", "items": [json.dumps(cp.get("estimated_impact") or {}, ensure_ascii=False)]},
            {"title": "Rollback", "items": [str(cp.get("rollback_possible"))]},
            {"title": "Rollback Runbook", "items": [str(cp.get("telephone_book_entry"))]},
        ],
        "primary": {
            "label": "I Understand And Continue",
            "action": "confirm",
            "style": "primary",
            "payload": {"confirm_token": cp.get("confirm_token")},
        },
        "secondary": {"label": "Cancel", "action": "cancel", "style": "secondary"},
    }
    validate_ui_contract(ui)
    return ui


def _build_missing_fields_candidates(ctx: Dict[str, Any]) -> Dict[str, Any]:
    catalog_ref = ctx.get("provider_catalog_ref") or os.getenv("OCTOPUSOS_DBOPS_CATALOG")
    if not catalog_ref:
        return {"instances": [], "targets": []}

    path = Path(catalog_ref)
    if not path.exists():
        return {"instances": [], "targets": []}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"instances": [], "targets": []}

    instances = []
    targets = []
    for provider in payload.get("providers", []):
        provider_id = provider.get("provider_id")
        for inst in provider.get("instances", [])[:5]:
            instance_id = inst.get("instance_id")
            target = inst.get("target")
            env = inst.get("environment")
            engine = inst.get("engine")
            instances.append({
                "instance_id": f"{provider_id}/{instance_id}",
                "label": f"{target or 'unknown'} ({env or 'unknown'}, {engine or 'unknown'})",
                "environment": env,
                "engine": engine,
            })
            if target:
                targets.append(target)
    return {"instances": instances[:5], "targets": sorted(set(targets))[:5]}


_SKILL_INVOKER: Optional[SkillInvoker] = None


def _get_skill_invoker() -> SkillInvoker:
    global _SKILL_INVOKER
    if _SKILL_INVOKER is None:
        registry = SkillRegistry()
        loader = SkillLoader(registry)
        loader.load_enabled_skills()
        _SKILL_INVOKER = SkillInvoker(loader, execution_phase="execution")
    return _SKILL_INVOKER


def try_handle_dbops_via_skillos(user_text: str, session_context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    ctx = session_context or {}
    intent = parse_db_intent(user_text, ctx)
    if not intent:
        return None

    if intent.get("intent") == "ask_missing_fields":
        candidates = _build_missing_fields_candidates(ctx)
        normalized_missing = []
        for field in intent.get("missing") or []:
            if field in {"environment", "target", "instance"}:
                normalized_missing.append(field)
            elif field == "migration_path":
                normalized_missing.append("target")
        if not normalized_missing:
            normalized_missing = ["target"]
        ui = {
            "kind": "ask_missing_fields",
            "version": "1",
            "title": "Missing fields for DB operation",
            "missing": normalized_missing,
            "candidates": {"instances": candidates.get("instances", [])},
            "primary": {"label": "Provide Fields", "action": "provide_fields", "style": "primary"},
            "secondary": {"label": "Cancel", "action": "cancel", "style": "secondary"},
        }
        validate_ui_contract(ui)
        return {
            "handled": True,
            "blocked": True,
            "message": str(intent.get("message") or "缺少必要参数。"),
            "missing": normalized_missing,
            "ui": ui,
        }

    if intent.get("intent") == "confirm_control" and intent.get("cancel"):
        return {
            "handled": True,
            "blocked": False,
            "message": "已取消数据库操作确认。",
            "pending_action_clear": True,
        }

    if intent.get("intent") == "confirm_control" and intent.get("confirm"):
        # Confirm path must come only from session pending snapshot.
        action_id = str(intent.get("action_id") or "")
        confirm_token = intent.get("confirm_token")
        parameters = intent.get("parameters") or {}

        invoker = _get_skill_invoker()
        invoke_args = {
            "action_id": action_id,
            "nl_text": str(intent.get("nl_text") or user_text),
            "reason": str(intent.get("reason") or "confirmed_by_user"),
            "parameters": parameters,
            "confirm": True,
            "confirm_token": confirm_token,
            "request_id": ctx.get("request_id") or ctx.get("session_id"),
            "provider_catalog_ref": ctx.get("provider_catalog_ref") or os.getenv("OCTOPUSOS_DBOPS_CATALOG"),
            "idempotency_store_ref": ctx.get("idempotency_store_ref") or os.getenv("OCTOPUSOS_DBOPS_IDEMPOTENCY_DB"),
            "task_id": ctx.get("task_id"),
            "requested_by": ctx.get("actor") or "chat",
            "approved_by": ctx.get("actor") or "user",
            "dry_run": False,
        }
        result = invoker.invoke("db_ops", action_id, invoke_args)
        return {
            "handled": True,
            "blocked": bool(result.get("status") == "blocked"),
            "message": _build_message_from_dbops_result(result),
            "dbops_result": result,
            "ui": _build_confirm_ui_contract(result),
            "pending_action_clear": True,
        }

    action_id = str(intent.get("action_id") or "")
    args = dict(intent.get("args") or {})
    hints = intent.get("hints") or {}

    invoker = _get_skill_invoker()
    invoke_args = {
        "action_id": action_id,
        "nl_text": user_text,
        "reason": args.get("reason") or "chat_db_intent",
        "parameters": args.get("parameters") or {},
        "dry_run": bool(args.get("dry_run", True)),
        "request_id": ctx.get("request_id") or ctx.get("session_id"),
        "provider_catalog_ref": ctx.get("provider_catalog_ref") or os.getenv("OCTOPUSOS_DBOPS_CATALOG"),
        "idempotency_store_ref": ctx.get("idempotency_store_ref") or os.getenv("OCTOPUSOS_DBOPS_IDEMPOTENCY_DB"),
        "task_id": ctx.get("task_id"),
        "requested_by": ctx.get("actor") or "chat",
    }
    if hints.get("environment"):
        invoke_args["parameters"]["environment"] = hints.get("environment")
    if hints.get("engine") and not invoke_args["parameters"].get("engine"):
        invoke_args["parameters"]["engine"] = hints.get("engine")
    if hints.get("target") and not invoke_args["parameters"].get("target"):
        invoke_args["parameters"]["target"] = hints.get("target")

    result = invoker.invoke("db_ops", action_id, invoke_args)

    payload: Dict[str, Any] = {
        "handled": True,
        "blocked": bool(result.get("status") == "blocked"),
        "message": _build_message_from_dbops_result(result),
        "dbops_result": result,
        "ui": _build_confirm_ui_contract(result),
    }

    if result.get("status") == "pending_confirmation":
        cp = result.get("confirm_payload") or {}
        parameter_digest = _json_digest(invoke_args["parameters"])
        payload["pending_action_set"] = {
            "request_id": invoke_args["request_id"],
            "action_id": action_id,
            "selected_instance_id": cp.get("selected_instance_id"),
            "nl_text": user_text,
            "reason": invoke_args["reason"],
            "parameters": invoke_args["parameters"],
            "args_digest": parameter_digest,
            "confirm_token": cp.get("confirm_token"),
        }

    return payload
