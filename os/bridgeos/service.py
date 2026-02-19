from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Dict, Optional

from octopusos.bridgeos.store import BridgeBinding, BridgeProfile, BridgeStore
from octopusos.networkos.capabilities.engine import NetworkCapabilityEngine
from octopusos.networkos.config_store import NetworkConfigStore
from octopusos.networkos.service import NetworkOSService
from octopusos.webui.secrets import SecretStore


@dataclass
class ResolvedBridgeRuntime:
    profile_id: str
    bridge_base_url: str
    send_path: str
    webhook_token: Optional[str]
    cloudflare_proxy_url: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "bridge_base_url": self.bridge_base_url,
            "send_path": self.send_path,
            "webhook_token": self.webhook_token,
            "cloudflare_proxy_url": self.cloudflare_proxy_url,
        }


class BridgeService:
    _DNS_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
    def __init__(
        self,
        *,
        store: Optional[BridgeStore] = None,
        secrets: Optional[SecretStore] = None,
        network_engine: Optional[NetworkCapabilityEngine] = None,
        network_config: Optional[NetworkConfigStore] = None,
        network_service: Optional[NetworkOSService] = None,
    ):
        self.store = store or BridgeStore()
        self.secrets = secrets or SecretStore()
        self.network_engine = network_engine or NetworkCapabilityEngine()
        self.network_config = network_config or NetworkConfigStore()
        self.network_service = network_service or NetworkOSService()

    def list_profiles(self) -> list[BridgeProfile]:
        return self.store.list_profiles()

    def get_profile(self, profile_id: str) -> Optional[BridgeProfile]:
        return self.store.get_profile(profile_id)

    def create_profile(
        self,
        *,
        name: str,
        provider: str,
        bridge_base_url: str,
        send_path: str,
        webhook_token: Optional[str] = None,
        local_target: Optional[str] = None,
        cloudflare_hostname: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BridgeProfile:
        profile = self.store.create_profile(
            name=str(name or "").strip() or "Bridge Profile",
            provider=str(provider or "custom").strip() or "custom",
            bridge_base_url=self._normalize_base_url(bridge_base_url),
            send_path=self._normalize_send_path(send_path),
            webhook_token_ref=None,
            local_target=self._normalize_optional(local_target),
            cloudflare_hostname=self._normalize_cloudflare_hostname(cloudflare_hostname),
            metadata=metadata or {},
        )
        token = str(webhook_token or "").strip()
        if token:
            secret_ref = self._webhook_secret_ref(profile.profile_id)
            self.secrets.set(secret_ref, token)
            updated = self.store.update_profile(profile.profile_id, patch={"webhook_token_ref": secret_ref})
            if updated:
                profile = updated
        return profile

    def update_profile(
        self,
        profile_id: str,
        *,
        patch: Dict[str, Any],
    ) -> Optional[BridgeProfile]:
        current = self.store.get_profile(profile_id)
        if not current:
            return None

        normalized_patch: Dict[str, Any] = {}
        if "name" in patch:
            normalized_patch["name"] = str(patch.get("name") or "").strip() or current.name
        if "provider" in patch:
            normalized_patch["provider"] = str(patch.get("provider") or "").strip() or current.provider
        if "bridge_base_url" in patch:
            normalized_patch["bridge_base_url"] = self._normalize_base_url(str(patch.get("bridge_base_url") or ""))
        if "send_path" in patch:
            normalized_patch["send_path"] = self._normalize_send_path(str(patch.get("send_path") or ""))
        if "local_target" in patch:
            normalized_patch["local_target"] = self._normalize_optional(patch.get("local_target"))
        if "cloudflare_hostname" in patch:
            normalized_patch["cloudflare_hostname"] = self._normalize_cloudflare_hostname(patch.get("cloudflare_hostname"))
        if "metadata" in patch and isinstance(patch.get("metadata"), dict):
            normalized_patch["metadata"] = patch.get("metadata")

        # secret handling: empty string clears secret; masked value keeps secret unchanged.
        if "webhook_token" in patch:
            token_value = patch.get("webhook_token")
            token = str(token_value or "").strip()
            if token == "***":
                pass
            elif not token:
                if current.webhook_token_ref:
                    self.secrets.delete(current.webhook_token_ref)
                normalized_patch["webhook_token_ref"] = None
            else:
                secret_ref = current.webhook_token_ref or self._webhook_secret_ref(profile_id)
                self.secrets.set(secret_ref, token)
                normalized_patch["webhook_token_ref"] = secret_ref

        updated = self.store.update_profile(profile_id, patch=normalized_patch)
        return updated

    def bind_channel(self, *, channel_id: str, profile_id: str) -> BridgeBinding:
        profile = self.store.get_profile(profile_id)
        if not profile:
            raise ValueError("profile_not_found")
        binding = self.store.upsert_binding(channel_id=channel_id, profile_id=profile_id)
        self.store.append_event(
            event_type="bridge_binding_upserted",
            profile_id=profile_id,
            channel_id=channel_id,
            payload={"channel_id": channel_id, "profile_id": profile_id},
        )
        return binding

    def get_channel_binding(self, channel_id: str) -> Optional[BridgeBinding]:
        return self.store.get_binding_by_channel(channel_id)

    def resolve_runtime_for_channel(self, *, channel_id: str, config: Optional[Dict[str, Any]] = None) -> Optional[ResolvedBridgeRuntime]:
        cfg = config or {}
        profile_id = str(cfg.get("bridge_profile_id") or "").strip()
        if not profile_id:
            binding = self.store.get_binding_by_channel(channel_id)
            profile_id = str(binding.profile_id).strip() if binding else ""
        if not profile_id:
            return None
        return self.resolve_runtime_for_profile(profile_id)

    def resolve_runtime_for_profile(self, profile_id: str) -> Optional[ResolvedBridgeRuntime]:
        profile = self.store.get_profile(profile_id)
        if not profile:
            return None
        token = self._resolve_webhook_token(profile)
        proxy_url = self.resolve_cloudflare_proxy_url(profile)
        return ResolvedBridgeRuntime(
            profile_id=profile.profile_id,
            bridge_base_url=profile.bridge_base_url,
            send_path=profile.send_path,
            webhook_token=token,
            cloudflare_proxy_url=proxy_url,
        )

    def request_cloudflare_exposure(self, *, profile_id: str, requested_by: str) -> Dict[str, Any]:
        profile = self.store.get_profile(profile_id)
        if not profile:
            return {"ok": False, "error": "profile_not_found"}

        local_target = str(profile.local_target or "").strip() or "http://127.0.0.1:8080"
        hostname = str(profile.cloudflare_hostname or "").strip()
        params: Dict[str, Any] = {
            "scope": f"/personal/bridgeos/{profile.profile_id}",
            "local_target": local_target,
            "hostname": hostname,
            "tunnel_name": f"bridgeos-{profile.profile_id[:8]}",
        }
        res = self.network_engine.request_capability(
            capability="network.tunnel.enable",
            params=params,
            requested_by=requested_by,
        )
        self.store.append_event(
            event_type="bridge_cloudflare_expose_requested",
            profile_id=profile.profile_id,
            payload={"request": res.get("request"), "ok": bool(res.get("ok"))},
        )
        return res

    def resolve_cloudflare_proxy_url(self, profile: BridgeProfile) -> Optional[str]:
        host = str(profile.cloudflare_hostname or "").strip()
        if host:
            return f"https://{host}"

        try:
            cfg = self.network_config.resolve_cloudflare_config()
            cfg_host = str((cfg.get("network.cloudflare.hostname").value if cfg.get("network.cloudflare.hostname") else "") or "").strip()  # type: ignore[union-attr]
            if cfg_host:
                return f"https://{cfg_host}"
        except Exception:
            pass

        target = str(profile.local_target or "").strip()
        target_port = self._extract_port(target)
        try:
            for tunnel in self.network_service.list_tunnels():
                if str(tunnel.provider).strip().lower() != "cloudflare":
                    continue
                if not bool(tunnel.is_enabled):
                    continue
                tunnel_port = self._extract_port(str(tunnel.local_target or "").strip())
                if target_port is not None and tunnel_port is not None and target_port != tunnel_port:
                    continue
                tunnel_host = str(tunnel.public_hostname or "").strip()
                if tunnel_host:
                    return f"https://{tunnel_host}"
        except Exception:
            pass
        return None

    def _resolve_webhook_token(self, profile: BridgeProfile) -> Optional[str]:
        ref = str(profile.webhook_token_ref or "").strip()
        if not ref:
            return None
        val = self.secrets.get(ref)
        token = str(val or "").strip()
        return token or None

    @staticmethod
    def _normalize_base_url(raw: str) -> str:
        out = str(raw or "").strip().rstrip("/")
        if not out:
            raise ValueError("bridge_base_url_required")
        if not (out.startswith("http://") or out.startswith("https://")):
            raise ValueError("bridge_base_url_invalid")
        return out

    @staticmethod
    def _normalize_send_path(raw: str) -> str:
        p = str(raw or "").strip() or "/api/imessage/send"
        if not p.startswith("/"):
            p = f"/{p}"
        return p

    @staticmethod
    def _normalize_optional(value: Any) -> Optional[str]:
        v = str(value or "").strip()
        return v or None

    @classmethod
    def _normalize_cloudflare_hostname(cls, value: Any) -> Optional[str]:
        raw = str(value or "").strip().lower()
        if not raw:
            return None
        if raw.startswith("http://") or raw.startswith("https://"):
            raise ValueError("cloudflare_hostname_invalid")
        if "/" in raw or raw.startswith(".") or raw.endswith("."):
            raise ValueError("cloudflare_hostname_invalid")
        labels = [x for x in raw.split(".") if x]
        if len(labels) < 2:
            raise ValueError("cloudflare_hostname_invalid")
        if len(raw) > 253:
            raise ValueError("cloudflare_hostname_invalid")
        for label in labels:
            if len(label) > 63 or not cls._DNS_LABEL_RE.match(label):
                raise ValueError("cloudflare_hostname_invalid")
        return raw

    @staticmethod
    def _extract_port(target: str) -> Optional[int]:
        from urllib.parse import urlparse

        raw = str(target or "").strip()
        if not raw:
            return None
        try:
            parsed = urlparse(raw if "://" in raw else f"http://{raw}")
            if parsed.port:
                return int(parsed.port)
        except Exception:
            return None
        return None

    @staticmethod
    def _webhook_secret_ref(profile_id: str) -> str:
        return f"secret://bridgeos/profiles/{profile_id}/webhook_token"
