"""Binary frame helpers for Volc Realtime Dialogue API."""

from __future__ import annotations

import json
import struct
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

PROTOCOL_VERSION = 0x1
HEADER_WORDS = 0x1

SERIALIZATION_RAW = 0x0
SERIALIZATION_JSON = 0x1

COMPRESSION_NONE = 0x0

FLAG_EVENT = 0x1
FLAG_CONNECT_ID = 0x2
FLAG_SEQUENCE = 0x4

MSG_TYPE_CONTROL = 0x1
MSG_TYPE_AUDIO = 0x2
MSG_TYPE_ERROR = 0xF

EVENT_TASK_REQUEST_AUDIO = 200


@dataclass
class DecodedFrame:
    msg_type: int
    flags: int
    serialization: int
    compression: int
    event_id: Optional[int]
    session_id: str
    connect_id: Optional[str]
    sequence: Optional[int]
    payload_bytes: bytes
    payload_json: Optional[Dict[str, Any]]


def _encode_common(
    *,
    msg_type: int,
    flags: int,
    serialization: int,
    compression: int,
    session_id: str,
    payload_bytes: bytes,
    event_id: Optional[int] = None,
    connect_id: Optional[str] = None,
    sequence: Optional[int] = None,
) -> bytes:
    if not session_id:
        raise ValueError("session_id is required")

    first = (PROTOCOL_VERSION << 4) | HEADER_WORDS
    second = (msg_type << 4) | (flags & 0x0F)
    third = (serialization << 4) | (compression & 0x0F)
    fourth = 0x00

    parts = [bytes([first, second, third, fourth])]

    if flags & FLAG_EVENT:
        if event_id is None:
            raise ValueError("event_id required when FLAG_EVENT is set")
        parts.append(struct.pack("!H", event_id))

    session_raw = session_id.encode("utf-8")
    parts.append(struct.pack("!H", len(session_raw)))
    parts.append(session_raw)

    if flags & FLAG_CONNECT_ID:
        connect_raw = (connect_id or str(uuid.uuid4())).encode("utf-8")
        parts.append(struct.pack("!H", len(connect_raw)))
        parts.append(connect_raw)

    if flags & FLAG_SEQUENCE:
        if sequence is None:
            raise ValueError("sequence required when FLAG_SEQUENCE is set")
        parts.append(struct.pack("!i", sequence))

    parts.append(struct.pack("!I", len(payload_bytes)))
    parts.append(payload_bytes)

    return b"".join(parts)


def encode_json_event(
    *,
    event_id: int,
    session_id: str,
    payload_dict: Dict[str, Any],
    sequence: Optional[int] = None,
    connect_id: Optional[str] = None,
) -> bytes:
    flags = FLAG_EVENT | FLAG_CONNECT_ID
    if sequence is not None:
        flags |= FLAG_SEQUENCE

    payload_bytes = json.dumps(payload_dict, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return _encode_common(
        msg_type=MSG_TYPE_CONTROL,
        flags=flags,
        serialization=SERIALIZATION_JSON,
        compression=COMPRESSION_NONE,
        event_id=event_id,
        session_id=session_id,
        connect_id=connect_id,
        sequence=sequence,
        payload_bytes=payload_bytes,
    )


def encode_audio_frame(
    *,
    session_id: str,
    pcm_bytes: bytes,
    sequence: Optional[int] = None,
    connect_id: Optional[str] = None,
) -> bytes:
    flags = FLAG_EVENT | FLAG_CONNECT_ID
    if sequence is not None:
        flags |= FLAG_SEQUENCE

    return _encode_common(
        msg_type=MSG_TYPE_AUDIO,
        flags=flags,
        serialization=SERIALIZATION_RAW,
        compression=COMPRESSION_NONE,
        event_id=EVENT_TASK_REQUEST_AUDIO,
        session_id=session_id,
        connect_id=connect_id,
        sequence=sequence,
        payload_bytes=pcm_bytes,
    )


def decode_frame(data: bytes) -> DecodedFrame:
    if len(data) < 8:
        raise ValueError("frame too short")

    first, second, third = data[0], data[1], data[2]
    version = (first >> 4) & 0x0F
    if version != PROTOCOL_VERSION:
        raise ValueError(f"unsupported protocol version {version}")

    msg_type = (second >> 4) & 0x0F
    flags = second & 0x0F
    serialization = (third >> 4) & 0x0F
    compression = third & 0x0F
    if compression != COMPRESSION_NONE:
        raise ValueError("unsupported compression")

    offset = 4
    event_id: Optional[int] = None
    if flags & FLAG_EVENT:
        if len(data) < offset + 2:
            raise ValueError("missing event_id")
        event_id = struct.unpack("!H", data[offset:offset + 2])[0]
        offset += 2

    if len(data) < offset + 2:
        raise ValueError("missing session_id length")
    session_len = struct.unpack("!H", data[offset:offset + 2])[0]
    offset += 2
    if session_len <= 0:
        raise ValueError("session ID length is zero")
    if len(data) < offset + session_len:
        raise ValueError("missing session_id")
    session_id = data[offset:offset + session_len].decode("utf-8")
    offset += session_len

    connect_id: Optional[str] = None
    if flags & FLAG_CONNECT_ID:
        if len(data) < offset + 2:
            raise ValueError("missing connect_id length")
        connect_len = struct.unpack("!H", data[offset:offset + 2])[0]
        offset += 2
        if len(data) < offset + connect_len:
            raise ValueError("missing connect_id")
        connect_id = data[offset:offset + connect_len].decode("utf-8")
        offset += connect_len

    sequence: Optional[int] = None
    if flags & FLAG_SEQUENCE:
        if len(data) < offset + 4:
            raise ValueError("missing sequence")
        sequence = struct.unpack("!i", data[offset:offset + 4])[0]
        offset += 4

    if len(data) < offset + 4:
        raise ValueError("missing payload length")
    payload_len = struct.unpack("!I", data[offset:offset + 4])[0]
    offset += 4
    if len(data) < offset + payload_len:
        raise ValueError("truncated payload")

    payload_bytes = data[offset:offset + payload_len]

    payload_json: Optional[Dict[str, Any]] = None
    if serialization == SERIALIZATION_JSON and payload_bytes:
        payload_json = json.loads(payload_bytes.decode("utf-8"))

    return DecodedFrame(
        msg_type=msg_type,
        flags=flags,
        serialization=serialization,
        compression=compression,
        event_id=event_id,
        session_id=session_id,
        connect_id=connect_id,
        sequence=sequence,
        payload_bytes=payload_bytes,
        payload_json=payload_json,
    )
