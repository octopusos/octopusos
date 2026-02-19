"""WhatsApp Web (Local QR) Channel Adapter.

This adapter integrates WhatsApp Web login via a local Node bridge (whatsapp-web.js).

Design goals:
- Local-only QR login (scan to connect)
- Persist auth state on disk so reconnect does not require re-scan
- Unified InboundMessage / OutboundMessage flow via MessageBus
- No plaintext message content in audit logs (AuditMiddleware already enforces this)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import queue
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from octopusos.communicationos.models import InboundMessage, OutboundMessage, MessageType
from octopusos.core.storage.paths import store_root
from octopusos.core.time import utc_now

logger = logging.getLogger(__name__)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _secure_mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        try:
            os.chmod(path, 0o700)
        except Exception:
            pass


def _guess_state_dir(channel_id: str) -> Path:
    # Keep it under ~/.octopusos/store/communicationos/whatsapp_web/<channel_id>
    base = store_root() / "communicationos" / "whatsapp_web" / channel_id
    _secure_mkdir(base)
    return base


def _guess_chrome_path(explicit: str | None) -> str:
    raw = (explicit or "").strip()
    if raw:
        return raw
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    return ""


def _wa_user_key_from_chat_id(chat_id: str) -> str:
    v = (chat_id or "").strip()
    if v.endswith("@c.us"):
        digits = v.split("@", 1)[0]
        if digits.isdigit():
            return f"+{digits}"
    return v


@dataclass
class WhatsAppWebStatus:
    state: str
    detail: str = ""
    last_event_ts_ms: int = 0


class WhatsAppWebAdapter:
    """Channel adapter for WhatsApp via WhatsApp Web (local QR login)."""

    def __init__(
        self,
        channel_id: str,
        *,
        state_dir: Optional[str] = None,
        chrome_path: Optional[str] = None,
        allow_from_me_inbound: bool = False,
        message_bus: Optional[Any] = None,
    ):
        self.channel_id = channel_id
        self.message_bus = message_bus

        self._state_dir = Path(state_dir).expanduser() if state_dir else _guess_state_dir(channel_id)
        _secure_mkdir(self._state_dir)
        self._chrome_path = _guess_chrome_path(chrome_path)
        self._allow_from_me_inbound = bool(allow_from_me_inbound)

        self._proc: Optional[subprocess.Popen[str]] = None
        self._stdout_thread: Optional[threading.Thread] = None
        self._stderr_thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

        self._latest_qr: Optional[Dict[str, Any]] = None
        self._status = WhatsAppWebStatus(state="stopped", last_event_ts_ms=_now_ms())

        self._send_results: "queue.Queue[Dict[str, Any]]" = queue.Queue()

    def get_channel_id(self) -> str:
        return self.channel_id

    def start(self) -> None:
        if self._proc and self._proc.poll() is None:
            return

        bridge = Path(__file__).parent / "whatsapp_web" / "node" / "whatsapp_web_bridge.mjs"
        if not bridge.exists():
            raise FileNotFoundError(f"Missing Node bridge: {bridge}")

        env = os.environ.copy()
        env["OCTOPUSOS_WHATSAPP_STATE_DIR"] = str(self._state_dir)
        if self._chrome_path:
            env["OCTOPUSOS_WHATSAPP_CHROME_PATH"] = self._chrome_path

        # Use line-buffered text pipes for JSONL exchange.
        self._proc = subprocess.Popen(
            ["node", str(bridge)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
        )
        self._stop.clear()
        self._status = WhatsAppWebStatus(state="starting", last_event_ts_ms=_now_ms())

        self._stdout_thread = threading.Thread(target=self._stdout_loop, daemon=True, name="whatsapp-web-stdout")
        self._stderr_thread = threading.Thread(target=self._stderr_loop, daemon=True, name="whatsapp-web-stderr")
        self._stdout_thread.start()
        self._stderr_thread.start()

    def stop(self) -> None:
        self._stop.set()
        proc = self._proc
        self._proc = None
        if not proc:
            self._status = WhatsAppWebStatus(state="stopped", last_event_ts_ms=_now_ms())
            return
        try:
            self._write_cmd({"cmd": "shutdown"})
        except Exception:
            pass
        try:
            proc.terminate()
        except Exception:
            pass
        self._status = WhatsAppWebStatus(state="stopped", last_event_ts_ms=_now_ms())

    def get_status(self) -> Dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "state": self._status.state,
            "detail": self._status.detail,
            "last_event_ts_ms": self._status.last_event_ts_ms,
            "has_qr": bool(self._latest_qr),
        }

    def get_qr(self) -> Optional[Dict[str, Any]]:
        return self._latest_qr

    def _write_cmd(self, obj: Dict[str, Any]) -> None:
        proc = self._proc
        if not proc or proc.stdin is None:
            raise RuntimeError("bridge_not_running")
        proc.stdin.write(json.dumps(obj) + "\n")
        proc.stdin.flush()

    def send_message(self, message: OutboundMessage) -> bool:
        # OutboundMessage.conversation_key is expected to be the WhatsApp chat id (e.g., 123@c.us)
        to = (message.conversation_key or "").strip()
        if not to:
            # Fallback: try derive from user_key
            user = (message.user_key or "").strip().lstrip("+")
            if user.isdigit():
                to = f"{user}@c.us"
        if not to:
            raise ValueError("missing_conversation_key")

        text = message.text or ""
        if not text:
            return False

        self.start()
        self._write_cmd({"cmd": "send", "to": to, "text": text})

        # Best-effort: wait briefly for send_result.
        try:
            result = self._send_results.get(timeout=10.0)
            return bool(result.get("ok"))
        except queue.Empty:
            # Bridge may still have sent it; treat as soft-failure.
            return False

    def _stderr_loop(self) -> None:
        proc = self._proc
        if not proc or proc.stderr is None:
            return
        for line in proc.stderr:
            if self._stop.is_set():
                break
            raw = (line or "").strip()
            if raw:
                logger.info("whatsapp_web bridge stderr: %s", raw[:500])

    def _stdout_loop(self) -> None:
        proc = self._proc
        if not proc or proc.stdout is None:
            return
        for line in proc.stdout:
            if self._stop.is_set():
                break
            raw = (line or "").strip()
            if not raw:
                continue
            try:
                evt = json.loads(raw)
            except Exception:
                logger.info("whatsapp_web bridge non-json line: %s", raw[:500])
                continue
            try:
                self._handle_event(evt)
            except Exception:
                logger.exception("Failed handling whatsapp_web event")

    def _handle_event(self, evt: Dict[str, Any]) -> None:
        et = str(evt.get("type") or "")
        ts = int(evt.get("ts_ms") or _now_ms())

        if et in {"status", "ready"}:
            state = str(evt.get("state") or ("ready" if et == "ready" else ""))
            if et == "ready":
                state = "ready"
            if state in {"ready", "authenticated"}:
                self._latest_qr = None
            self._status = WhatsAppWebStatus(
                state=state or self._status.state,
                detail=str(evt.get("detail") or ""),
                last_event_ts_ms=ts,
            )
            return

        if et == "qr":
            self._latest_qr = {
                "qr": evt.get("qr"),
                "qr_data_url": evt.get("qr_data_url"),
                "ts_ms": ts,
            }
            self._status = WhatsAppWebStatus(state="needs_qr", detail="", last_event_ts_ms=ts)
            return

        if et == "send_result":
            self._send_results.put(evt)
            return

        if et == "inbound_message":
            if not self.message_bus:
                return
            is_from_me = bool(evt.get("from_me"))
            if is_from_me and not self._allow_from_me_inbound:
                return
            chat_id = str(evt.get("from") or "").strip()
            if not chat_id:
                return
            user_key = _wa_user_key_from_chat_id(chat_id)
            msg_id = str(evt.get("message_id") or f"wa_{ts}")
            body = str(evt.get("body") or "").strip()
            if not body:
                return

            inbound = InboundMessage(
                channel_id=self.channel_id,
                user_key=user_key,
                conversation_key=chat_id,  # keep raw chat id for replies
                message_id=msg_id,
                timestamp=utc_now(),
                type=MessageType.TEXT,
                text=body,
                raw=evt,
                metadata={
                    "wa_chat_id": chat_id,
                    "wa_is_group": bool(evt.get("is_group")),
                    "wa_from_me": is_from_me,
                },
            )

            # Run through async middleware pipeline without blocking bridge reader thread.
            try:
                loop = asyncio.get_running_loop()
                loop.call_soon_threadsafe(lambda: asyncio.create_task(self.message_bus.process_inbound(inbound)))
            except RuntimeError:
                # No running loop; fall back to a background thread.
                threading.Thread(
                    target=lambda: asyncio.run(self.message_bus.process_inbound(inbound)),
                    daemon=True,
                    name="whatsapp-web-inbound-fallback",
                ).start()
            return

        logger.debug("Unhandled whatsapp_web event type: %s", et)
