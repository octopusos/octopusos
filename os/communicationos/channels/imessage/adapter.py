"""iMessage bridge adapter.

This adapter expects a bridge service that can:
- POST inbound message events to OctopusOS webhook: /api/channels/imessage/webhook
- Accept outbound message requests from OctopusOS
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import threading
import time
from typing import Any, Dict, Optional, Tuple
from urllib import request

from octopusos.communicationos.models import InboundMessage, MessageType, OutboundMessage
from octopusos.core.time import utc_now

logger = logging.getLogger(__name__)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _sanitize_outbound_text(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return raw
    action_pattern = re.compile(r"/\{action:\s*.*?\}/", re.IGNORECASE | re.DOTALL)
    sanitized = action_pattern.sub("", raw)
    blocked_markers = ("declare externalinfoneed", "externalinfoneed", "{action:", "stop 和 declare", "stop and declare")
    kept_lines: list[str] = []
    for line in sanitized.splitlines():
        low = line.lower()
        if any(marker in low for marker in blocked_markers):
            continue
        kept_lines.append(line)
    sanitized = "\n".join(kept_lines).strip()
    if sanitized != raw:
        logger.warning("sanitized_internal_control_text_for_imessage")
    return sanitized or "（已省略内部系统控制信息）"


class IMessageAdapter:
    def __init__(
        self,
        *,
        channel_id: str,
        bridge_base_url: str,
        webhook_token: Optional[str] = None,
        send_path: str = "/api/imessage/send",
        assistant_display_name: str = "OctopusOS",
        allow_from_me_inbound: bool = True,
        message_bus: Any = None,
    ):
        self.channel_id = channel_id
        self.bridge_base_url = bridge_base_url.rstrip("/")
        self.webhook_token = (webhook_token or "").strip()
        self.send_path = send_path if str(send_path or "").startswith("/") else f"/{send_path}"
        self.assistant_display_name = str(assistant_display_name or "").strip()
        self.allow_from_me_inbound = bool(allow_from_me_inbound)
        self.message_bus = message_bus

        self._state = "stopped"
        self._detail = ""
        self._last_event_ts_ms = _now_ms()

    def get_channel_id(self) -> str:
        return self.channel_id

    def start(self) -> None:
        self._state = "ready"
        self._detail = ""
        self._last_event_ts_ms = _now_ms()

    def stop(self) -> None:
        self._state = "stopped"
        self._detail = ""
        self._last_event_ts_ms = _now_ms()

    def get_status(self) -> Dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "state": self._state,
            "detail": self._detail,
            "last_event_ts_ms": self._last_event_ts_ms,
        }

    def _verify_webhook_token(self, headers: Dict[str, str], payload: Dict[str, Any]) -> None:
        if not self.webhook_token:
            return
        header_token = str(headers.get("x-imessage-token") or "").strip()
        if not header_token:
            auth = str(headers.get("authorization") or "").strip()
            if auth.lower().startswith("bearer "):
                header_token = auth[7:].strip()
        body_token = str(payload.get("webhook_token") or "").strip()
        actual = header_token or body_token
        if actual != self.webhook_token:
            raise PermissionError("webhook_token_mismatch")

    def _normalize_inbound(self, payload: Dict[str, Any]) -> Optional[InboundMessage]:
        # Common bridge challenge flow support.
        if payload.get("type") == "challenge" and payload.get("challenge"):
            return None

        if str(payload.get("direction") or "").strip().lower() == "outbound":
            return None
        if (bool(payload.get("is_from_me")) or bool(payload.get("from_me"))) and not self.allow_from_me_inbound:
            return None

        raw_message_id = str(payload.get("message_id") or payload.get("id") or f"imsg_{_now_ms()}").strip()
        semantic_dedupe_key = str(payload.get("semantic_dedupe_key") or "").strip()
        message_id = semantic_dedupe_key or raw_message_id
        text = str(payload.get("text") or payload.get("body") or payload.get("message") or "").strip()
        if not text:
            return None

        conversation_key = str(
            payload.get("conversation_key")
            or payload.get("conversation_id")
            or payload.get("chat_id")
            or payload.get("thread_id")
            or payload.get("from")
            or payload.get("sender")
            or ""
        ).strip()
        user_key = str(
            payload.get("user_key")
            or payload.get("sender")
            or payload.get("sender_id")
            or payload.get("from")
            or conversation_key
        ).strip()
        if not conversation_key:
            conversation_key = user_key
        if not user_key:
            user_key = conversation_key
        if not conversation_key or not user_key:
            return None

        return InboundMessage(
            channel_id=self.channel_id,
            user_key=user_key,
            conversation_key=conversation_key,
            message_id=message_id,
            timestamp=utc_now(),
            type=MessageType.TEXT,
            text=text,
            raw=payload,
            metadata={
                "platform": "imessage",
                "imessage_message_id": message_id,
                "imessage_raw_message_id": raw_message_id,
                "imessage_conversation_key": conversation_key,
            },
        )

    def handle_webhook(self, *, headers: Dict[str, str], body_bytes: bytes) -> Tuple[int, Dict[str, Any]]:
        try:
            payload = json.loads(body_bytes.decode("utf-8") or "{}")
        except Exception as exc:
            raise ValueError(f"invalid_json:{exc}") from exc
        if not isinstance(payload, dict):
            return 200, {"ok": True}

        self._verify_webhook_token(headers, payload)
        self._last_event_ts_ms = _now_ms()

        if payload.get("type") == "challenge" and payload.get("challenge"):
            return 200, {"ok": True, "challenge": payload.get("challenge")}

        inbound = self._normalize_inbound(payload)
        if not inbound or not self.message_bus:
            return 200, {"ok": True}

        try:
            loop = asyncio.get_running_loop()
            loop.call_soon_threadsafe(lambda: asyncio.create_task(self.message_bus.process_inbound(inbound)))
        except RuntimeError:
            threading.Thread(
                target=lambda: asyncio.run(self.message_bus.process_inbound(inbound)),
                daemon=True,
                name="imessage-inbound-fallback",
            ).start()
        return 200, {"ok": True}

    def send_message(self, message: OutboundMessage) -> bool:
        if not self.bridge_base_url:
            raise ValueError("bridge_base_url_required")
        md = message.metadata or {}
        text = _sanitize_outbound_text(str(message.text or ""))
        if not text:
            return False
        if str(md.get("policy_applied") or "").strip() == "LOW_LATENCY_EXPLICIT_WEB_UNLOCK":
            text = f"ℹ️ 本条消息已临时启用联网搜索（仅本条有效）\n{text}"
        if self.assistant_display_name:
            text = f"[{self.assistant_display_name}] {text}"

        target = str(message.conversation_key or "").strip() or str(message.user_key or "").strip()
        if not target:
            raise ValueError("missing_target")

        url = f"{self.bridge_base_url}{self.send_path}"
        payload = {
            "to": target,
            "text": text,
            "channel_id": self.channel_id,
            "session_id": str((message.metadata or {}).get("session_id") or ""),
            "user_key": str(message.user_key or ""),
            "conversation_key": str(message.conversation_key or ""),
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.webhook_token:
            headers["X-iMessage-Token"] = self.webhook_token

        req = request.Request(url=url, data=body, headers=headers, method="POST")
        with request.urlopen(req, timeout=20) as resp:
            code = int(resp.getcode() or 0)
            if code not in (200, 201, 202):
                logger.warning("iMessage bridge send got unexpected status: %s", code)
            return code in (200, 201, 202)
