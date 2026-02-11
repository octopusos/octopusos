"""Volc Realtime Dialogue websocket client."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Optional

import websockets
from octopusos.webui.config_resolver import resolve_config
from octopusos.webui.secret_resolver import resolve_secret_ref

from .frames import decode_frame, encode_audio_frame, encode_json_event

VOLC_WS_URL = "wss://openspeech.bytedance.com/api/v3/realtime/dialogue"


@dataclass
class VolcConfig:
    app_id: str
    access_key: str
    app_key: str
    resource_id: str = "volc.speech.dialog"
    model: str = "O"
    speaker: str = "zh_female_vv_jupiter_bigtts"
    keep_alive: bool = True


class VolcConfigError(ValueError):
    pass


def load_volc_config() -> VolcConfig:
    def _resolve_with_fallback(primary_key: str, fallback_key: str) -> str:
        primary = resolve_config(key=primary_key)
        primary_value = str(primary.get("value") or "").strip()
        if primary.get("source") != "default" and primary_value:
            return primary_value
        fallback = resolve_config(key=fallback_key)
        return str(fallback.get("value") or "").strip()

    access_ref = _resolve_with_fallback("providers.volc.access_key_ref", "calls.volc.access_key_ref")
    secret_ref = _resolve_with_fallback("providers.volc.app_key_ref", "calls.volc.secret_key_ref")
    app_id = str(resolve_config(key="providers.volc.app_id").get("value") or "").strip()
    resource_id = str(resolve_config(key="providers.volc.resource_id").get("value") or "volc.speech.dialog").strip() or "volc.speech.dialog"
    model = str(resolve_config(key="providers.volc.model").get("value") or "O").strip() or "O"
    speaker = str(resolve_config(key="providers.volc.tts_speaker").get("value") or "zh_female_vv_jupiter_bigtts").strip() or "zh_female_vv_jupiter_bigtts"
    keep_alive_raw = str(resolve_config(key="providers.volc.keep_alive").get("value") or "true").strip().lower()

    access_key = resolve_secret_ref(access_ref) or ""
    app_key = resolve_secret_ref(secret_ref) or ""
    return VolcConfig(
        app_id=app_id,
        access_key=access_key,
        app_key=app_key,
        resource_id=resource_id,
        model=model,
        speaker=speaker,
        keep_alive=keep_alive_raw in {"1", "true", "yes", "on"},
    )


class VolcRealtimeClient:
    def __init__(self, session_id: str, connect_id: Optional[str] = None, config: Optional[VolcConfig] = None) -> None:
        self.session_id = session_id
        self.connect_id = connect_id or str(uuid.uuid4())
        self.config = config or load_volc_config()
        self.ws: Optional[Any] = None
        self.sequence = 0

    def _next_seq(self) -> int:
        self.sequence += 1
        return self.sequence

    def _headers(self) -> Dict[str, str]:
        return {
            "X-Api-App-ID": self.config.app_id,
            "X-Api-Access-Key": self.config.access_key,
            "X-Api-Resource-Id": self.config.resource_id,
            "X-Api-App-Key": self.config.app_key,
            "X-Api-Connect-Id": self.connect_id,
        }

    def assert_enabled(self) -> None:
        if not self.config.app_id or not self.config.access_key or not self.config.app_key:
            raise VolcConfigError("VOLC_API_APP_ID/VOLC_API_ACCESS_KEY/VOLC_API_APP_KEY are required")

    async def connect(self) -> str:
        if self.ws is not None:
            return ""
        self.assert_enabled()
        self.ws = await websockets.connect(VOLC_WS_URL, additional_headers=self._headers())
        headers = getattr(self.ws, "response_headers", None)
        if headers is None:
            return ""
        try:
            return str(headers.get("X-Tt-Logid", ""))
        except Exception:
            return ""

    async def close(self) -> None:
        if self.ws is None:
            return
        await self.ws.close()
        self.ws = None

    async def start_connection(self) -> None:
        await self._send_json_event(1, {"connect": {"hello": "octopusos"}})

    async def finish_connection(self) -> None:
        await self._send_json_event(2, {"connect": {"bye": "octopusos"}})

    async def start_session(self) -> None:
        payload = {
            "dialog": {
                "extra": {
                    "model": self.config.model,
                    "input_mod": "keep_alive" if self.config.keep_alive else "audio_only",
                }
            },
            "tts": {
                "audio_config": {
                    "format": "pcm_s16le",
                    "sample_rate": 24000,
                    "channel": 1,
                },
                "speaker": self.config.speaker,
            },
        }
        await self._send_json_event(100, payload)

    async def finish_session(self) -> None:
        await self._send_json_event(102, {"session": {"finish": True}})

    async def send_audio(self, pcm_bytes: bytes) -> None:
        if self.ws is None:
            raise RuntimeError("Volc websocket not connected")
        frame = encode_audio_frame(
            session_id=self.session_id,
            connect_id=self.connect_id,
            sequence=self._next_seq(),
            pcm_bytes=pcm_bytes,
        )
        await self.ws.send(frame)

    async def recv_loop(self, on_event: Callable[[dict], Awaitable[None]]) -> None:
        if self.ws is None:
            raise RuntimeError("Volc websocket not connected")

        async for message in self.ws:
            if not isinstance(message, (bytes, bytearray)):
                continue
            decoded = decode_frame(bytes(message))
            await on_event(
                {
                    "event_id": decoded.event_id,
                    "session_id": decoded.session_id,
                    "connect_id": decoded.connect_id,
                    "sequence": decoded.sequence,
                    "payload_json": decoded.payload_json,
                    "payload_bytes": decoded.payload_bytes,
                    "msg_type": decoded.msg_type,
                }
            )

    async def _send_json_event(self, event_id: int, payload: dict) -> None:
        if self.ws is None:
            raise RuntimeError("Volc websocket not connected")
        frame = encode_json_event(
            event_id=event_id,
            session_id=self.session_id,
            connect_id=self.connect_id,
            sequence=self._next_seq(),
            payload_dict=payload,
        )
        await self.ws.send(frame)
