"""CommunicationOS runtime wiring.

This module instantiates channel adapters based on manifests + ChannelConfigStore,
registers them into MessageBus, and routes inbound messages into OctopusOS ChatEngine.

Goal for this repo task: enable a real, testable WhatsApp Web QR login channel
and keep the rest of the system minimally impacted.
"""

from __future__ import annotations

import json
import hashlib
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from octopusos.communicationos.audit import AuditMiddleware, AuditStore
from octopusos.communicationos.bindings_store import ChannelBindingsStore
from octopusos.communicationos.commands import CommandProcessor
from octopusos.communicationos.dedupe import DedupeMiddleware, DedupeStore
from octopusos.communicationos.manifest import ChannelManifest
from octopusos.communicationos.message_bus import MessageBus
from octopusos.communicationos.models import InboundMessage, OutboundMessage, MessageType
from octopusos.communicationos.rate_limit import RateLimitMiddleware, RateLimitStore
from octopusos.communicationos.registry import ChannelConfigStore, ChannelRegistry
from octopusos.communicationos.security import PolicyEnforcer
from octopusos.communicationos.session_router import SessionRouter
from octopusos.communicationos.session_store import SessionStore
from octopusos.core.chat.engine import ChatEngine
from octopusos.core.chat.service import ChatService

logger = logging.getLogger(__name__)

