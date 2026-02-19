"""Feishu/Lark enterprise IM adapter (bridge-only).

Inbound events are delivered via a FastAPI webhook in WebUI layer.
That webhook calls `handle_webhook()` here to:
- verify signature/token
- decrypt if needed
- map to InboundMessage and enqueue into MessageBus

Outbound messages are sent via Feishu OpenAPI.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from octopusos.communicationos.channels.feishu.client import FeishuClient
from octopusos.communicationos.channels.feishu.crypto import decrypt_event_payload, maybe_verify_signature
from octopusos.communicationos.models import InboundMessage, MessageType, OutboundMessage
from octopusos.core.time import utc_now

logger = logging.getLogger(__name__)


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass
class FeishuStatus:
    state: str = "stopped"
    detail: str = ""
    last_event_ts_ms: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel_id": "feishu",
            "state": self.state,
            "detail": self.detail,
            "last_event_ts_ms": self.last_event_ts_ms,
        }


class FeishuAdapter:
    def __init__(
        self,
        *,
        channel_id: str,
        app_id: str,
        app_secret: str,
        verification_token: str,
        encrypt_key: Optional[str] = None,
        message_bus: Any = None,
    ):
        self._channel_id = channel_id
        self._client = FeishuClient(app_id=app_id, app_secret=app_secret)
        self._verification_token = verification_token
        self._encrypt_key = encrypt_key or ""
        self.message_bus = message_bus
        self._status = FeishuStatus(state="ready", detail="")

    def get_channel_id(self) -> str:
        return self._channel_id

    def start(self) -> None:
        self._status.state = "ready"

    def stop(self) -> None:
        self._status.state = "stopped"

    def get_status(self) -> Dict[str, Any]:
        return self._status.to_dict()

    def send_message(self, message: OutboundMessage) -> bool:
        # conversation_key carries Feishu chat_id (for 1:1 or group chat)
        chat_id = str(message.conversation_key or "").strip()
        if not chat_id:
            raise ValueError("missing_chat_id")
        text = str(message.text or "").strip()
        if not text:
            return True
        self._client.send_text_to_chat(chat_id=chat_id, text=text)
        return True

    def _verify_token(self, token: Optional[str]) -> None:
        if not token or token != self._verification_token:
            raise PermissionError("verification_token_mismatch")

    def _parse_body(self, *, headers: Dict[str, str], body_bytes: bytes) -> Dict[str, Any]:
        # Signature verify (best-effort).
        # If signature headers present but verification fails -> reject.
        signature = headers.get("x-lark-signature") or headers.get("x-feishu-signature")
        ts = headers.get("x-lark-request-timestamp") or headers.get("x-feishu-request-timestamp")
        nonce = headers.get("x-lark-request-nonce") or headers.get("x-feishu-request-nonce")
        if not maybe_verify_signature(
            encrypt_key=self._encrypt_key or None,
            timestamp=ts,
            nonce=nonce,
            signature_hex=signature,
            body_bytes=body_bytes,
        ):
            raise PermissionError("signature_invalid")

        raw = json.loads(body_bytes.decode("utf-8") or "{}")
        if isinstance(raw, dict) and "encrypt" in raw and raw.get("encrypt"):
            if not self._encrypt_key:
                raise PermissionError("encrypt_key_required")
            plain = decrypt_event_payload(encrypt_key=self._encrypt_key, encrypt_b64=str(raw["encrypt"]))
            return json.loads(plain)
        return raw if isinstance(raw, dict) else {}

    def handle_webhook(
        self,
        *,
        headers: Dict[str, str],
        body_bytes: bytes,
    ) -> Tuple[int, Dict[str, Any]]:
        """Handle webhook HTTP request.

        Returns: (http_status, response_json)
        """
        payload = self._parse_body(headers=headers, body_bytes=body_bytes)

        # URL verification challenge
        if payload.get("type") == "url_verification":
            self._verify_token(payload.get("token"))
            return 200, {"challenge": payload.get("challenge")}

        # Event callback
        if payload.get("type") == "event_callback":
            self._verify_token(payload.get("token"))
            event = payload.get("event") if isinstance(payload.get("event"), dict) else {}
            header = payload.get("header") if isinstance(payload.get("header"), dict) else {}

            event_type = str(header.get("event_type") or "")
            if event_type == "im.message.receive_v1":
                self._handle_im_message_receive(event=event, header=header)
            else:
                logger.debug("feishu unhandled event_type=%s", event_type)
            return 200, {"ok": True}

        # Unknown payload
        return 200, {"ok": True}

    def _handle_im_message_receive(self, *, event: Dict[str, Any], header: Dict[str, Any]) -> None:
        if not self.message_bus:
            return

        message = event.get("message") if isinstance(event.get("message"), dict) else {}
        sender = event.get("sender") if isinstance(event.get("sender"), dict) else {}
        sender_id = sender.get("sender_id") if isinstance(sender.get("sender_id"), dict) else {}

        chat_id = str(message.get("chat_id") or "").strip()
        msg_id = str(message.get("message_id") or "").strip()
        msg_type = str(message.get("message_type") or "").strip()
        content_raw = str(message.get("content") or "")

        # Only text for M1.
        if msg_type != "text":
            return
        try:
            content_obj = json.loads(content_raw) if content_raw else {}
        except Exception:
            content_obj = {}
        text = str(content_obj.get("text") or "").strip()
        if not chat_id or not msg_id or not text:
            return

        user_key = str(sender_id.get("open_id") or sender_id.get("user_id") or "").strip() or chat_id

        inbound = InboundMessage(
            channel_id=self._channel_id,
            user_key=user_key,
            conversation_key=chat_id,
            message_id=msg_id,
            timestamp=utc_now(),
            type=MessageType.TEXT,
            text=text,
            raw={"header": header, "event": {"message": {"message_id": msg_id, "chat_id": chat_id, "message_type": msg_type}}},
            metadata={
                "platform": "feishu",
                "event_type": "im.message.receive_v1",
                "feishu_message_id": msg_id,
                "feishu_chat_id": chat_id,
                "content_hash": _sha256_hex(text),
                "content_len": len(text),
            },
        )

        # Non-blocking: enqueue into async pipeline.
        try:
            loop = asyncio.get_running_loop()
            loop.call_soon_threadsafe(lambda: asyncio.create_task(self.message_bus.process_inbound(inbound)))
        except RuntimeError:
            # No running loop; fall back to direct run.
            asyncio.run(self.message_bus.process_inbound(inbound))

