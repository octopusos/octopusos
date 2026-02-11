from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from octopusos.core.audit import EXTENSION_STEP_EXECUTED, EXT_PERMISSION_CHECK, log_audit_event
from octopusos.core.dbops import DBOperationsOrchestrator, DBProviderCatalog, Decision, OperationRequest
from octopusos.core.dbops.idempotency import DBOpsIdempotencyStore


class DBOpsBridge:
    """Bridge layer from SkillOS invoke -> DBOps orchestrator + governance-shaped audit payload."""

    def __init__(self, catalog_path: str | Path, idempotency_db_path: str | Path | None = None):
        self.catalog = DBProviderCatalog(Path(catalog_path))
        self.orchestrator = DBOperationsOrchestrator(self.catalog)
        if idempotency_db_path is None:
            idempotency_db_path = Path.home() / ".octopusos" / "store" / "dbops" / "idempotency.sqlite"
        self.idempotency = DBOpsIdempotencyStore(idempotency_db_path)

    def handle(
        self,
        *,
        skill_id: str,
        command: str,
        args: Dict[str, Any],
        actor: str,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        action_id = str(args.get("action_id") or command)
        nl_text = str(args.get("nl_text") or args.get("text") or action_id)
        dry_run = bool(args.get("dry_run", True))
        reason = str(args.get("reason") or "db_ops_request")
        confirm_requested = bool(args.get("confirm") or args.get("confirmed"))
        confirm_token_input = args.get("confirm_token")

        # Idempotency fast-path: if this confirmation token already executed, replay result.
        if confirm_requested and confirm_token_input:
            existing = self.idempotency.get(str(confirm_token_input))
            if existing and existing.status == "EXECUTED" and existing.result:
                replay = dict(existing.result)
                replay["status"] = "already_executed"
                replay["idempotent_replay"] = True
                return replay

        op_req = OperationRequest(
            action_id=action_id,
            reason=reason,
            parameters=dict(args.get("parameters") or {}),
            requested_by=actor,
            dry_run=dry_run,
        )

        # plan_from_nl already applies instance selection and rejected-instance filtering
        try:
            plan = self.orchestrator.plan_from_nl(nl_text, op_req)
        except Exception as exc:
            payload = self._block_payload(
                action_id=action_id,
                actor=actor,
                reason=f"INSTANCE_SELECTION_FAILED: {exc}",
                request_id=request_id,
            )
            self._audit_event(payload, task_id=args.get("task_id"), level="warn")
            return payload

        pre_decision = {
            "at": self._now(),
            "risk": plan.risk.risk_level.value,
            "decision": plan.risk.decision.value,
            "reason": plan.risk.reason,
            "selected_instance_id": f"{plan.instance.provider_id}/{plan.instance.instance_id}",
            "why_this_instance": plan.why_this_instance,
        }

        if plan.risk.decision == Decision.BLOCK:
            payload = self._block_payload(
                action_id=action_id,
                actor=actor,
                reason=plan.risk.reason,
                request_id=request_id,
                selected_instance_id=pre_decision["selected_instance_id"],
                why_this_instance=plan.why_this_instance,
                risk=plan.risk.risk_level.value,
            )
            self._audit_event(payload, task_id=args.get("task_id"), level="warn")
            return payload

        if plan.risk.decision == Decision.CONFIRM:
            confirm_token = str(
                confirm_token_input
                or self._generate_confirm_token(
                    request_id=request_id,
                    action_id=action_id,
                    selected_instance_id=pre_decision["selected_instance_id"],
                    payload_signature=self._build_payload_signature(args=args, action_id=action_id),
                )
            )

            if not confirm_requested:
                payload = {
                    "status": "pending_confirmation",
                    "decision": "CONFIRM",
                    "request_id": request_id,
                    "confirm_payload": {
                        "confirm_token": confirm_token,
                        "risk": plan.risk.risk_level.value,
                        "why_this_instance": plan.why_this_instance,
                        "selected_instance_id": pre_decision["selected_instance_id"],
                        "estimated_impact": {
                            "estimated_rows": plan.risk.estimated_rows,
                            "target": plan.instance.target,
                        },
                        "rollback_possible": plan.risk.rollback_possible,
                        "telephone_book_entry": "TB-002",
                        "query_shape": plan.query_shape,
                    },
                    "audit": {
                        "policy": {
                            "gates": [
                                {
                                    "name": "dbops.precheck",
                                    "status": "PASSED",
                                    "details": "confirmation required",
                                }
                            ]
                        },
                        "decisions": [pre_decision],
                        "evidence": [],
                    },
                }
                self._audit_event(payload, task_id=args.get("task_id"), level="info")
                return payload

            # Confirm execution path: idempotent begin check before executing.
            state = self.idempotency.begin_once(confirm_token)
            if state.status == "EXECUTED" and state.result:
                replay = dict(state.result)
                replay["status"] = "already_executed"
                replay["idempotent_replay"] = True
                self._audit_event(replay, task_id=args.get("task_id"), level="info")
                return replay

            execution_payload = self._build_execution_payload(
                args=args,
                request_id=request_id,
                pre_decision=pre_decision,
                plan=plan,
                approved_by=args.get("approved_by") or actor,
                confirm_token=confirm_token,
            )
            self.idempotency.mark_executed(confirm_token, execution_payload)
            self._audit_event(execution_payload, task_id=args.get("task_id"), level="info")
            return execution_payload

        execution_payload = self._build_execution_payload(
            args=args,
            request_id=request_id,
            pre_decision=pre_decision,
            plan=plan,
            approved_by=args.get("approved_by"),
            confirm_token=None,
        )
        self._audit_event(execution_payload, task_id=args.get("task_id"), level="info")
        return execution_payload

    def _build_execution_payload(
        self,
        *,
        args: Dict[str, Any],
        request_id: Optional[str],
        pre_decision: Dict[str, Any],
        plan: Any,
        approved_by: Optional[str],
        confirm_token: Optional[str],
    ) -> Dict[str, Any]:
        audit_record = self.orchestrator.build_audit(
            plan,
            executed_via=str(args.get("executed_via") or "mcp:db-ops"),
            approved_by=approved_by,
        )

        evidence = []
        for artifact in args.get("artifacts", []):
            evidence.append({"kind": "artifact", "ref": {"path": str(artifact)}, "note": "dbops output"})

        return {
            "status": "success",
            "decision": "ALLOW",
            "request_id": request_id,
            "confirm_token": confirm_token,
            "result": {
                "selected_instance_id": pre_decision["selected_instance_id"],
                "query_shape": plan.query_shape,
                "why_this_instance": plan.why_this_instance,
                "execution": audit_record,
            },
            "audit": {
                "policy": {
                    "gates": [
                        {
                            "name": "dbops.precheck",
                            "status": "PASSED",
                            "details": "execution allowed",
                        }
                    ]
                },
                "decisions": [
                    pre_decision,
                    {
                        "at": self._now(),
                        "risk": plan.risk.risk_level.value,
                        "decision": "EXECUTED",
                        "reason": "dbops action executed through orchestrator",
                        "selected_instance_id": pre_decision["selected_instance_id"],
                        "why_this_instance": plan.why_this_instance,
                    },
                ],
                "evidence": evidence,
            },
        }

    def _block_payload(
        self,
        *,
        action_id: str,
        actor: str,
        reason: str,
        request_id: Optional[str],
        selected_instance_id: Optional[str] = None,
        why_this_instance: Optional[str] = None,
        risk: str = "HIGH",
    ) -> Dict[str, Any]:
        return {
            "status": "blocked",
            "decision": "BLOCK",
            "request_id": request_id,
            "error": {
                "reason_code": "DBOPS_BLOCKED",
                "message": (
                    "数据库实例被阻断或操作不被允许。请使用最小权限账号，"
                    "禁止 DBA/超级权限账号接入。"
                ),
                "details": reason,
            },
            "audit": {
                "policy": {
                    "gates": [
                        {
                            "name": "dbops.precheck",
                            "status": "FAILED",
                            "details": reason,
                        }
                    ]
                },
                "decisions": [
                    {
                        "at": self._now(),
                        "risk": risk,
                        "decision": "BLOCK",
                        "reason": reason,
                        "selected_instance_id": selected_instance_id,
                        "why_this_instance": why_this_instance,
                        "requested_by": actor,
                        "action_id": action_id,
                    }
                ],
                "evidence": [],
            },
        }

    def _audit_event(self, payload: Dict[str, Any], task_id: Optional[str], level: str) -> None:
        event_type = EXT_PERMISSION_CHECK if payload.get("decision") == "CONFIRM" else EXTENSION_STEP_EXECUTED
        try:
            log_audit_event(
                event_type=event_type,
                task_id=task_id,
                level=level,
                metadata={
                    "dbops": True,
                    "status": payload.get("status"),
                    "decision": payload.get("decision"),
                    "audit": payload.get("audit"),
                },
            )
        except Exception:
            # Do not break the skill path on audit persistence issues.
            return

    @staticmethod
    def _generate_confirm_token(
        *,
        request_id: Optional[str],
        action_id: str,
        selected_instance_id: str,
        payload_signature: str,
    ) -> str:
        seed = f"{request_id or 'no_request'}|{action_id}|{selected_instance_id}|{payload_signature}"
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _build_payload_signature(*, args: Dict[str, Any], action_id: str) -> str:
        """
        Build a deterministic summary hash input for confirm token generation.
        This binds token to meaningful operation shape and avoids cross-payload reuse.
        """
        parameters = args.get("parameters") or {}
        summary = {
            "action_id": action_id,
            "parameters": parameters,
            "migration_path": args.get("migration_path"),
            "tables": args.get("tables"),
            "predicate": args.get("predicate"),
            "target": args.get("target"),
        }
        encoded = json.dumps(summary, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]