BRIDGE_CHANNEL_PLATFORMS: Dict[str, str] = {
    "line": "line",
    "facebook_messenger": "facebook_messenger",
    "instagram_dm": "instagram_dm",
    "viber": "viber",
    "matrix": "matrix",
    "google_chat": "google_chat",
    "mattermost": "mattermost",
    "rocket_chat": "rocket_chat",
    "zulip": "zulip",
    "wechat_official": "wechat_official",
    "wecom": "wecom",
    "kakaotalk": "kakaotalk",
}


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _comm_trace(event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    try:
        logger.info("comm_trace %s", json.dumps(payload, ensure_ascii=False, sort_keys=True))
    except Exception:
        logger.info("comm_trace %s %s", event, fields)


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return bool(default)


def _mask_config_for_ui(manifest: ChannelManifest, config: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(config or {})
    secret_fields = {f.name for f in (manifest.required_config_fields or []) if getattr(f, "secret", False)}
    for k in list(out.keys()):
        if k in secret_fields and out.get(k):
            out[k] = "***"
    return out


@dataclass
class ChannelRuntimeState:
    adapter: Any
    manifest: ChannelManifest


class CommunicationRuntime:
    def __init__(self):
        self.registry = ChannelRegistry()
        self.config_store = ChannelConfigStore()
        self.session_router = SessionRouter(self.registry)
        self.session_store = SessionStore()
        self.bindings_store = ChannelBindingsStore()

        self.bus = MessageBus()
        self._install_middleware()
        self.bus.add_inbound_handler(self._handle_inbound)

        self.chat_service = ChatService()
        self.chat_engine = ChatEngine(self.chat_service)

        self._adapters: Dict[str, ChannelRuntimeState] = {}
        self._lock = threading.RLock()
        self._inbound_conversation_locks: Dict[str, threading.Lock] = {}
        self._inbound_conversation_locks_guard = threading.RLock()

        self._command_processor = CommandProcessor(self.session_store)

    def _install_middleware(self) -> None:
        dedupe_store = DedupeStore()
        limiter = RateLimitStore()
        audit_store = AuditStore()
        self.bus.add_middleware(DedupeMiddleware(dedupe_store))
        self.bus.add_middleware(RateLimitMiddleware(limiter))
        self.bus.add_middleware(AuditMiddleware(audit_store))
        self.bus.add_middleware(PolicyEnforcer())

    def list_marketplace(self) -> list[Dict[str, Any]]:
        manifests = self.registry.list_manifests()
        configured = {c["channel_id"]: c for c in self.config_store.list_channels()}

        items: list[Dict[str, Any]] = []
        for m in manifests:
            st = configured.get(m.id) or {}
            items.append(
                {
                    **m.to_dict(),
                    "enabled": bool(st.get("enabled", False)),
                    "status": st.get("status", "needs_setup"),
                    "last_error": st.get("last_error"),
                    "last_heartbeat_at": st.get("last_heartbeat_at"),
                }
            )
        return items

    def get_channel_config_for_ui(self, channel_id: str) -> Dict[str, Any]:
        manifest = self.registry.get_manifest(channel_id)
        if not manifest:
            raise ValueError(f"unknown_channel:{channel_id}")
        cfg = self.config_store.get_config(channel_id) or {}
        return {"channel_id": channel_id, "config": _mask_config_for_ui(manifest, cfg)}

    def configure_channel(self, channel_id: str, config: Dict[str, Any], *, performed_by: str = "system") -> None:
        ok, err = self.registry.validate_config(channel_id, config or {})
        if not ok:
            raise ValueError(err or "invalid_config")
        self.config_store.save_config(channel_id, config or {}, performed_by=performed_by)
        # Hot apply: if channel is currently enabled, reload adapter in-place.
        # This avoids requiring a service restart for config changes.
        try:
            if self.config_store.is_enabled(channel_id):
                self.stop_adapter(channel_id)
                self.ensure_adapter_started(channel_id)
        except Exception as e:
            logger.warning("Hot reload failed for channel %s: %s", channel_id, e)

    def enable_channel(self, channel_id: str, enabled: bool, *, performed_by: str = "system") -> None:
        self.config_store.set_enabled(channel_id, enabled, performed_by=performed_by)
        if enabled:
            self.ensure_adapter_started(channel_id)
        else:
            self.stop_adapter(channel_id)

    def ensure_adapter_started(self, channel_id: str) -> None:
        with self._lock:
            if channel_id in self._adapters:
                return
            manifest = self.registry.get_manifest(channel_id)
            if not manifest:
                raise ValueError(f"unknown_channel:{channel_id}")

            cfg = self.config_store.get_config(channel_id) or {}
            adapter = self._instantiate_adapter(channel_id, cfg)

            # Register for outbound sends.
            self.bus.register_adapter(channel_id, adapter)

            # Start lifecycle if supported.
            if hasattr(adapter, "start"):
                try:
                    adapter.start()
                except Exception as e:
                    logger.warning("Failed starting adapter %s: %s", channel_id, e)

            self._adapters[channel_id] = ChannelRuntimeState(adapter=adapter, manifest=manifest)

    def stop_adapter(self, channel_id: str) -> None:
        with self._lock:
            st = self._adapters.pop(channel_id, None)
            self.bus.unregister_adapter(channel_id)
            if st and hasattr(st.adapter, "stop"):
                try:
                    st.adapter.stop()
                except Exception:
                    pass

    def _instantiate_adapter(self, channel_id: str, cfg: Dict[str, Any]) -> Any:
        if channel_id == "whatsapp_web":
            from octopusos.communicationos.channels.whatsapp_web import WhatsAppWebAdapter

            return WhatsAppWebAdapter(
                channel_id=channel_id,
                state_dir=cfg.get("state_dir"),
                chrome_path=cfg.get("chrome_path"),
                allow_from_me_inbound=_as_bool(cfg.get("allow_from_me_inbound", False), default=False),
                message_bus=self.bus,
            )

        if channel_id == "feishu":
            from octopusos.communicationos.channels.feishu import FeishuAdapter

            return FeishuAdapter(
                channel_id=channel_id,
                app_id=str(cfg.get("app_id") or ""),
                app_secret=str(cfg.get("app_secret") or ""),
                verification_token=str(cfg.get("verification_token") or ""),
                encrypt_key=str(cfg.get("encrypt_key") or "") or None,
                message_bus=self.bus,
            )

        if channel_id == "whatsapp_twilio":
            from octopusos.communicationos.channels.whatsapp_twilio import WhatsAppTwilioAdapter

            return WhatsAppTwilioAdapter(
                channel_id=channel_id,
                account_sid=str(cfg.get("account_sid") or ""),
                auth_token=str(cfg.get("auth_token") or ""),
                phone_number=str(cfg.get("phone_number") or ""),
                messaging_service_sid=str(cfg.get("messaging_service_sid") or "") or None,
            )

        if channel_id == "teams":
            from octopusos.communicationos.channels.teams import TeamsAdapter

            return TeamsAdapter(
                channel_id=channel_id,
                tenant_id=str(cfg.get("tenant_id") or ""),
                client_id=str(cfg.get("client_id") or ""),
                client_secret=str(cfg.get("client_secret") or ""),
                bot_app_id=str(cfg.get("bot_app_id") or cfg.get("client_id") or ""),
                message_bus=self.bus,
            )

        if channel_id == "imessage":
            from octopusos.communicationos.channels.imessage import IMessageAdapter

            bridge_base_url = str(cfg.get("bridge_base_url") or "").strip()
            webhook_token = str(cfg.get("webhook_token") or "").strip() or None
            send_path = str(cfg.get("send_path") or "/api/imessage/send").strip() or "/api/imessage/send"
            assistant_display_name = str(cfg.get("assistant_display_name") or "OctopusOS").strip()
            allow_from_me_inbound = _as_bool(cfg.get("allow_from_me_inbound", False), default=False)
            bridge_profile_id = str(cfg.get("bridge_profile_id") or "").strip()

            # BridgeOS-first resolution for iMessage:
            # - explicit bridge_profile_id in channel config
            # - fallback to BridgeOS channel binding
            if bridge_profile_id or channel_id == "imessage":
                try:
                    from octopusos.bridgeos.service import BridgeService

                    runtime = BridgeService().resolve_runtime_for_channel(channel_id=channel_id, config=cfg)
                    if runtime:
                        bridge_base_url = runtime.bridge_base_url or bridge_base_url
                        webhook_token = runtime.webhook_token or webhook_token
                        send_path = runtime.send_path or send_path
                except Exception:
                    # Keep backward-compatible direct config path if BridgeOS is unavailable.
                    pass

            return IMessageAdapter(
                channel_id=channel_id,
                bridge_base_url=bridge_base_url,
                webhook_token=webhook_token,
                send_path=send_path,
                assistant_display_name=assistant_display_name,
                allow_from_me_inbound=allow_from_me_inbound,
                message_bus=self.bus,
            )

        if channel_id in BRIDGE_CHANNEL_PLATFORMS:
            from octopusos.bridgeos.service import BridgeService
            from octopusos.communicationos.channels.bridge_im import GenericBridgeIMAdapter

            runtime = BridgeService().resolve_runtime_for_channel(channel_id=channel_id, config=cfg)
            if not runtime:
                raise ValueError("bridge_profile_required")
            return GenericBridgeIMAdapter(
                channel_id=channel_id,
                platform=BRIDGE_CHANNEL_PLATFORMS[channel_id],
                bridge_base_url=runtime.bridge_base_url,
                webhook_token=runtime.webhook_token,
                send_path=runtime.send_path,
                message_bus=self.bus,
            )

        raise ValueError(f"adapter_not_implemented:{channel_id}")

    def get_adapter_status(self, channel_id: str) -> Dict[str, Any]:
        with self._lock:
            st = self._adapters.get(channel_id)
        if not st:
            return {"channel_id": channel_id, "state": "stopped"}
        adapter = st.adapter
        if hasattr(adapter, "get_status"):
            try:
                return adapter.get_status()
            except Exception as e:
                return {"channel_id": channel_id, "state": "error", "detail": str(e)}
        return {"channel_id": channel_id, "state": "running"}

    def get_adapter_qr(self, channel_id: str) -> Dict[str, Any]:
        with self._lock:
            st = self._adapters.get(channel_id)
        if not st:
            raise ValueError("not_running")
        adapter = st.adapter
        if not hasattr(adapter, "get_qr"):
            raise ValueError("qr_not_supported")
        qr = adapter.get_qr()
        if not qr:
            return {"ok": False, "qr": None}
        return {"ok": True, "qr": qr}

    def send_outbound_text(self, *, channel_id: str, peer_user_key: str, peer_conversation_key: str, text: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        self.ensure_adapter_started(channel_id)
        msg = OutboundMessage(
            channel_id=channel_id,
            user_key=peer_user_key,
            conversation_key=peer_conversation_key,
            type=MessageType.TEXT,
            text=text,
            metadata={
                "session_id": session_id,
                "content_hash": _hash_text(text),
            },
        )
        ctx = self.bus.send_outbound(msg)
        # send_outbound is async; run it in a temporary loop via asyncio.run in caller.
        return {"ok": True, "queued": True, "message_id": ctx.message_id if hasattr(ctx, "message_id") else None}

    def _handle_inbound(self, message: InboundMessage) -> None:
        inbound_t0 = time.perf_counter()
        _comm_trace(
            "inbound_received",
            channel_id=message.channel_id,
            message_id=message.message_id,
            conversation_key=message.conversation_key,
            user_key=message.user_key,
            text_len=len(str(message.text or "")),
        )
        # Fast-path session reset commands for IM usage:
        # /new, /start, /session new, /resume, /session resume
        try:
            text = " ".join(str(message.text or "").strip().lower().split())
            if text in {"/new", "/start", "/session new"}:
                _comm_trace("shortcut_detected", command=text, message_id=message.message_id)
                self._handle_session_new_shortcut(message)
                return
            if text in {"/clear", "/session clear"}:
                _comm_trace("shortcut_detected", command=text, message_id=message.message_id)
                self._handle_session_clear_shortcut(message)
                return
            if text in {"/resume", "/session resume"}:
                _comm_trace("shortcut_detected", command=text, message_id=message.message_id)
                self._handle_session_resume_shortcut(message)
                return
        except Exception:
            logger.exception("Session shortcut failed")

        # Commands are handled inline (cheap) and responded via same channel.
        try:
            text = str(message.text or "")
            if self._command_processor.is_command(text):
                _comm_trace("command_detected", command=text, message_id=message.message_id)
                response = self._command_processor.process_command(
                    text=text,
                    channel_id=message.channel_id,
                    user_key=message.user_key,
                    conversation_key=message.conversation_key,
                )
                outbound = OutboundMessage(
                    channel_id=response.channel_id,
                    user_key=response.user_key,
                    conversation_key=response.conversation_key,
                    type=response.type,
                    text=response.text,
                    metadata={**(response.metadata or {}), "source": "command"},
                )
                # fire-and-forget in a background thread to avoid blocking bus handlers
                threading.Thread(
                    target=lambda: _run_async_send(self.bus, outbound),
                    daemon=True,
                    name="commos-cmd-send",
                ).start()
                _comm_trace(
                    "command_enqueued",
                    command=text,
                    message_id=message.message_id,
                    elapsed_ms=int((time.perf_counter() - inbound_t0) * 1000),
                )
                return
        except Exception:
            logger.exception("Command processing failed")
            _comm_trace("command_failed", message_id=message.message_id)

        threading.Thread(
            target=lambda: self._handle_inbound_chat_serialized(message),
            daemon=True,
            name="commos-inbound-chat",
        ).start()

    def _get_inbound_lock(self, message: InboundMessage) -> threading.Lock:
        key = f"{message.channel_id}:{message.user_key}:{message.conversation_key}"
        with self._inbound_conversation_locks_guard:
            lk = self._inbound_conversation_locks.get(key)
            if lk is None:
                lk = threading.Lock()
                self._inbound_conversation_locks[key] = lk
            return lk

    def _handle_inbound_chat_serialized(self, message: InboundMessage) -> None:
        lk = self._get_inbound_lock(message)
        with lk:
            self._handle_inbound_chat(message)

    def _handle_session_new_shortcut(
        self,
        message: InboundMessage,
        *,
        command_name: str = "session_new",
        success_text_prefix: str = "✅ New session started",
    ) -> None:
        """Create/switch to a new chat session for the same lookup key.

        This is purpose-built for single-account IM workflows where users type
        `/new` or `/start` to rotate context without needing another account.
        """
        try:
            ctx = self.session_router.resolve(message)
        except Exception as e:
            logger.warning("Session routing failed for /new shortcut: %s", e)
            return

        current_binding = self.bindings_store.get(channel_id=ctx.channel_id, session_lookup_key=ctx.session_lookup_key)
        cfg = self.config_store.get_config(ctx.channel_id) or {}
        if current_binding:
            model_route = str(current_binding.model_route or "local").strip() or "local"
            provider = str(current_binding.provider or "").strip() or ("ollama" if model_route == "local" else "openai")
            model = str(current_binding.model or "").strip()
        else:
            model_route = str(cfg.get("model_route") or "local").strip() or "local"
            provider = str(cfg.get("provider") or "").strip() or ("ollama" if model_route == "local" else "openai")
            model = str(cfg.get("model") or "").strip()
        # Bot-mode default: low-latency on for all channels unless explicitly disabled in channel config.
        low_latency_mode = _as_bool(cfg.get("low_latency_mode", True), default=True)

        chat_session = self.chat_service.create_session(
            title=f"{ctx.channel_id}:{ctx.user_key}",
            metadata={
                "source": "communicationos",
                "model_route": model_route,
                "provider": provider,
                "model": model,
                "channel_id": ctx.channel_id,
                "user_key": ctx.user_key,
                "conversation_key": ctx.conversation_key,
                "low_latency_mode": low_latency_mode,
            },
        )
        new_session_id = str(chat_session.session_id)

        self.session_store.create_session(
            channel_id=ctx.channel_id,
            user_key=ctx.user_key,
            conversation_key=ctx.conversation_key,
            scope=ctx.session_scope,
            title="new session",
            session_id=new_session_id,
            metadata={"session_lookup_key": ctx.session_lookup_key},
        )
        self.bindings_store.upsert(
            channel_id=ctx.channel_id,
            session_lookup_key=ctx.session_lookup_key,
            session_id=new_session_id,
            model_route=model_route,
            provider=provider,
            model=model,
            user_key=ctx.user_key,
            conversation_key=ctx.conversation_key,
        )

        outbound = OutboundMessage(
            channel_id=message.channel_id,
            user_key=message.user_key,
            conversation_key=message.conversation_key,
            type=MessageType.TEXT,
            text=f"{success_text_prefix}: {new_session_id}",
            metadata={"source": "command", "command": command_name},
        )
        threading.Thread(
            target=lambda: _run_async_send(self.bus, outbound),
            daemon=True,
            name="commos-cmd-send",
        ).start()

    def _handle_session_clear_shortcut(self, message: InboundMessage) -> None:
        """Clear current context by rotating to a fresh session."""
        self._handle_session_new_shortcut(
            message,
            command_name="session_clear",
            success_text_prefix="🧹 Context cleared. New session started",
        )

    def _handle_session_resume_shortcut(self, message: InboundMessage) -> None:
        """Switch current lookup key back to the previous non-closed session."""
        try:
            ctx = self.session_router.resolve(message)
        except Exception as e:
            logger.warning("Session routing failed for /resume shortcut: %s", e)
            return

        current_binding = self.bindings_store.get(channel_id=ctx.channel_id, session_lookup_key=ctx.session_lookup_key)
        current_session_id = str(current_binding.session_id or "").strip() if current_binding else ""

        sessions = self.session_store.list_sessions(channel_id=ctx.channel_id, user_key=ctx.user_key, limit=100)
        target_session_id: Optional[str] = None
        for session in sessions:
            session_id = str(session["session_id"]).strip()
            if not session_id or session_id == current_session_id:
                continue
            if str(session.get("status", "active")).lower() in {"closed", "archived"}:
                continue
            # For USER_CONVERSATION scope, resume only within the same conversation.
            if ctx.session_scope.value == "user_conversation":
                if str(session.get("conversation_key", "")) != str(ctx.conversation_key):
                    continue
            target_session_id = session_id
            break

        if not target_session_id:
            outbound = OutboundMessage(
                channel_id=message.channel_id,
                user_key=message.user_key,
                conversation_key=message.conversation_key,
                type=MessageType.TEXT,
                text="ℹ️ No previous session available. Use /new to create one.",
                metadata={"source": "command", "command": "session_resume"},
            )
            threading.Thread(
                target=lambda: _run_async_send(self.bus, outbound),
                daemon=True,
                name="commos-cmd-send",
            ).start()
            return

        try:
            self.session_store.switch_session(
                channel_id=ctx.channel_id,
                user_key=ctx.user_key,
                conversation_key=ctx.conversation_key,
                new_session_id=target_session_id,
            )
        except Exception as e:
            logger.warning("Failed switching previous session for /resume: %s", e)
            outbound = OutboundMessage(
                channel_id=message.channel_id,
                user_key=message.user_key,
                conversation_key=message.conversation_key,
                type=MessageType.TEXT,
                text=f"❌ Failed to resume previous session: {e}",
                metadata={"source": "command", "command": "session_resume"},
            )
            threading.Thread(
                target=lambda: _run_async_send(self.bus, outbound),
                daemon=True,
                name="commos-cmd-send",
            ).start()
            return

        if current_binding:
            model_route = str(current_binding.model_route or "local").strip() or "local"
            provider = str(current_binding.provider or "").strip() or ("ollama" if model_route == "local" else "openai")
            model = str(current_binding.model or "").strip()
        else:
            cfg = self.config_store.get_config(ctx.channel_id) or {}
            model_route = str(cfg.get("model_route") or "local").strip() or "local"
            provider = str(cfg.get("provider") or "").strip() or ("ollama" if model_route == "local" else "openai")
            model = str(cfg.get("model") or "").strip()

        self.bindings_store.upsert(
            channel_id=ctx.channel_id,
            session_lookup_key=ctx.session_lookup_key,
            session_id=target_session_id,
            model_route=model_route,
            provider=provider,
            model=model,
            user_key=ctx.user_key,
            conversation_key=ctx.conversation_key,
        )

        outbound = OutboundMessage(
            channel_id=message.channel_id,
            user_key=message.user_key,
            conversation_key=message.conversation_key,
            type=MessageType.TEXT,
            text=f"✅ Resumed previous session: {target_session_id}",
            metadata={"source": "command", "command": "session_resume"},
        )
        threading.Thread(
            target=lambda: _run_async_send(self.bus, outbound),
            daemon=True,
            name="commos-cmd-send",
        ).start()

    def _handle_inbound_chat(self, message: InboundMessage) -> None:
        t0 = time.perf_counter()
        def _create_and_bind_session(*, source: str, existing_binding: Any = None) -> tuple[Any, str]:
            if existing_binding is not None:
                model_route_local = str(existing_binding.model_route or "local").strip() or "local"
                provider_local = str(existing_binding.provider or "").strip() or ("ollama" if model_route_local == "local" else "openai")
                model_local = str(existing_binding.model or "").strip()
            else:
                model_route_local = str(cfg.get("model_route") or "local").strip() or "local"
                provider_local = str(cfg.get("provider") or "").strip()
                model_local = str(cfg.get("model") or "").strip()
                if not provider_local:
                    provider_local = "ollama" if model_route_local == "local" else "openai"
            # Bot-mode default: low-latency on for all channels unless explicitly disabled.
            low_latency_mode_local = _as_bool(cfg.get("low_latency_mode", True), default=True)

            chat_session_local = self.chat_service.create_session(
                title=ctx.title_hint or f"{ctx.channel_id}:{ctx.user_key}",
                metadata={
                    "source": "communicationos",
                    "model_route": model_route_local,
                    "provider": provider_local,
                    "model": model_local,
                    "channel_id": ctx.channel_id,
                    "user_key": ctx.user_key,
                    "conversation_key": ctx.conversation_key,
                    "low_latency_mode": low_latency_mode_local,
                },
            )
            session_id_local = str(chat_session_local.session_id)
            self.session_store.create_session(
                channel_id=ctx.channel_id,
                user_key=ctx.user_key,
                conversation_key=ctx.conversation_key,
                scope=ctx.session_scope,
                title=ctx.title_hint,
                session_id=session_id_local,
                metadata={"session_lookup_key": ctx.session_lookup_key},
            )
            new_binding = self.bindings_store.upsert(
                channel_id=ctx.channel_id,
                session_lookup_key=ctx.session_lookup_key,
                session_id=session_id_local,
                model_route=model_route_local,
                provider=provider_local,
                model=model_local,
                user_key=ctx.user_key,
                conversation_key=ctx.conversation_key,
            )
            _comm_trace(
                "session_bound",
                message_id=message.message_id,
                channel_id=ctx.channel_id,
                session_id=session_id_local,
                source=source,
            )
            return new_binding, session_id_local

        try:
            ctx = self.session_router.resolve(message)
        except Exception as e:
            logger.warning("Session routing failed: %s", e)
            _comm_trace(
                "chat_route_failed",
                message_id=message.message_id,
                channel_id=message.channel_id,
                error=str(e),
            )
            return

        _comm_trace(
            "chat_routed",
            message_id=message.message_id,
            channel_id=ctx.channel_id,
            session_lookup_key=ctx.session_lookup_key,
            user_key=ctx.user_key,
            conversation_key=ctx.conversation_key,
        )

        cfg = self.config_store.get_config(ctx.channel_id) or {}
        status_enabled = (
            ctx.channel_id == "imessage"
            and _as_bool(cfg.get("processing_status_enabled", False), default=False)
        )
        status_text = str(cfg.get("processing_status_text") or "⏳ 正在处理中，请稍候…").strip()
        if status_enabled and status_text:
            status_outbound = OutboundMessage(
                channel_id=ctx.channel_id,
                user_key=message.user_key,
                conversation_key=message.conversation_key,
                type=MessageType.TEXT,
                text=status_text,
                metadata={"source": "status", "status": "processing"},
            )
            _run_async_send(self.bus, status_outbound)
            _comm_trace(
                "status_sent",
                message_id=message.message_id,
                channel_id=ctx.channel_id,
                status_text=status_text,
                elapsed_ms=int((time.perf_counter() - t0) * 1000),
            )

        binding = self.bindings_store.get(channel_id=ctx.channel_id, session_lookup_key=ctx.session_lookup_key)
        if not binding:
            binding, session_id = _create_and_bind_session(source="created")
        else:
            # Teams should follow channel-level model changes immediately.
            # Existing bindings may keep stale model/provider values from earlier setup.
            if ctx.channel_id == "teams":
                cfg_model_route = str(cfg.get("model_route") or "local").strip() or "local"
                cfg_provider = str(cfg.get("provider") or "").strip() or (
                    "ollama" if cfg_model_route == "local" else "openai"
                )
                cfg_model = str(cfg.get("model") or "").strip()
                if (
                    str(binding.model_route or "").strip() != cfg_model_route
                    or str(binding.provider or "").strip() != cfg_provider
                    or str(binding.model or "").strip() != cfg_model
                ):
                    binding = self.bindings_store.upsert(
                        channel_id=ctx.channel_id,
                        session_lookup_key=ctx.session_lookup_key,
                        session_id=str(binding.session_id),
                        model_route=cfg_model_route,
                        provider=cfg_provider,
                        model=cfg_model,
                        user_key=ctx.user_key,
                        conversation_key=ctx.conversation_key,
                    )
                    _comm_trace(
                        "binding_synced_from_channel_config",
                        message_id=message.message_id,
                        channel_id=ctx.channel_id,
                        session_id=str(binding.session_id),
                        model_route=cfg_model_route,
                        provider=cfg_provider,
                        model=cfg_model,
                    )
            session_id = binding.session_id
            # Ensure session exists and metadata matches binding.
            try:
                if hasattr(self.chat_service, "get_session"):
                    self.chat_service.get_session(session_id)
                if hasattr(self.chat_service, "update_session_metadata"):
                    self.chat_service.update_session_metadata(
                        session_id=session_id,
                        metadata={
                            "model_route": binding.model_route,
                            "provider": binding.provider,
                            "model": binding.model,
                            "low_latency_mode": _as_bool(cfg.get("low_latency_mode", True), default=True),
                        },
                    )
                _comm_trace(
                    "session_bound",
                    message_id=message.message_id,
                    channel_id=ctx.channel_id,
                    session_id=session_id,
                    source="existing",
                )
            except Exception as e:
                _comm_trace(
                    "binding_stale",
                    message_id=message.message_id,
                    channel_id=ctx.channel_id,
                    session_id=session_id,
                    error=str(e),
                )
                binding, session_id = _create_and_bind_session(source="recreated", existing_binding=binding)

        user_text = message.text or ""
        if not user_text:
            return

        llm_t0 = time.perf_counter()
        recovered_once = False
        try:
            result = self.chat_engine.send_message(
                session_id=session_id,
                user_input=user_text,
                stream=False,
                idempotency_key=message.message_id,
            )
            assistant_text = str(result.get("content") or "").strip()
            _comm_trace(
                "llm_completed",
                message_id=message.message_id,
                session_id=session_id,
                channel_id=ctx.channel_id,
                elapsed_ms=int((time.perf_counter() - llm_t0) * 1000),
                reply_len=len(assistant_text),
                provider=str(getattr(binding, "provider", "") or cfg.get("provider") or ""),
                model=str(getattr(binding, "model", "") or cfg.get("model") or ""),
                policy_applied=str((result.get("metadata") or {}).get("policy_applied") or ""),
                blocked_capabilities=list((result.get("metadata") or {}).get("blocked_capabilities") or []),
            )
        except Exception as e:
            err_text = str(e)
            recoverable = ("FOREIGN KEY constraint failed" in err_text) or ("Chat session not found" in err_text)
            if recoverable:
                try:
                    binding, session_id = _create_and_bind_session(source="recovered_after_llm_failure", existing_binding=binding)
                    recovered_once = True
                    result = self.chat_engine.send_message(
                        session_id=session_id,
                        user_input=user_text,
                        stream=False,
                        idempotency_key=f"{message.message_id}:retry",
                    )
                    assistant_text = str(result.get("content") or "").strip()
                    _comm_trace(
                        "llm_recovered",
                        message_id=message.message_id,
                        session_id=session_id,
                        channel_id=ctx.channel_id,
                        elapsed_ms=int((time.perf_counter() - llm_t0) * 1000),
                    )
                except Exception as e2:
                    assistant_text = f"⚠️ chat_engine_failed: {e2}"
                    _comm_trace(
                        "llm_failed",
                        message_id=message.message_id,
                        session_id=session_id,
                        channel_id=ctx.channel_id,
                        elapsed_ms=int((time.perf_counter() - llm_t0) * 1000),
                        error=str(e2),
                        recovered_once=recovered_once,
                    )
            else:
                assistant_text = f"⚠️ chat_engine_failed: {e}"
                _comm_trace(
                    "llm_failed",
                    message_id=message.message_id,
                    session_id=session_id,
                    channel_id=ctx.channel_id,
                    elapsed_ms=int((time.perf_counter() - llm_t0) * 1000),
                    error=err_text,
                )

        if not assistant_text:
            return

        # Enterprise-facing channels must pass through a simple policy gate before replying.
        # This is intentionally lightweight for M1: it guarantees all replies are policy-audited.
        try:
            policy_mode = str(cfg.get("policy_mode") or "silent_allow").strip().lower()
        except Exception:
            policy_mode = "silent_allow"

        gate_decision = "allow"
        gate_reason = "silent_allow"
        reply_text = assistant_text
        if policy_mode == "block":
            gate_decision = "block"
            gate_reason = "policy_mode:block"
            reply_text = "Blocked by policy gate."
        elif policy_mode == "explain_confirm":
            gate_decision = "explain_confirm"
            gate_reason = "policy_mode:explain_confirm"
            # Minimal explain-confirm for M1: do not send the LLM output automatically.
            reply_text = "This reply requires approval (policy gate). Please approve in WebUI."
        _comm_trace(
            "policy_gate_decision",
            message_id=message.message_id,
            session_id=session_id,
            channel_id=ctx.channel_id,
            decision=gate_decision,
            reason=gate_reason,
        )

        outbound = OutboundMessage(
            channel_id=ctx.channel_id,
            user_key=message.user_key,
            conversation_key=message.conversation_key,
            type=MessageType.TEXT,
            text=reply_text,
            metadata={
                "session_id": session_id,
                "inbound_message_id": message.message_id,
                "content_hash": _hash_text(reply_text),
                "policy_gate": {"decision": gate_decision, "reason": gate_reason},
                "policy_applied": str((result.get("metadata") or {}).get("policy_applied") or ""),
                "blocked_capabilities": list((result.get("metadata") or {}).get("blocked_capabilities") or []),
                "unlock_fallback_offline": bool((result.get("metadata") or {}).get("unlock_fallback_offline")),
            },
        )
        _run_async_send(self.bus, outbound)
        _comm_trace(
            "chat_reply_sent",
            message_id=message.message_id,
            session_id=session_id,
            channel_id=ctx.channel_id,
            elapsed_ms=int((time.perf_counter() - t0) * 1000),
            reply_len=len(reply_text),
        )


def _run_async_send(bus: MessageBus, msg: OutboundMessage) -> None:
    import asyncio

    try:
        asyncio.run(bus.send_outbound(msg))
    except RuntimeError:
        # already in a running loop
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(bus.send_outbound(msg))
        except Exception:
            pass


_runtime_singleton: Optional[CommunicationRuntime] = None
_runtime_lock = threading.RLock()


def get_communication_runtime() -> CommunicationRuntime:
    global _runtime_singleton
    with _runtime_lock:
        if _runtime_singleton is None:
            _runtime_singleton = CommunicationRuntime()
        return _runtime_singleton
