"""Generic bridge-based IM adapter.

Reusable for channels that integrate through an external bridge service:
- inbound webhooks -> CommunicationOS inbound pipeline
- outbound send API -> bridge endpoint
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from typing import Any, Dict, Optional, Tuple
from urllib import request

from octopusos.communicationos.models import InboundMessage, MessageType, OutboundMessage
from octopusos.core.time import utc_now

logger = logging.getLogger(__name__)


def _now_ms() -> int:
    return int(time.time() * 1000)


class GenericBridgeIMAdapter:
    def __init__(
        self,
        *,
        channel_id: str,
        platform: str,
        bridge_base_url: str,
        webhook_token: Optional[str] = None,
        send_path: str = "/api/bridge/send",
        message_bus: Any = None,
    ):
        self.channel_id = channel_id
        self.platform = platform
        self.bridge_base_url = bridge_base_url.rstrip("/")
        self.webhook_token = (webhook_token or "").strip()
        self.send_path = send_path if str(send_path or "").startswith("/") else f"/{send_path}"
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
            "platform": self.platform,
            "state": self._state,
            "detail": self._detail,
            "last_event_ts_ms": self._last_event_ts_ms,
        }

    def _verify_webhook_token(self, headers: Dict[str, str], payload: Dict[str, Any]) -> None:
        if not self.webhook_token:
            return
        header_token = str(headers.get("x-bridge-token") or "").strip()
        if not header_token:
            auth = str(headers.get("authorization") or "").strip()
            if auth.lower().startswith("bearer "):
                header_token = auth[7:].strip()
        body_token = str(payload.get("webhook_token") or "").strip()
        actual = header_token or body_token
        if actual != self.webhook_token:
            raise PermissionError("webhook_token_mismatch")

    def _normalize_inbound(self, payload: Dict[str, Any]) -> Optional[InboundMessage]:
        if payload.get("type") == "challenge" and payload.get("challenge"):
            return None

        if str(payload.get("direction") or "").strip().lower() == "outbound":
            return None
        if bool(payload.get("is_from_me")) or bool(payload.get("from_me")):
            return None

        message_id = str(payload.get("message_id") or payload.get("id") or f"bridge_{_now_ms()}").strip()
        text = str(payload.get("text") or payload.get("body") or payload.get("message") or "").strip()
        if not text:
            return None

        conversation_key = str(
            payload.get("conversation_key")
            or payload.get("conversation_id")
            or payload.get("chat_id")
            or payload.get("thread_id")
            or payload.get("room_id")
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
                "platform": self.platform,
                "bridge_message_id": message_id,
                "bridge_conversation_key": conversation_key,
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
                name=f"{self.channel_id}-bridge-inbound-fallback",
            ).start()
        return 200, {"ok": True}

    def send_message(self, message: OutboundMessage) -> bool:
        if not self.bridge_base_url:
            raise ValueError("bridge_base_url_required")
        text = str(message.text or "").strip()
        if not text:
            return False

        target = str(message.conversation_key or "").strip() or str(message.user_key or "").strip()
        if not target:
            raise ValueError("missing_target")

        url = f"{self.bridge_base_url}{self.send_path}"
        payload = {
            "to": target,
            "text": text,
            "channel_id": self.channel_id,
            "platform": self.platform,
            "session_id": str((message.metadata or {}).get("session_id") or ""),
            "user_key": str(message.user_key or ""),
            "conversation_key": str(message.conversation_key or ""),
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.webhook_token:
            headers["X-Bridge-Token"] = self.webhook_token

        req = request.Request(url=url, data=body, headers=headers, method="POST")
        with request.urlopen(req, timeout=20) as resp:
            code = int(resp.getcode() or 0)
            if code not in (200, 201, 202):
                logger.warning("%s bridge send got unexpected status: %s", self.channel_id, code)
            return code in (200, 201, 202)
