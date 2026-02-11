"""Call sessions, call events, transcripts, voice contacts, and call WebSocket."""

from __future__ import annotations

import asyncio
import base64
import contextlib
import hashlib
import json
import math
import os
import struct
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from octopusos.webui.calls import IdempotencyConflictError, get_call_store
from octopusos.webui.calls.voice_pipeline import get_audio_formats, synthesize_samples, transcribe_samples
from octopusos.webui.calls.providers.volc import VolcConfigError, VolcRealtimeClient, extract_error, extract_text, is_final_asr
from octopusos.webui.config_resolver import resolve_config
from octopusos.webui.api.compat_state import db_connect, get_state
from octopusos.core.capabilities.admin_token import validate_admin_token
from octopusos.core.task.service import TaskService

router = APIRouter(tags=["calls"])
PROTOCOL_VERSION = 1
IN_AUDIO_FORMAT, OUT_AUDIO_FORMAT = get_audio_formats()
CALL_CAPABILITIES = {
    "audio_input": True,
    "audio_output": True,
    "transcript": "partial+final",
    "codec_in": [IN_AUDIO_FORMAT.codec],
    "codec_out": [OUT_AUDIO_FORMAT.codec],
    "audio_format_in": IN_AUDIO_FORMAT.to_dict(),
    "audio_format_out": OUT_AUDIO_FORMAT.to_dict(),
}


def _provider_hint_for_session(session: Dict[str, Any]) -> str:
    provider_id = str(session.get("provider_id") or "").strip().lower()
    runtime = str(session.get("runtime") or "").strip().lower()
    if runtime == "cloud" and provider_id in {"volc", "doubao", "bytedance"}:
        return "volc"
    if runtime == "cloud" and provider_id in {"openai"}:
        return provider_id
    if provider_id:
        return provider_id
    return "unconfigured"


def _capabilities_for_provider(provider_hint: str) -> Dict[str, Any]:
    if provider_hint == "volc":
        return {
            "audio_input": True,
            "audio_output": True,
            "barge_in": True,
            "transcript": "partial+final",
            "codec_in": ["pcm_s16le"],
            "codec_out": ["pcm_s16le"],
            "audio_format_in": {
                "codec": "pcm_s16le",
                "sample_rate_hz": 16000,
                "channels": 1,
                "frame_ms": 20,
            },
            "audio_format_out": {
                "codec": "pcm_s16le",
                "sample_rate_hz": 24000,
                "channels": 1,
                "frame_ms": 20,
            },
        }
    return CALL_CAPABILITIES


def _float_samples_to_pcm16(samples: List[float]) -> bytes:
    payload = bytearray()
    for sample in samples:
        value = max(-1.0, min(1.0, float(sample)))
        payload.extend(struct.pack("<h", int(value * 32767.0)))
    return bytes(payload)


def _pcm16_to_float_samples(pcm: bytes) -> List[float]:
    if not pcm:
        return []
    sample_count = len(pcm) // 2
    ints = struct.unpack("<" + ("h" * sample_count), pcm[: sample_count * 2])
    return [max(-1.0, min(1.0, value / 32768.0)) for value in ints]


def _ws_url_from_request(request: Request, call_session_id: str) -> str:
    scheme = "wss" if request.url.scheme == "https" else "ws"
    host = request.headers.get("host") or request.url.netloc
    return f"{scheme}://{host}/ws/calls/{call_session_id}"


