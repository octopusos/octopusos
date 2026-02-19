"""NetworkOS capability engine (M2).

Responsible for:
- validating requests against capability registry (scope allowlist)
- applying governance gate (silent_allow / explain_confirm / block)
- executing provider actions only after approval
- writing isolated audit trail to network_audit_log

Hard constraint: never touch CommunicationOS message_audit.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, Optional

from octopusos.networkos.capabilities.db import NetworkCapabilityStore
from octopusos.networkos.capabilities.registry import get_capability_spec
from octopusos.networkos.capabilities.types import GateDecision, RequestStatus
from octopusos.networkos.providers.cloudflare.provider import CloudflareProvider

logger = logging.getLogger(__name__)


def _hash_json_like(value: Any) -> str:
    raw = repr(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class NetworkCapabilityEngine:
    def __init__(self, store: Optional[NetworkCapabilityStore] = None):
        self.store = store or NetworkCapabilityStore()
        self.cloudflare = CloudflareProvider()

    def request_capability(self, *, capability: str, params: Dict[str, Any], requested_by: str) -> Dict[str, Any]:
        spec = get_capability_spec(capability)
        if not spec:
            return {"ok": False, "error": f"unknown_capability:{capability}"}

        scope = str((params or {}).get("scope") or "").strip()
        if scope:
            if not any(scope.startswith(prefix) for prefix in spec.allowed_scopes):
                return {"ok": False, "error": "scope_not_allowed", "details": {"scope": scope, "allowed": spec.allowed_scopes}}

        decision = spec.default_gate.value
        decision_reason = f"default_gate:{spec.default_gate.value}"
        status = RequestStatus.PENDING.value
        if spec.default_gate == GateDecision.SILENT_ALLOW:
            status = RequestStatus.APPROVED.value

        row = self.store.create_request(
            capability=spec.capability,
            params=params or {},
            requested_by=requested_by,
            decision=decision,
            decision_reason=decision_reason,
            status=status,
        )
        logger.info(
            "[networkos.engine] request created id=%s capability=%s decision=%s status=%s actor=%s",
            row.id,
            row.capability,
            row.decision,
            row.status,
            requested_by,
        )

        # Auto-execute if silent_allow
        if status == RequestStatus.APPROVED.value:
            self._execute_request(row.id)

        return {"ok": True, "request": row.to_dict()}

    def approve(self, *, request_id: str, actor: str) -> Dict[str, Any]:
        row = self.store.get_request(request_id)
        if not row:
            return {"ok": False, "error": "not_found"}
        # Idempotent approve: if already approved/active, return success without error.
        if row.status in {RequestStatus.APPROVED.value, RequestStatus.ACTIVE.value}:
            return {"ok": True, "request": row.to_dict(), "idempotent": True}
        if row.status not in {RequestStatus.PENDING.value, RequestStatus.FAILED.value}:
            return {"ok": False, "error": "not_approvable", "details": {"status": row.status}}

        self.store.update_request_status(request_id=row.id, status=RequestStatus.APPROVED.value)
        self.store.append_audit(
            request_id=row.id,
            event_type="APPROVED",
            metadata={"actor": actor},
        )
        logger.info("[networkos.engine] request approved id=%s capability=%s actor=%s", row.id, row.capability, actor)
        self._execute_request(row.id)
        return {"ok": True, "request": (self.store.get_request(row.id) or row).to_dict()}

    def revoke(self, *, request_id: str, actor: str) -> Dict[str, Any]:
        row = self.store.get_request(request_id)
        if not row:
            return {"ok": False, "error": "not_found"}
        # Revoke is allowed for active/approved/pending
        self.store.update_request_status(request_id=row.id, status=RequestStatus.REVOKED.value)
        self.store.append_audit(request_id=row.id, event_type="REVOKED", metadata={"actor": actor})
        # Best-effort provider revoke
        try:
            if row.capability in {"network.tunnel.enable", "network.access.attach"}:
                self.cloudflare.revoke(row.params)
            if row.capability in {"network.cloudflare.access.provision"}:
                self.cloudflare.revoke_access(row.params)
        except Exception:
            pass
        return {"ok": True, "request": (self.store.get_request(row.id) or row).to_dict()}

    def get_status(self) -> Dict[str, Any]:
        rows = self.store.list_requests(limit=200)
        return {"ok": True, "requests": [r.to_dict() for r in rows], "total": len(rows)}

    def _execute_request(self, request_id: str) -> None:
        row = self.store.get_request(request_id)
        if not row:
            return
        if row.status != RequestStatus.APPROVED.value:
            return
        logger.info("[networkos.engine] execute start id=%s capability=%s", row.id, row.capability)

        try:
            daemon_event: Dict[str, str] = {
                "network.cloudflare.daemon.install": "DAEMON_INSTALL",
                "network.cloudflare.daemon.uninstall": "DAEMON_UNINSTALL",
                "network.cloudflare.daemon.start": "DAEMON_START",
                "network.cloudflare.daemon.stop": "DAEMON_STOP",
                "network.cloudflare.daemon.restart": "DAEMON_RESTART",
                "network.cloudflare.daemon.enable_autostart": "DAEMON_AUTOSTART_ENABLE",
                "network.cloudflare.daemon.disable_autostart": "DAEMON_AUTOSTART_DISABLE",
            }
            if row.capability == "network.tunnel.enable":
                res = self.cloudflare.apply(row.params)
            elif row.capability == "network.tunnel.disable":
                res = self.cloudflare.revoke(row.params)
            elif row.capability == "network.access.attach":
                # In this minimal implementation, access attach is a no-op at provider,
                # but still audited as executed.
                res = self.cloudflare.apply(row.params)
            elif row.capability == "network.access.revoke":
                res = self.cloudflare.revoke(row.params)
            elif row.capability == "network.cloudflare.access.provision":
                res = self.cloudflare.provision_access(row.params)
            elif row.capability == "network.cloudflare.access.revoke":
                res = self.cloudflare.revoke_access(row.params)
            elif row.capability == "network.cloudflare.daemon.install":
                res = self.cloudflare.daemon_install(row.params)
            elif row.capability == "network.cloudflare.daemon.uninstall":
                res = self.cloudflare.daemon_uninstall(row.params)
            elif row.capability == "network.cloudflare.daemon.start":
                res = self.cloudflare.daemon_start(row.params)
            elif row.capability == "network.cloudflare.daemon.stop":
                res = self.cloudflare.daemon_stop(row.params)
            elif row.capability == "network.cloudflare.daemon.restart":
                res = self.cloudflare.daemon_restart(row.params)
            elif row.capability == "network.cloudflare.daemon.enable_autostart":
                res = self.cloudflare.daemon_enable_autostart(row.params)
            elif row.capability == "network.cloudflare.daemon.disable_autostart":
                res = self.cloudflare.daemon_disable_autostart(row.params)
            else:
                # network.status.get or unknown -> no-op
                return

            event_type = "EXECUTED" if res.ok else "FAILED"
            if row.capability in daemon_event:
                event_type = daemon_event[row.capability] + ("" if res.ok else "_FAILED")

            if res.ok:
                self.store.update_request_status(request_id=row.id, status=RequestStatus.ACTIVE.value)
                self.store.append_audit(
                    request_id=row.id,
                    event_type=event_type,
                    metadata={
                        "result": res.to_dict(),
                        "params_hash": _hash_json_like(row.params),
                    },
                )
                logger.info(
                    "[networkos.engine] execute success id=%s capability=%s daemon_state=%s detail=%s",
                    row.id,
                    row.capability,
                    getattr(res, "daemon_state", None),
                    getattr(res, "detail", None),
                )
            else:
                self.store.update_request_status(request_id=row.id, status=RequestStatus.FAILED.value)
                self.store.append_audit(
                    request_id=row.id,
                    event_type=event_type,
                    metadata={
                        "result": res.to_dict(),
                        "params_hash": _hash_json_like(row.params),
                    },
                )
                logger.warning(
                    "[networkos.engine] execute failed id=%s capability=%s daemon_state=%s detail=%s",
                    row.id,
                    row.capability,
                    getattr(res, "daemon_state", None),
                    getattr(res, "detail", None),
                )
        except Exception as e:
            self.store.update_request_status(request_id=row.id, status=RequestStatus.FAILED.value)
            self.store.append_audit(request_id=row.id, event_type="FAILED", metadata={"error": str(e)})
            logger.exception("[networkos.engine] execute exception id=%s capability=%s", row.id, row.capability)
