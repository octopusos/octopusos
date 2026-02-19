"""Cloudflare provider wrapper for NetworkOS capabilities (M2).

Hard boundary:
- NetworkOS owns Cloudflare execution
- Callers (including MCP) submit only declarative requests
- Provider must not log secrets; only metadata may be audited

Implementation note (minimal):
- We support starting/stopping a Cloudflare tunnel when a tunnel token is available.
- Access (Cloudflare Access) is represented as a required client header pair
  (CF-Access-Client-Id/CF-Access-Client-Secret) to keep verification script meaningful.

This repo does not yet fully automate Cloudflare Access application provisioning.
When Access secrets are configured, we treat Access as "required" for verification.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

from octopusos.networkos.service import NetworkOSService
from octopusos.networkos.config_store import NetworkConfigStore
from octopusos.networkos.providers.cloudflare.daemon_manager import CloudflaredDaemonManager
from octopusos.webui.secrets import SecretStore

logger = logging.getLogger(__name__)


@dataclass
class CloudflareExecutionStatus:
    ok: bool
    detail: str
    public_hostname: str | None = None
    access_required: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": bool(self.ok),
            "detail": self.detail,
            "public_hostname": self.public_hostname,
            "access_required": bool(self.access_required),
        }


@dataclass
class DaemonExecutionResult:
    ok: bool
    detail: str
    daemon_state: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {"ok": bool(self.ok), "detail": self.detail, "daemon_state": self.daemon_state}


class CloudflareProvider:
    def __init__(self, service: Optional[NetworkOSService] = None, secrets: Optional[SecretStore] = None):
        self.service = service or NetworkOSService()
        self.secrets = secrets or SecretStore()
        self.config = NetworkConfigStore()
        self.daemon = CloudflaredDaemonManager()

    def _get_secret(self, ref: str) -> str:
        v = self.secrets.get(ref) or ""
        return str(v).strip()

    def _get_cfg(self, key: str, default: Any = None) -> Any:
        return self.config.resolve(key, default=default).value

    def _cf_headers(self, api_token: str) -> Dict[str, str]:
        return {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}

    def _cf_base(self) -> str:
        return "https://api.cloudflare.com/client/v4"

    def _cf_request(self, *, api_token: str, method: str, path: str, json_body: Any | None = None) -> Dict[str, Any]:
        url = f"{self._cf_base()}{path}"
        with httpx.Client(timeout=20) as client:
            resp = client.request(method.upper(), url, headers=self._cf_headers(api_token), json=json_body)
        try:
            data = resp.json()
        except Exception:
            data = {"success": False, "errors": [{"message": f"http_{resp.status_code}"}]}
        if not isinstance(data, dict):
            data = {"success": False, "errors": [{"message": f"http_{resp.status_code}"}]}
        if not resp.is_success or not data.get("success", False):
            msg = ""
            try:
                errs = data.get("errors") or []
                if errs and isinstance(errs, list):
                    msg = str(errs[0].get("message") or errs[0])
            except Exception:
                msg = ""
            raise RuntimeError(f"cloudflare_api_error:{resp.status_code}:{msg or 'request_failed'}")
        return data

    def _find_access_app_id(self, *, api_token: str, account_id: str, hostname: str) -> str | None:
        data = self._cf_request(api_token=api_token, method="GET", path=f"/accounts/{account_id}/access/apps")
        items = data.get("result") or []
        if not isinstance(items, list):
            return None
        for it in items:
            domain = str(it.get("domain") or "").strip()
            if domain == hostname:
                app_id = str(it.get("id") or "").strip()
                return app_id or None
        return None

    def _get_access_app_policies(self, *, api_token: str, account_id: str, app_id: str) -> list[dict[str, Any]]:
        data = self._cf_request(api_token=api_token, method="GET", path=f"/accounts/{account_id}/access/apps/{app_id}/policies")
        items = data.get("result") or []
        return items if isinstance(items, list) else []

    @staticmethod
    def _extract_scoped_token_id(*, policies: list[dict[str, Any]], target_policy_name: str) -> tuple[str | None, str, str | None]:
        """Extract service_token.token_id from a named policy.

        Conservative parsing:
        - If policy not found -> None + reason
        - If include structure missing/invalid -> None + reason
        - If multiple service_token token_id values -> None + reason
        """
        name = str(target_policy_name or "").strip()
        if not name:
            return None, "missing_target_policy_name", None
        matches = [p for p in (policies or []) if str(p.get("name") or "").strip() == name]
        if not matches:
            return None, "no_policy_found", None
        if len(matches) > 1:
            return None, "multiple_policies_found", None
        pol = matches[0]
        policy_id = str(pol.get("id") or "").strip() or None
        include = pol.get("include")
        if not isinstance(include, list):
            return None, "include_not_list", policy_id

        token_ids: list[str] = []
        for rule in include:
            if not isinstance(rule, dict):
                continue
            st = rule.get("service_token")
            if not isinstance(st, dict):
                continue
            tid = str(st.get("token_id") or "").strip()
            if tid:
                token_ids.append(tid)

        token_ids = list(dict.fromkeys(token_ids))
        if not token_ids:
            return None, "no_service_token_rule", policy_id
        if len(token_ids) > 1:
            return None, "multiple_service_token_ids", policy_id
        return token_ids[0], "ok", policy_id

    def get_policy_scoping_status(self, params: Dict[str, Any], *, debug: bool = False) -> Dict[str, Any]:
        """Return policy scoping metadata without returning any secrets."""
        hostname = str(params.get("hostname") or self._get_cfg("network.cloudflare.hostname") or "").strip()
        account_id = str(params.get("account_id") or self._get_cfg("network.cloudflare.account_id") or "").strip()
        app_name = str(params.get("app_name") or self._get_cfg("network.cloudflare.app_name") or "octopusos-access").strip()
        expected_token_id = str(params.get("service_token_id") or self._get_cfg("network.cloudflare.service_token_id") or "").strip()

        api_token_ref = str(params.get("api_token_ref") or "secret://networkos/cloudflare/api_token").strip()
        api_token = self._get_secret(api_token_ref)
        if not api_token:
            base = {
                "expected_service_token_id": expected_token_id or None,
                "policy_scoped_token_id": None,
                "policy_scoping_ok": False,
                "policy_scoping_reason": f"missing_api_token:{api_token_ref}",
            }
            return base
        if not hostname or not account_id:
            base = {
                "expected_service_token_id": expected_token_id or None,
                "policy_scoped_token_id": None,
                "policy_scoping_ok": False,
                "policy_scoping_reason": "missing_cloudflare_config:hostname/account_id",
            }
            return base

        app_id = self._find_access_app_id(api_token=api_token, account_id=account_id, hostname=hostname)
        if not app_id:
            base = {
                "expected_service_token_id": expected_token_id or None,
                "policy_scoped_token_id": None,
                "policy_scoping_ok": False,
                "policy_scoping_reason": "access_app_not_found",
            }
            if debug:
                base.update(
                    {
                        "access_app_id": None,
                        "service_auth_policy_id": None,
                        "policies_seen_count": 0,
                        "policy_name_matched": False,
                    }
                )
            return base

        policies = self._get_access_app_policies(api_token=api_token, account_id=account_id, app_id=app_id)
        scoped, reason, policy_id = self._extract_scoped_token_id(policies=policies, target_policy_name=f"{app_name}-service-auth")
        ok = bool(scoped and expected_token_id and scoped == expected_token_id)
        if not expected_token_id:
            ok = False
            if reason == "ok":
                reason = "missing_expected_service_token_id"
        elif scoped is None and reason == "ok":
            reason = "scoped_token_id_missing"
        elif scoped and expected_token_id and scoped != expected_token_id:
            reason = "token_id_mismatch"
        base = {
            "expected_service_token_id": expected_token_id or None,
            "policy_scoped_token_id": scoped,
            "policy_scoping_ok": bool(ok),
            "policy_scoping_reason": reason,
        }
        if debug:
            base.update(
                {
                    "access_app_id": app_id,
                    "service_auth_policy_id": policy_id,
                    "policies_seen_count": len(policies),
                    "policy_name_matched": bool(policy_id),
                }
            )
        return base

    def daemon_status(self, params: Dict[str, Any], *, debug: bool = False) -> Dict[str, Any]:
        tunnel_name = str(params.get("tunnel_name") or self._get_cfg("network.cloudflare.tunnel_name") or "octopusos").strip()
        st = self.daemon.get_status(tunnel_name=tunnel_name, debug=bool(debug))
        return st.to_dict()

    def daemon_install(self, params: Dict[str, Any]) -> "DaemonExecutionResult":
        tunnel_name = str(params.get("tunnel_name") or self._get_cfg("network.cloudflare.tunnel_name") or "octopusos").strip()
        det = self.daemon.detect_cloudflared()
        if not det.installed:
            return DaemonExecutionResult(ok=False, detail="cloudflared_not_installed")
        maybe_invalid = self._validate_local_tunnel_name(tunnel_name)
        if maybe_invalid:
            return DaemonExecutionResult(
                ok=False,
                detail=maybe_invalid,
                daemon_state=self.daemon.get_status(tunnel_name=tunnel_name).state,
            )
        self.daemon.install_service(tunnel_name=tunnel_name)
        return DaemonExecutionResult(ok=True, detail="installed", daemon_state=self.daemon.get_status(tunnel_name=tunnel_name).state)

    def daemon_uninstall(self, params: Dict[str, Any]) -> "DaemonExecutionResult":
        tunnel_name = str(params.get("tunnel_name") or self._get_cfg("network.cloudflare.tunnel_name") or "octopusos").strip()
        self.daemon.uninstall_service()
        return DaemonExecutionResult(ok=True, detail="uninstalled", daemon_state=self.daemon.get_status(tunnel_name=tunnel_name).state)

    def daemon_start(self, params: Dict[str, Any]) -> "DaemonExecutionResult":
        tunnel_name = str(params.get("tunnel_name") or self._get_cfg("network.cloudflare.tunnel_name") or "octopusos").strip()
        maybe_invalid = self._validate_local_tunnel_name(tunnel_name)
        if maybe_invalid:
            return DaemonExecutionResult(
                ok=False,
                detail=maybe_invalid,
                daemon_state=self.daemon.get_status(tunnel_name=tunnel_name).state,
            )
        self.daemon.sync_service_runtime(tunnel_name=tunnel_name)
        self.daemon.start()
        st = self._wait_daemon_state(tunnel_name=tunnel_name, expect="running", timeout_s=8)
        if st and st.state == "running":
            return DaemonExecutionResult(ok=True, detail="started", daemon_state=st.state)
        detail = self._daemon_failure_detail(st, fallback="start_not_running")
        return DaemonExecutionResult(ok=False, detail=detail, daemon_state=(st.state if st else None))

    def daemon_stop(self, params: Dict[str, Any]) -> "DaemonExecutionResult":
        tunnel_name = str(params.get("tunnel_name") or self._get_cfg("network.cloudflare.tunnel_name") or "octopusos").strip()
        self.daemon.stop()
        return DaemonExecutionResult(ok=True, detail="stopped", daemon_state=self.daemon.get_status(tunnel_name=tunnel_name).state)

    def daemon_restart(self, params: Dict[str, Any]) -> "DaemonExecutionResult":
        tunnel_name = str(params.get("tunnel_name") or self._get_cfg("network.cloudflare.tunnel_name") or "octopusos").strip()
        maybe_invalid = self._validate_local_tunnel_name(tunnel_name)
        if maybe_invalid:
            return DaemonExecutionResult(
                ok=False,
                detail=maybe_invalid,
                daemon_state=self.daemon.get_status(tunnel_name=tunnel_name).state,
            )
        self.daemon.sync_service_runtime(tunnel_name=tunnel_name)
        self.daemon.restart()
        st = self._wait_daemon_state(tunnel_name=tunnel_name, expect="running", timeout_s=8)
        if st and st.state == "running":
            return DaemonExecutionResult(ok=True, detail="restarted", daemon_state=st.state)
        detail = self._daemon_failure_detail(st, fallback="restart_not_running")
        return DaemonExecutionResult(ok=False, detail=detail, daemon_state=(st.state if st else None))

    def daemon_enable_autostart(self, params: Dict[str, Any]) -> "DaemonExecutionResult":
        tunnel_name = str(params.get("tunnel_name") or self._get_cfg("network.cloudflare.tunnel_name") or "octopusos").strip()
        self.daemon.enable_autostart()
        return DaemonExecutionResult(ok=True, detail="autostart_enabled", daemon_state=self.daemon.get_status(tunnel_name=tunnel_name).state)

    def daemon_disable_autostart(self, params: Dict[str, Any]) -> "DaemonExecutionResult":
        tunnel_name = str(params.get("tunnel_name") or self._get_cfg("network.cloudflare.tunnel_name") or "octopusos").strip()
        self.daemon.disable_autostart()
        return DaemonExecutionResult(ok=True, detail="autostart_disabled", daemon_state=self.daemon.get_status(tunnel_name=tunnel_name).state)

    def cli_install(self, params: Dict[str, Any]) -> "DaemonExecutionResult":
        tunnel_name = str(params.get("tunnel_name") or self._get_cfg("network.cloudflare.tunnel_name") or "octopusos").strip()
        ok, detail = self.daemon.install_cli()
        return DaemonExecutionResult(ok=bool(ok), detail=str(detail), daemon_state=self.daemon.get_status(tunnel_name=tunnel_name).state)

    def daemon_list_tunnels(self, params: Dict[str, Any]) -> Dict[str, Any]:
        items = self.daemon.list_tunnels()
        return {
            "items": items,
            "total": len(items),
        }

    def daemon_create_tunnel(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = str(params.get("name") or "").strip()
        result = self.daemon.create_tunnel(name=name)
        return {
            "created": bool(result.get("created")),
            "detail": str(result.get("detail") or "created"),
            "tunnel": result.get("tunnel") or {},
        }

    def daemon_clear_logs(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.daemon.clear_logs()

    def _validate_local_tunnel_name(self, tunnel_name: str) -> str | None:
        name = str(tunnel_name or "").strip()
        if not name:
            return "missing_tunnel_name"
        items = self.daemon.list_tunnels()
        if not items:
            # Best effort: do not hard-fail when list command is unavailable.
            return None
        names = [str(it.get("name") or "").strip() for it in items if str(it.get("name") or "").strip()]
        if name in names:
            return None
        sample = ",".join(names[:8]) if names else "-"
        return f"tunnel_not_found:{name};available={sample}"

    def _wait_daemon_state(self, *, tunnel_name: str, expect: str, timeout_s: int = 8):
        deadline = time.time() + max(1, int(timeout_s))
        last = None
        while time.time() < deadline:
            last = self.daemon.get_status(tunnel_name=tunnel_name, debug=True)
            if str(last.state) == expect:
                return last
            time.sleep(0.8)
        return last

    def _daemon_failure_detail(self, status: Any, *, fallback: str) -> str:
        if not status:
            return fallback
        if getattr(status, "last_error", None):
            return str(status.last_error)
        tail = str(getattr(status, "logs_tail", "") or "").strip()
        if tail:
            line = tail.splitlines()[-1].strip()
            if line:
                return f"{fallback}:{line[:240]}"
        return fallback

    def _ensure_service_token(
        self,
        *,
        api_token: str,
        account_id: str,
        name: str,
        token_id_ref: str,
        token_secret_ref: str,
    ) -> tuple[str, str]:
        # Reuse if already stored.
        existing_id = self._get_secret(token_id_ref)
        existing_secret = self._get_secret(token_secret_ref)
        if existing_id and existing_secret:
            return existing_id, existing_secret

        # Find by name (list)
        data = self._cf_request(api_token=api_token, method="GET", path=f"/accounts/{account_id}/access/service_tokens")
        items = data.get("result") or []
        if isinstance(items, list):
            for it in items:
                if str(it.get("name") or "").strip() == name:
                    # NOTE: Cloudflare does not return secret again; if we found by name but
                    # secret isn't stored, we must create a new token to keep probes working.
                    break

        created = self._cf_request(
            api_token=api_token,
            method="POST",
            path=f"/accounts/{account_id}/access/service_tokens",
            json_body={"name": name},
        )
        res = created.get("result") or {}
        client_id = str(res.get("client_id") or "").strip()
        client_secret = str(res.get("client_secret") or "").strip()
        if not client_id or not client_secret:
            raise RuntimeError("cloudflare_service_token_missing_credentials")
        self.secrets.set(token_id_ref, client_id)
        self.secrets.set(token_secret_ref, client_secret)
        return client_id, client_secret

    def _ensure_access_app(self, *, api_token: str, account_id: str, name: str, hostname: str) -> str:
        # Find existing app by domain match.
        data = self._cf_request(api_token=api_token, method="GET", path=f"/accounts/{account_id}/access/apps")
        items = data.get("result") or []
        if isinstance(items, list):
            for it in items:
                domain = str(it.get("domain") or "").strip()
                if domain == hostname:
                    return str(it.get("id"))

        created = self._cf_request(
            api_token=api_token,
            method="POST",
            path=f"/accounts/{account_id}/access/apps",
            json_body={
                "name": name,
                "domain": hostname,
                "type": "self_hosted",
                "session_duration": "24h",
            },
        )
        res = created.get("result") or {}
        app_id = str(res.get("id") or "").strip()
        if not app_id:
            raise RuntimeError("cloudflare_access_app_missing_id")
        return app_id

    def _ensure_policy(
        self,
        *,
        api_token: str,
        account_id: str,
        app_id: str,
        name: str,
        decision: str,
        include: list[dict[str, Any]],
        precedence: int,
        enabled: bool = True,
    ) -> str:
        data = self._cf_request(api_token=api_token, method="GET", path=f"/accounts/{account_id}/access/apps/{app_id}/policies")
        items = data.get("result") or []
        if isinstance(items, list):
            for it in items:
                if str(it.get("name") or "").strip() == name:
                    pid = str(it.get("id") or "").strip()
                    if not pid:
                        continue
                    # Update to desired state (idempotent)
                    self._cf_request(
                        api_token=api_token,
                        method="PUT",
                        path=f"/accounts/{account_id}/access/apps/{app_id}/policies/{pid}",
                        json_body={
                            "name": name,
                            "decision": decision,
                            "include": include,
                            "precedence": int(precedence),
                            "enabled": bool(enabled),
                        },
                    )
                    return pid

        created = self._cf_request(
            api_token=api_token,
            method="POST",
            path=f"/accounts/{account_id}/access/apps/{app_id}/policies",
            json_body={
                "name": name,
                "decision": decision,
                "include": include,
                "precedence": int(precedence),
                "enabled": bool(enabled),
            },
        )
        res = created.get("result") or {}
        pid = str(res.get("id") or "").strip()
        if not pid:
            raise RuntimeError("cloudflare_access_policy_missing_id")
        return pid

    def provision_access(self, params: Dict[str, Any]) -> CloudflareExecutionStatus:
        """Provision Cloudflare Access (Application + Policy + Service Token).

        Does NOT manage tunnel/daemon/DNS. Assumes hostname already routes to this instance.
        """
        hostname = str(params.get("hostname") or self._get_cfg("network.cloudflare.hostname") or "").strip()
        account_id = str(params.get("account_id") or self._get_cfg("network.cloudflare.account_id") or "").strip()
        app_name = str(params.get("app_name") or self._get_cfg("network.cloudflare.app_name") or "octopusos-access").strip()
        enforce_access = bool(params.get("enforce_access") if "enforce_access" in (params or {}) else self._get_cfg("network.cloudflare.enforce_access", True))
        probe_path = str(params.get("probe_path") or self._get_cfg("network.cloudflare.health_path", "/api/health") or "/api/health").strip()

        api_token_ref = str(params.get("api_token_ref") or "secret://networkos/cloudflare/api_token").strip()
        api_token = self._get_secret(api_token_ref)
        if not api_token:
            return CloudflareExecutionStatus(False, f"missing_cloudflare_api_token:{api_token_ref}", public_hostname=hostname, access_required=True)
        if not hostname or not account_id:
            return CloudflareExecutionStatus(False, "missing_cloudflare_config:hostname/account_id", public_hostname=hostname, access_required=True)

        # Service token stored in SecretStore
        st_id_ref = str(params.get("service_token_id_ref") or "secret://networkos/cloudflare/access_service_token_id").strip()
        st_sec_ref = str(params.get("service_token_secret_ref") or "secret://networkos/cloudflare/access_service_token_secret").strip()
        st_name = str(params.get("service_token_name") or f"{app_name}-probe").strip()
        client_id, client_secret = self._ensure_service_token(
            api_token=api_token,
            account_id=account_id,
            name=st_name,
            token_id_ref=st_id_ref,
            token_secret_ref=st_sec_ref,
        )

        app_id = self._ensure_access_app(api_token=api_token, account_id=account_id, name=app_name, hostname=hostname)

        # Enforce access by default using "non_identity" (service auth) policy.
        # SECURITY: scope allow to the exact service token id created/managed by this system.
        # This avoids accidental lateral authorization in shared Cloudflare accounts.
        if enforce_access:
            self._ensure_policy(
                api_token=api_token,
                account_id=account_id,
                app_id=app_id,
                name=f"{app_name}-service-auth",
                decision="non_identity",
                include=[{"service_token": {"token_id": client_id}}],
                precedence=1,
                enabled=True,
            )
            # Ensure no bypass-all policy is enabled.
            self._ensure_policy(
                api_token=api_token,
                account_id=account_id,
                app_id=app_id,
                name=f"{app_name}-bypass-all",
                decision="bypass",
                include=[{"everyone": {}}],
                precedence=100,
                enabled=False,
            )
        else:
            # If enforcement disabled, set bypass-all.
            self._ensure_policy(
                api_token=api_token,
                account_id=account_id,
                app_id=app_id,
                name=f"{app_name}-bypass-all",
                decision="bypass",
                include=[{"everyone": {}}],
                precedence=1,
                enabled=True,
            )

        # Validate at edge (uses service token headers).
        if enforce_access:
            probe = self._probe_access(hostname=hostname, path=probe_path, client_id=client_id, client_secret=client_secret)
            if not probe.ok:
                return probe

        # Persist last-known-good non-sensitive config when provision succeeds.
        try:
            self.config.set_many(
                items={
                    "network.cloudflare.hostname": hostname,
                    "network.cloudflare.account_id": account_id,
                    "network.cloudflare.enforce_access": bool(enforce_access),
                    "network.cloudflare.health_path": probe_path,
                    "network.cloudflare.app_name": app_name,
                    # Non-secret id is safe to persist for status/diagnostics.
                    "network.cloudflare.service_token_id": client_id,
                },
                updated_by="provision_access",
            )
        except Exception:
            pass

        return CloudflareExecutionStatus(True, "access_provisioned", public_hostname=hostname, access_required=True)

    def revoke_access(self, params: Dict[str, Any]) -> CloudflareExecutionStatus:
        """Revoke Cloudflare Access enforcement (without touching tunnel/DNS)."""
        hostname = str(params.get("hostname") or self._get_cfg("network.cloudflare.hostname") or "").strip()
        account_id = str(params.get("account_id") or self._get_cfg("network.cloudflare.account_id") or "").strip()
        app_name = str(params.get("app_name") or self._get_cfg("network.cloudflare.app_name") or "octopusos-access").strip()
        api_token_ref = str(params.get("api_token_ref") or "secret://networkos/cloudflare/api_token").strip()
        api_token = self._get_secret(api_token_ref)
        if not api_token:
            return CloudflareExecutionStatus(False, f"missing_cloudflare_api_token:{api_token_ref}", public_hostname=hostname, access_required=True)
        if not hostname or not account_id:
            return CloudflareExecutionStatus(False, "missing_cloudflare_config:hostname/account_id", public_hostname=hostname, access_required=True)

        app_id = self._ensure_access_app(api_token=api_token, account_id=account_id, name=app_name, hostname=hostname)
        # Enable bypass-all to effectively disable enforcement.
        self._ensure_policy(
            api_token=api_token,
            account_id=account_id,
            app_id=app_id,
            name=f"{app_name}-bypass-all",
            decision="bypass",
            include=[{"everyone": {}}],
            precedence=1,
            enabled=True,
        )
        # Best-effort: disable service-auth policy if present.
        try:
            self._ensure_policy(
                api_token=api_token,
                account_id=account_id,
                app_id=app_id,
                name=f"{app_name}-service-auth",
                decision="non_identity",
                include=[{"service_token": {"token_id": str(self._get_cfg('network.cloudflare.service_token_id') or '').strip() or 'unknown'}}],
                precedence=100,
                enabled=False,
            )
        except Exception:
            pass

        try:
            self.config.set_db_value(key="network.cloudflare.enforce_access", value=False, updated_by="revoke_access")
        except Exception:
            pass

        return CloudflareExecutionStatus(True, "access_revoked_bypass", public_hostname=hostname, access_required=False)

    def access_status(self, params: Dict[str, Any]) -> CloudflareExecutionStatus:
        hostname = str(params.get("hostname") or self._get_cfg("network.cloudflare.hostname") or "").strip()
        enforce_access = bool(self._get_cfg("network.cloudflare.enforce_access", True))
        detail = "configured" if hostname else "missing_hostname"
        return CloudflareExecutionStatus(True, detail, public_hostname=hostname or None, access_required=enforce_access)

    def _probe_access(
        self,
        *,
        hostname: str,
        path: str,
        client_id: str,
        client_secret: str,
        timeout_sec: int = 10,
        attempts: int = 20,
    ) -> CloudflareExecutionStatus:
        """Probe Cloudflare Access at the edge.

        Expected behavior:
        - Without headers: blocked (401/403) OR redirected to login (3xx).
        - With service token headers: 200 and /api/health returns ok.
        """
        url = f"https://{hostname}{path}"
        headers = {"CF-Access-Client-Id": client_id, "CF-Access-Client-Secret": client_secret}

        last_err = ""
        for _ in range(max(1, int(attempts))):
            try:
                with httpx.Client(follow_redirects=False, timeout=timeout_sec) as client:
                    # 1) unauth probe
                    r0 = client.get(url)
                    blocked = r0.status_code in (401, 403) or (300 <= r0.status_code < 400)
                    if not blocked:
                        return CloudflareExecutionStatus(
                            False,
                            f"access_not_enforced:http_{r0.status_code}",
                            public_hostname=hostname,
                            access_required=True,
                        )

                    # 2) auth probe
                    r1 = client.get(url, headers=headers)
                    if r1.status_code != 200:
                        return CloudflareExecutionStatus(
                            False,
                            f"access_auth_failed:http_{r1.status_code}",
                            public_hostname=hostname,
                            access_required=True,
                        )
                    return CloudflareExecutionStatus(True, "access_enforced", public_hostname=hostname, access_required=True)
            except Exception as e:
                last_err = str(e)[:200]
                time.sleep(1)
                continue

        return CloudflareExecutionStatus(False, f"access_probe_failed:{last_err}", public_hostname=hostname, access_required=True)

    def apply(self, params: Dict[str, Any]) -> CloudflareExecutionStatus:
        """Apply a network access request.

        Expected params:
        - local_target: http://127.0.0.1:8080 (default)
        - hostname: public hostname (for display)
        - tunnel_name: stable name
        - tunnel_token_ref: secret://networkos/cloudflare/tunnel_token
        - access_client_id_ref / access_client_secret_ref (optional; for verification)
        """
        tunnel_name = str(params.get("tunnel_name") or "octopusos").strip()
        local_target = str(params.get("local_target") or "http://127.0.0.1:8080").strip()
        hostname = str(params.get("hostname") or self._get_cfg("network.cloudflare.hostname") or "").strip()

        token_ref = str(params.get("tunnel_token_ref") or "secret://networkos/cloudflare/tunnel_token").strip()
        token = self._get_secret(token_ref)
        if not token:
            return CloudflareExecutionStatus(False, f"missing_cloudflare_tunnel_token:{token_ref}", public_hostname=hostname)

        # Create or reuse a single tunnel record by name.
        # Minimal strategy: if a tunnel with same provider+name exists, reuse it.
        existing = None
        for t in self.service.list_tunnels():
            if t.provider == "cloudflare" and t.name == tunnel_name:
                existing = t
                break
        if existing is None:
            tunnel_id = self.service.create_tunnel(
                provider="cloudflare",
                name=tunnel_name,
                public_hostname=hostname or "(unknown)",
                local_target=local_target,
                token=token,
                mode="http",
            )
        else:
            tunnel_id = existing.tunnel_id

        ok = self.service.start_tunnel(tunnel_id)
        if not ok:
            return CloudflareExecutionStatus(False, "tunnel_start_failed", public_hostname=hostname)

        # Access requirement is considered enabled if both secret refs are present and resolvable.
        cid_ref = str(params.get("access_client_id_ref") or "secret://networkos/cloudflare/access_client_id").strip()
        csec_ref = str(params.get("access_client_secret_ref") or "secret://networkos/cloudflare/access_client_secret").strip()
        cid = self._get_secret(cid_ref)
        csec = self._get_secret(csec_ref)
        access_required = bool(hostname and cid and csec)

        enforce_access = bool(params.get("enforce_access") if "enforce_access" in (params or {}) else self._get_cfg("network.cloudflare.enforce_access", True))
        probe_path = str(params.get("probe_path") or self._get_cfg("network.cloudflare.health_path", "/api/health") or "/api/health").strip() or "/api/health"
        if access_required and enforce_access:
            probe = self._probe_access(hostname=hostname, path=probe_path, client_id=cid, client_secret=csec)
            if not probe.ok:
                return probe

        return CloudflareExecutionStatus(True, "tunnel_active", public_hostname=hostname or None, access_required=access_required)

    def revoke(self, params: Dict[str, Any]) -> CloudflareExecutionStatus:
        tunnel_name = str(params.get("tunnel_name") or "octopusos").strip()
        hostname = str(params.get("hostname") or "").strip()
        for t in self.service.list_tunnels():
            if t.provider == "cloudflare" and t.name == tunnel_name:
                try:
                    self.service.stop_tunnel(t.tunnel_id)
                except Exception as e:
                    return CloudflareExecutionStatus(False, f"stop_failed:{e}", public_hostname=hostname or None)
                return CloudflareExecutionStatus(True, "tunnel_stopped", public_hostname=hostname or None)
        return CloudflareExecutionStatus(True, "no_tunnel", public_hostname=hostname or None)

    def get_status(self, params: Dict[str, Any]) -> CloudflareExecutionStatus:
        tunnel_name = str(params.get("tunnel_name") or "octopusos").strip()
        hostname = str(params.get("hostname") or "").strip()
        for t in self.service.list_tunnels():
            if t.provider == "cloudflare" and t.name == tunnel_name:
                st = self.service.get_tunnel_status(t.tunnel_id) or {}
                is_running = bool(st.get("is_running"))
                return CloudflareExecutionStatus(
                    bool(is_running),
                    "active" if is_running else "inactive",
                    public_hostname=hostname or t.public_hostname,
                    access_required=False,
                )
        return CloudflareExecutionStatus(False, "not_configured", public_hostname=hostname or None)