def _normalize_runtime(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    runtime = value.strip().lower()
    if runtime not in {"local", "cloud"}:
        return None
    return runtime


def _mock_audio_samples(sample_rate: int = 24000, seconds: float = 0.18) -> List[float]:
    total = int(sample_rate * seconds)
    hz = 440.0
    return [0.15 * math.sin(2 * math.pi * hz * (i / sample_rate)) for i in range(total)]


def _request_hash(payload: Dict[str, Any]) -> str:
    stable_payload = {
        "runtime": payload.get("runtime"),
        "provider_id": payload.get("provider_id"),
        "model_id": payload.get("model_id"),
        "voice_profile_id": payload.get("voice_profile_id"),
    }
    canonical = json.dumps(stable_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _idempotency_ttl_seconds() -> int:
    raw = str(os.environ.get("OCTOPUSOS_CALLS_IDEMPOTENCY_TTL_SECONDS", "600")).strip()
    try:
        value = int(raw)
    except ValueError:
        value = 600
    return max(value, 1)


def _vad_threshold() -> float:
    raw = os.getenv("OCTOPUSOS_CALLS_VAD_THRESHOLD", "0.02").strip()
    try:
        value = float(raw)
    except ValueError:
        value = 0.02
    return max(value, 0.0)


def _chunk_samples(samples: List[float], frame_samples: int) -> List[List[float]]:
    size = max(frame_samples, 1)
    return [samples[i:i + size] for i in range(0, len(samples), size)]


def _speech_energy(samples: List[float]) -> float:
    if not samples:
        return 0.0
    total = 0.0
    for sample in samples:
        total += abs(sample)
    return total / len(samples)


def _should_auto_create_task() -> bool:
    return os.getenv("OCTOPUSOS_CALLS_CREATE_TASK", "1").strip().lower() in {"1", "true", "yes", "on"}


def _maybe_create_call_task(
    *,
    call_session_id: str,
    runtime: str,
    provider_id: Optional[str],
    model_id: Optional[str],
) -> Optional[str]:
    if not _should_auto_create_task():
        return None
    try:
        title = f"Call {call_session_id}: {runtime}/{provider_id or 'n/a'}/{model_id or 'n/a'}"
        task = TaskService().create_draft_task(
            title=title,
            session_id=call_session_id,
            created_by="calls",
            metadata={"source": "calls", "channel": "voice_call"},
        )
        return task.task_id
    except Exception:
        return None


def _create_agent_task_from_transcript(call_session_id: str, transcript: str) -> Optional[str]:
    lowered = transcript.lower().strip()
    if not (lowered.startswith("agent ") or lowered.startswith("task ")):
        return None
    title = transcript.split(" ", 1)[1].strip() if " " in transcript else ""
    if not title:
        return None
    try:
        task = TaskService().create_draft_task(
            title=title,
            session_id=call_session_id,
            created_by="calls_voice",
            metadata={"source": "voice_command"},
        )
        return task.task_id
    except Exception:
        return None


def _require_admin_token(token: Optional[str]) -> bool:
    if not token:
        return False
    return validate_admin_token(token)


def _resolve_str(key: str, default: str) -> str:
    resolved = resolve_config(key=key)
    value = resolved.get("value")
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip()


def _resolve_optional_str(key: str) -> Optional[str]:
    resolved = resolve_config(key=key)
    value = resolved.get("value")
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def _resolve_bool(key: str, default: bool) -> bool:
    resolved = resolve_config(key=key)
    value = resolved.get("value")
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _is_demo_or_test_mode() -> bool:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return True
    raw = os.getenv("OCTOPUSOS_DEMO_MODE", "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    conn = None
    try:
        conn = db_connect()
        return bool(get_state(conn, key="demo_mode_enabled", default=False))
    except Exception:
        return False
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


@router.post("/api/calls/sessions")
async def create_call_session(
    request: Request,
    idempotency_header: Optional[str] = Header(default=None, alias="Idempotency-Key"),
) -> JSONResponse:
    if not _resolve_bool("calls.enabled", True):
        return JSONResponse(status_code=403, content={"error": "CALLS_DISABLED"})

    try:
        payload = await request.json()
    except Exception:
        # Empty/invalid JSON must not surface as 500.
        return JSONResponse(status_code=422, content={"detail": "Invalid JSON payload"})
    if not isinstance(payload, dict):
        return JSONResponse(status_code=422, content={"detail": "Invalid payload"})

    runtime = _normalize_runtime(payload.get("runtime"))
    if runtime is None:
        return JSONResponse(status_code=422, content={"detail": "runtime must be local or cloud"})

    provider_id = payload.get("provider_id")
    model_id = payload.get("model_id")
    voice_profile_id = payload.get("voice_profile_id")

    if provider_id is not None and not isinstance(provider_id, str):
        return JSONResponse(status_code=422, content={"detail": "provider_id must be a string"})
    if model_id is not None and not isinstance(model_id, str):
        return JSONResponse(status_code=422, content={"detail": "model_id must be a string"})
    if voice_profile_id is not None and not isinstance(voice_profile_id, str):
        return JSONResponse(status_code=422, content={"detail": "voice_profile_id must be a string"})

    if runtime == "cloud":
        if not provider_id or not model_id:
            return JSONResponse(status_code=422, content={"detail": "provider_id and model_id are required for cloud runtime"})

    if runtime == "local":
        demo_or_test = _is_demo_or_test_mode()
        provider_id = provider_id or _resolve_optional_str("calls.provider")
        if not provider_id and demo_or_test:
            provider_id = "mock"
        if provider_id == "mock" and not demo_or_test:
            return JSONResponse(
                status_code=412,
                content={
                    "error": "CALLS_PROVIDER_NOT_CONFIGURED",
                    "detail": "mock provider is only allowed in demo/test mode",
                },
            )
        if not provider_id:
            return JSONResponse(
                status_code=412,
                content={
                    "error": "CALLS_PROVIDER_NOT_CONFIGURED",
                    "detail": "calls.provider is required unless demo/test mode is enabled",
                },
            )
        model_id = model_id or "local-voice-v1"

    idempotency_from_body = payload.get("idempotency_key")
    idempotency_key: Optional[str] = None
    if isinstance(idempotency_header, str) and idempotency_header.strip():
        idempotency_key = idempotency_header.strip()
    elif isinstance(idempotency_from_body, str) and idempotency_from_body.strip():
        idempotency_key = idempotency_from_body.strip()

    if idempotency_key is not None and len(idempotency_key) > 255:
        return JSONResponse(status_code=422, content={"detail": "idempotency_key too long"})

    store = get_call_store()
    try:
        session, created = store.create_call_session(
            runtime,
            provider_id,
            model_id,
            voice_profile_id,
            idempotency_key=idempotency_key,
            request_hash=_request_hash(
                {
                    "runtime": runtime,
                    "provider_id": provider_id,
                    "model_id": model_id,
                    "voice_profile_id": voice_profile_id,
                }
            ) if idempotency_key else None,
            ttl_seconds=_idempotency_ttl_seconds(),
        )
    except IdempotencyConflictError:
        return JSONResponse(
            status_code=409,
            content={"error": "idempotency_key_reuse_with_different_payload"},
        )

    if created:
        linked_task_id = _maybe_create_call_task(
            call_session_id=session["id"],
            runtime=runtime,
            provider_id=provider_id,
            model_id=model_id,
        )
        if linked_task_id:
            store.set_call_task_link(session["id"], linked_task_id)
            store.add_call_event(session["id"], "agent.task.linked", {"task_id": linked_task_id})

    source_header = "real"
    reason_header = None
    if runtime == "local" and provider_id == "mock":
        source_header = "demo"
        reason_header = "demo_mode_mock_provider"

    response = JSONResponse(
        status_code=201 if created else 200,
        content={
            "call_session_id": session["id"],
            "ws_url": _ws_url_from_request(request, session["id"]),
            "protocol_version": PROTOCOL_VERSION,
            "idempotency_key": idempotency_key,
            "idempotency_reused": not created,
            "session": session,
        },
    )
    response.headers["X-OctopusOS-Source"] = source_header
    if reason_header:
        response.headers["X-OctopusOS-Reason"] = reason_header
    return response


@router.get("/api/calls/sessions/{call_session_id}")
async def get_call_session(call_session_id: str) -> JSONResponse:
    store = get_call_store()
    session = store.get_call_session(call_session_id)
    if session is None:
        return JSONResponse(status_code=404, content={"ok": False, "error": "Call session not found"})
    return JSONResponse(status_code=200, content={"session": session})


@router.get("/api/calls/sessions/{call_session_id}/task")
async def get_call_task(call_session_id: str) -> JSONResponse:
    store = get_call_store()
    session = store.get_call_session(call_session_id)
    if session is None:
        return JSONResponse(status_code=404, content={"ok": False, "error": "Call session not found"})
    link = store.get_call_task_link(call_session_id)
    if link is None:
        return JSONResponse(status_code=404, content={"ok": False, "error": "Task link not found"})
    return JSONResponse(status_code=200, content={"task_link": link})


@router.get("/api/calls/sessions/{call_session_id}/events")
async def list_call_events(call_session_id: str) -> JSONResponse:
    store = get_call_store()
    session = store.get_call_session(call_session_id)
    if session is None:
        return JSONResponse(status_code=404, content={"ok": False, "error": "Call session not found"})
    events = store.list_call_events(call_session_id)
    return JSONResponse(status_code=200, content={"events": events})


@router.get("/api/calls/sessions/{call_session_id}/transcripts")
async def list_call_transcripts(call_session_id: str) -> JSONResponse:
    store = get_call_store()
    session = store.get_call_session(call_session_id)
    if session is None:
        return JSONResponse(status_code=404, content={"ok": False, "error": "Call session not found"})
    transcripts = store.list_transcripts(call_session_id)
    return JSONResponse(status_code=200, content={"transcripts": transcripts})


@router.get("/api/voice-contacts")
async def list_voice_contacts() -> JSONResponse:
    store = get_call_store()
    return JSONResponse(status_code=200, content={"contacts": store.list_voice_contacts()})


@router.post("/api/voice-contacts")
async def create_voice_contact(request: Request) -> JSONResponse:
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=422, content={"detail": "Invalid JSON payload"})
    if not isinstance(payload, dict):
        return JSONResponse(status_code=422, content={"detail": "Invalid payload"})

    display_name = payload.get("display_name")
    runtime = _normalize_runtime(payload.get("runtime"))
    provider_id = payload.get("provider_id")
    model_id = payload.get("model_id")
    voice_profile_id = payload.get("voice_profile_id")
    prefs_json = payload.get("prefs_json") if isinstance(payload.get("prefs_json"), dict) else {}

    if not isinstance(display_name, str) or not display_name.strip():
        return JSONResponse(status_code=422, content={"detail": "display_name is required"})
    if runtime is None:
        return JSONResponse(status_code=422, content={"detail": "runtime must be local or cloud"})

    if runtime == "cloud" and (not provider_id or not model_id):
        return JSONResponse(status_code=422, content={"detail": "provider_id and model_id are required for cloud runtime"})

    store = get_call_store()
    contact = store.create_voice_contact(
        display_name=display_name.strip(),
        runtime=runtime,
        provider_id=provider_id if isinstance(provider_id, str) else None,
        model_id=model_id if isinstance(model_id, str) else None,
        voice_profile_id=voice_profile_id if isinstance(voice_profile_id, str) else None,
        prefs_json=prefs_json,
    )
    return JSONResponse(status_code=200, content={"contact": contact})


@router.put("/api/voice-contacts/{contact_id}")
async def update_voice_contact(contact_id: str, request: Request) -> JSONResponse:
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=422, content={"detail": "Invalid JSON payload"})
    if not isinstance(payload, dict):
        return JSONResponse(status_code=422, content={"detail": "Invalid payload"})

    display_name = payload.get("display_name")
    runtime = _normalize_runtime(payload.get("runtime"))
    provider_id = payload.get("provider_id")
    model_id = payload.get("model_id")
    voice_profile_id = payload.get("voice_profile_id")
    prefs_json = payload.get("prefs_json") if isinstance(payload.get("prefs_json"), dict) else {}

    if not isinstance(display_name, str) or not display_name.strip():
        return JSONResponse(status_code=422, content={"detail": "display_name is required"})
    if runtime is None:
        return JSONResponse(status_code=422, content={"detail": "runtime must be local or cloud"})

    if runtime == "cloud" and (not provider_id or not model_id):
        return JSONResponse(status_code=422, content={"detail": "provider_id and model_id are required for cloud runtime"})

    store = get_call_store()
    contact = store.update_voice_contact(
        contact_id=contact_id,
        display_name=display_name.strip(),
        runtime=runtime,
        provider_id=provider_id if isinstance(provider_id, str) else None,
        model_id=model_id if isinstance(model_id, str) else None,
        voice_profile_id=voice_profile_id if isinstance(voice_profile_id, str) else None,
        prefs_json=prefs_json,
    )
    if contact is None:
        return JSONResponse(status_code=404, content={"ok": False, "error": "Voice contact not found"})
    return JSONResponse(status_code=200, content={"contact": contact})


@router.delete("/api/voice-contacts/{contact_id}")
async def delete_voice_contact(contact_id: str) -> JSONResponse:
    store = get_call_store()
    deleted = store.delete_voice_contact(contact_id)
    if not deleted:
        return JSONResponse(status_code=404, content={"ok": False, "error": "Voice contact not found"})
    return JSONResponse(status_code=200, content={"ok": True})


@router.post("/api/calls/sessions/{call_session_id}/channels/twilio/start")
async def start_twilio_channel(call_session_id: str, request: Request) -> JSONResponse:
    store = get_call_store()
    session = store.get_call_session(call_session_id)
    if session is None:
        return JSONResponse(status_code=404, content={"ok": False, "error": "Call session not found"})
    payload = await request.json()
    phone_number = payload.get("phone_number") if isinstance(payload, dict) else None
    store.add_call_event(call_session_id, "channel.twilio.start", {"phone_number": phone_number})
    return JSONResponse(
        status_code=200,
        content={
            "ok": True,
            "channel": "twilio",
            "stream_ws_url": f"/ws/calls/{call_session_id}",
            "phone_number": phone_number,
        },
    )


@router.post("/api/calls/sessions/{call_session_id}/channels/webrtc/offer")
async def create_webrtc_answer(call_session_id: str, request: Request) -> JSONResponse:
    store = get_call_store()
    session = store.get_call_session(call_session_id)
    if session is None:
        return JSONResponse(status_code=404, content={"ok": False, "error": "Call session not found"})
    payload = await request.json()
    offer_sdp = payload.get("offer_sdp") if isinstance(payload, dict) else None
    if not isinstance(offer_sdp, str) or not offer_sdp.strip():
        return JSONResponse(status_code=422, content={"detail": "offer_sdp is required"})
    store.add_call_event(call_session_id, "channel.webrtc.offer", {"offer_len": len(offer_sdp)})
    answer_sdp = "v=0\r\no=octopusos 0 0 IN IP4 127.0.0.1\r\ns=OctopusOS Calls\r\nt=0 0\r\nm=audio 9 RTP/AVP 0\r\n"
    return JSONResponse(status_code=200, content={"ok": True, "answer_sdp": answer_sdp})


@router.post("/api/calls/sessions/{call_session_id}/channels/sip/transfer")
async def transfer_sip_call(
    call_session_id: str,
    request: Request,
    admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
) -> JSONResponse:
    store = get_call_store()
    session = store.get_call_session(call_session_id)
    if session is None:
        return JSONResponse(status_code=404, content={"ok": False, "error": "Call session not found"})
    if not _require_admin_token(admin_token):
        return JSONResponse(status_code=403, content={"ok": False, "error": "Invalid admin token"})
    payload = await request.json()
    target = payload.get("target") if isinstance(payload, dict) else None
    if not isinstance(target, str) or not target.strip():
        return JSONResponse(status_code=422, content={"detail": "target is required"})
    store.add_call_event(call_session_id, "channel.sip.transfer", {"target": target})
    return JSONResponse(status_code=200, content={"ok": True, "transferred_to": target})


@router.post("/api/calls/sessions/{call_session_id}/recording/start")
async def start_call_recording(call_session_id: str) -> JSONResponse:
    store = get_call_store()
    session = store.get_call_session(call_session_id)
    if session is None:
        return JSONResponse(status_code=404, content={"ok": False, "error": "Call session not found"})
    store.add_call_event(call_session_id, "recording.started", {})
    return JSONResponse(status_code=200, content={"ok": True, "recording": "started"})


@router.post("/api/calls/sessions/{call_session_id}/recording/stop")
async def stop_call_recording(call_session_id: str) -> JSONResponse:
    store = get_call_store()
    session = store.get_call_session(call_session_id)
    if session is None:
        return JSONResponse(status_code=404, content={"ok": False, "error": "Call session not found"})
    store.add_call_event(call_session_id, "recording.stopped", {})
    return JSONResponse(status_code=200, content={"ok": True, "recording": "stopped"})


@router.websocket("/ws/calls/{call_session_id}")
async def call_websocket(call_session_id: str, websocket: WebSocket) -> None:
    store = get_call_store()
    session = store.get_call_session(call_session_id)
    if session is None:
        await websocket.close(code=4404)
        return

    await websocket.accept()
    store.update_call_status(call_session_id, "connected")
    store.add_call_event(call_session_id, "connected", {})
    provider_hint = _provider_hint_for_session(session)
    capabilities = _capabilities_for_provider(provider_hint)

    await websocket.send_json(
        {
            "type": "hello",
            "protocol_version": PROTOCOL_VERSION,
            "call_session_id": call_session_id,
            "capabilities": capabilities,
        }
    )
    await websocket.send_json({"type": "status", "status": "listening"})
    if provider_hint == "mock":
        if not _is_demo_or_test_mode():
            await websocket.send_json(
                {
                    "type": "error",
                    "message": "Mock calls provider is disabled outside demo/test mode",
                }
            )
            await websocket.close(code=1011)
            return
        await websocket.send_json(
            {
                "type": "audio_output",
                "codec": capabilities["audio_format_out"]["codec"],
                "sample_rate": capabilities["audio_format_out"]["sample_rate_hz"],
                "format": capabilities["audio_format_out"],
                "samples": _mock_audio_samples(),
            }
        )

    ended = False
    hold = False
    buffered_input: List[float] = []
    min_asr_samples = max(IN_AUDIO_FORMAT.sample_rate_hz * 2, 1)
    tts_task: Optional[asyncio.Task[None]] = None
    frame_samples_out = max(int(OUT_AUDIO_FORMAT.sample_rate_hz * (OUT_AUDIO_FORMAT.frame_ms / 1000)), 1)
    speaking = False
    volc_client: Optional[VolcRealtimeClient] = None
    volc_recv_task: Optional[asyncio.Task[None]] = None
    volc_tts_suppressed = False

    async def _handle_volc_event(event: Dict[str, Any]) -> None:
        nonlocal speaking, volc_tts_suppressed
        event_id = event.get("event_id")
        payload_json = event.get("payload_json")
        payload = payload_json if isinstance(payload_json, dict) else {}
        payload_bytes = event.get("payload_bytes")

        if event_id == 450:
            volc_tts_suppressed = True
            if speaking:
                store.add_call_event(call_session_id, "tts.cancelled", {"provider": "volc"})
            speaking = False
            store.add_call_event(call_session_id, "barge_in.triggered", {"source": "volc.asrinfo"})
            await websocket.send_json({"type": "status", "status": "listening"})
            return

        if event_id == 451:
            text = extract_text(payload)
            if not text:
                return
            speaker = "user"
            if is_final_asr(payload):
                store.add_transcript(call_session_id, speaker, text)
                store.add_call_event(call_session_id, "transcript.final", {"speaker": speaker})
            else:
                store.add_call_event(call_session_id, "transcript.partial", {"speaker": speaker, "text": text[:32]})
            return

        if event_id == 459:
            volc_tts_suppressed = False
            if speaking:
                store.add_call_event(call_session_id, "tts.completed", {"provider": "volc"})
            speaking = False
            await websocket.send_json({"type": "status", "status": "listening"})
            return

        if event_id == 550:
            text = extract_text(payload)
            if text:
                store.add_call_event(call_session_id, "llm.turn.completed", {"speaker": "assistant"})
                store.add_transcript(call_session_id, "assistant", text)
                store.add_call_event(call_session_id, "transcript.final", {"speaker": "assistant"})
            return

        if event_id == 352:
            if volc_tts_suppressed:
                return
            if not payload_bytes and payload:
                encoded = payload.get("audio")
                if isinstance(encoded, str) and encoded:
                    with contextlib.suppress(Exception):
                        payload_bytes = base64.b64decode(encoded)
            if isinstance(payload_bytes, (bytes, bytearray)):
                samples = _pcm16_to_float_samples(bytes(payload_bytes))
                if samples:
                    if not speaking:
                        store.add_call_event(call_session_id, "tts.started", {"provider": "volc"})
                    speaking = True
                    store.add_call_event(call_session_id, "tts.chunk", {"samples": len(samples)})
                    await websocket.send_json({"type": "status", "status": "speaking"})
                    await websocket.send_json(
                        {
                            "type": "audio_output",
                            "codec": "pcm_s16le",
                            "sample_rate": 24000,
                            "format": capabilities["audio_format_out"],
                            "samples": samples,
                        }
                    )
            return

        if event_id in {350, 351, 359}:
            status = "speaking" if event_id in {350, 351} else "listening"
            await websocket.send_json({"type": "status", "status": status})
            return

        if event_id == 154:
            store.add_call_event(call_session_id, "volc.usage", payload)
            return

        if event_id in {599, 153}:
            reason = extract_error(payload, fallback="Volc session failed")
            store.add_call_event(call_session_id, "error", {"detail": reason, "provider": "volc"})
            await websocket.send_json({"type": "error", "message": reason})
            await websocket.send_json({"type": "status", "status": "ended"})
            store.update_call_status(call_session_id, "error", error_message=reason)
            return

    if provider_hint == "volc":
        try:
            volc_client = VolcRealtimeClient(session_id=call_session_id)
            logid = await volc_client.connect()
            await volc_client.start_connection()
            await volc_client.start_session()
            store.add_call_event(
                call_session_id,
                "volc.connected",
                {"connect_id": volc_client.connect_id, "x_tt_logid": logid},
            )
            volc_recv_task = asyncio.create_task(volc_client.recv_loop(_handle_volc_event))
        except VolcConfigError as exc:
            message = str(exc)
            store.add_call_event(call_session_id, "error", {"detail": message, "provider": "volc"})
            store.update_call_status(call_session_id, "error", error_message=message)
            await websocket.send_json({"type": "error", "message": message})
            await websocket.send_json({"type": "status", "status": "ended"})
            await websocket.close(code=1011)
            return
        except Exception as exc:
            message = f"Failed to connect Volc realtime: {exc}"
            store.add_call_event(call_session_id, "error", {"detail": message, "provider": "volc"})
            store.update_call_status(call_session_id, "error", error_message=message)
            await websocket.send_json({"type": "error", "message": message})
            await websocket.send_json({"type": "status", "status": "ended"})
            await websocket.close(code=1011)
            return

    try:
        while True:
            message = await websocket.receive_json()
            if not isinstance(message, dict):
                continue

            message_type = message.get("type")

            if message_type == "control.end":
                if tts_task is not None and not tts_task.done():
                    tts_task.cancel()
                if volc_client is not None:
                    with contextlib.suppress(Exception):
                        await volc_client.finish_session()
                    with contextlib.suppress(Exception):
                        await volc_client.finish_connection()
                store.add_call_event(call_session_id, "ended", {"reason": "client_end"})
                store.update_call_status(call_session_id, "ended")
                await websocket.send_json({"type": "status", "status": "ended"})
                ended = True
                await websocket.close(code=1000)
                break

            if message_type == "control.mute":
                muted = bool(message.get("muted", False))
                store.add_call_event(call_session_id, "mute_changed", {"muted": muted})
                continue

            if message_type == "control.hold":
                hold = bool(message.get("hold", False))
                if hold and tts_task is not None and not tts_task.done():
                    tts_task.cancel()
                if hold:
                    volc_tts_suppressed = True
                else:
                    volc_tts_suppressed = False
                event_name = "call.hold.on" if hold else "call.hold.off"
                store.add_call_event(call_session_id, event_name, {})
                await websocket.send_json({"type": "status", "status": "hold" if hold else "listening"})
                continue

            if message_type == "audio_input":
                frame_size = len(message.get("samples") or [])
                store.add_call_event(call_session_id, "audio_input", {"samples": frame_size})
                if hold:
                    continue

                frame_samples = message.get("samples")
                if provider_hint == "volc":
                    if isinstance(frame_samples, list):
                        chunk = [float(v) for v in frame_samples if isinstance(v, (int, float))]
                        if chunk and volc_client is not None:
                            try:
                                await volc_client.send_audio(_float_samples_to_pcm16(chunk))
                                store.add_call_event(call_session_id, "volc.media.in", {"samples": len(chunk)})
                            except Exception as exc:
                                store.add_call_event(call_session_id, "error", {"detail": str(exc), "provider": "volc"})
                                await websocket.send_json({"type": "error", "message": f"Volc send error: {exc}"})
                    continue
                if isinstance(frame_samples, list):
                    for value in frame_samples:
                        if isinstance(value, (int, float)):
                            buffered_input.append(float(value))

                if speaking and isinstance(frame_samples, list):
                    energy = _speech_energy([float(v) for v in frame_samples if isinstance(v, (int, float))])
                    if energy >= _vad_threshold():
                        if tts_task is not None and not tts_task.done():
                            tts_task.cancel()
                            store.add_call_event(call_session_id, "barge_in.triggered", {"energy": energy})
                        speaking = False
                        await websocket.send_json({"type": "status", "status": "listening"})

                if len(buffered_input) < min_asr_samples:
                    continue

                working_buffer = buffered_input[:]
                buffered_input.clear()

                transcript = (
                    await asyncio.to_thread(
                        transcribe_samples,
                        working_buffer,
                        IN_AUDIO_FORMAT,
                        provider_hint,
                    )
                ).strip()
                if not transcript:
                    continue

                partial = transcript[: max(1, min(len(transcript), 16))]
                store.add_call_event(call_session_id, "transcript.partial", {"speaker": "user", "text": partial})

                store.add_transcript(call_session_id, "user", transcript)
                store.add_call_event(call_session_id, "transcript.final", {"speaker": "user"})

                store.add_call_event(call_session_id, "llm.turn.requested", {"speaker": "user"})
                reply_text = f"你说的是：{transcript}"
                created_task_id = _create_agent_task_from_transcript(call_session_id, transcript)
                if created_task_id:
                    store.set_call_task_link(call_session_id, created_task_id)
                    store.add_call_event(call_session_id, "agent.task.created", {"task_id": created_task_id})
                    reply_text = f"已创建任务 {created_task_id}。我听到：{transcript}"

                store.add_transcript(call_session_id, "assistant", reply_text)
                store.add_call_event(call_session_id, "transcript.final", {"speaker": "assistant"})
                store.add_call_event(call_session_id, "llm.turn.completed", {"speaker": "assistant"})

                tts_samples = await asyncio.to_thread(
                    synthesize_samples,
                    reply_text,
                    OUT_AUDIO_FORMAT,
                    provider_hint,
                )
                if tts_task is not None and not tts_task.done():
                    tts_task.cancel()

                async def _stream_tts_output(samples: List[float]) -> None:
                    nonlocal speaking
                    speaking = True
                    try:
                        store.add_call_event(call_session_id, "tts.started", {"samples": len(samples)})
                        await websocket.send_json({"type": "status", "status": "speaking"})
                        for chunk in _chunk_samples(samples, frame_samples_out):
                            if hold:
                                store.add_call_event(call_session_id, "tts.paused_hold", {})
                                break
                            await websocket.send_json(
                                {
                                    "type": "audio_output",
                                    "codec": OUT_AUDIO_FORMAT.codec,
                                    "sample_rate": OUT_AUDIO_FORMAT.sample_rate_hz,
                                    "format": OUT_AUDIO_FORMAT.to_dict(),
                                    "samples": chunk,
                                }
                            )
                            store.add_call_event(call_session_id, "tts.chunk", {"samples": len(chunk)})
                            await asyncio.sleep(max(OUT_AUDIO_FORMAT.frame_ms, 1) / 1000.0)
                    except asyncio.CancelledError:
                        store.add_call_event(call_session_id, "tts.cancelled", {})
                        raise
                    finally:
                        speaking = False
                        store.add_call_event(call_session_id, "tts.completed", {})
                        try:
                            await websocket.send_json({"type": "status", "status": "listening"})
                        except Exception:
                            pass

                tts_task = asyncio.create_task(_stream_tts_output(tts_samples))
                continue

            store.add_call_event(call_session_id, "error", {"detail": "unsupported_message"})
            await websocket.send_json(
                {
                    "type": "error",
                    "message": "Unsupported websocket message",
                }
            )

    except WebSocketDisconnect:
        if tts_task is not None and not tts_task.done():
            tts_task.cancel()
        if volc_recv_task is not None and not volc_recv_task.done():
            volc_recv_task.cancel()
        if volc_client is not None:
            with contextlib.suppress(Exception):
                await volc_client.finish_session()
            with contextlib.suppress(Exception):
                await volc_client.finish_connection()
            with contextlib.suppress(Exception):
                await volc_client.close()
        store.add_call_event(call_session_id, "disconnected", {})
    except Exception as exc:  # pragma: no cover - defensive fallback
        if tts_task is not None and not tts_task.done():
            tts_task.cancel()
        if volc_recv_task is not None and not volc_recv_task.done():
            volc_recv_task.cancel()
        if volc_client is not None:
            with contextlib.suppress(Exception):
                await volc_client.close()
        store.add_call_event(call_session_id, "error", {"detail": str(exc)})
        store.update_call_status(call_session_id, "error", error_message=str(exc))
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
    finally:
        if volc_recv_task is not None and not volc_recv_task.done():
            volc_recv_task.cancel()
        if volc_client is not None:
            with contextlib.suppress(Exception):
                await volc_client.close()
        if not ended:
            store.update_call_status(call_session_id, "ended")
            store.add_call_event(call_session_id, "ended", {"reason": "disconnect"})


__all__ = ["router"]
