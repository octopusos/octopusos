# Voice API Documentation

## Overview

The Voice API provides REST and WebSocket endpoints for voice-based interactions in AgentOS. It enables:
- Voice session management
- Real-time audio streaming via WebSocket
- Speech-to-Text (STT) integration
- Text-to-Speech (TTS) integration (future)
- Integration with AgentOS chat engine (future)

**Status**: MVP Implementation
**Version**: 1.0.0
**Module**: `agentos.webui.api.voice`

## Architecture

```
┌─────────────┐
│   Client    │
│  (Browser/  │
│    App)     │
└──────┬──────┘
       │
       │ ① REST: Create Session
       │ POST /api/voice/sessions
       ├─────────────────────────────┐
       │                             │
       │ ② WebSocket: Connect        │
       │ WS /api/voice/sessions/{id}/events
       ├─────────────────────────────┤
       │                             │
       │ ③ Send Audio Chunks         │
       │ voice.audio.chunk           │
       │                             │
       │ ④ Receive STT Results       │
       │ voice.stt.final             │
       │                             │
       │ ⑤ Receive Assistant Reply   │
       │ voice.assistant.text        │
       │                             │
       │ ⑥ REST: Stop Session        │
       │ POST /api/voice/sessions/{id}/stop
       └─────────────────────────────┘
```

## REST API Endpoints

### 1. Create Voice Session

**Endpoint**: `POST /api/voice/sessions`

Creates a new voice conversation session.

**Request Body**:
```json
{
  "project_id": "proj-abc123",      // Optional: Project context
  "provider": "local",              // Voice provider: local, openai, azure
  "stt_provider": "whisper_local"   // STT provider: whisper_local, openai, azure, mock
}
```

**Response** (200 OK):
```json
{
  "ok": true,
  "data": {
    "session_id": "voice-a1b2c3d4e5f6",
    "project_id": "proj-abc123",
    "provider": "local",
    "stt_provider": "whisper_local",
    "state": "ACTIVE",
    "created_at": "2026-02-01T12:34:56.789012Z",
    "ws_url": "/api/voice/sessions/voice-a1b2c3d4e5f6/events"
  },
  "error": null,
  "hint": null,
  "reason_code": null
}
```

**Error Response** (400 Bad Request):
```json
{
  "ok": false,
  "data": null,
  "error": "Invalid provider: invalid-provider",
  "hint": "Valid providers: local, openai, azure",
  "reason_code": "INVALID_INPUT"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/api/voice/sessions \
  -H "Content-Type: application/json" \
  -d '{"project_id":"test","provider":"local","stt_provider":"whisper_local"}'
```

---

### 2. Get Voice Session

**Endpoint**: `GET /api/voice/sessions/{session_id}`

Retrieves information about a voice session.

**Path Parameters**:
- `session_id` (string, required): Voice session ID

**Response** (200 OK):
```json
{
  "ok": true,
  "data": {
    "session_id": "voice-a1b2c3d4e5f6",
    "project_id": "proj-abc123",
    "provider": "local",
    "stt_provider": "whisper_local",
    "state": "ACTIVE",
    "created_at": "2026-02-01T12:34:56.789012Z"
  },
  "error": null,
  "hint": null,
  "reason_code": null
}
```

**Error Response** (404 Not Found):
```json
{
  "ok": false,
  "data": null,
  "error": "Voice session not found: invalid-id",
  "hint": "Check the voice session_id and ensure the voice session exists",
  "reason_code": "VOICE SESSION_NOT_FOUND"
}
```

**Example**:
```bash
curl http://localhost:8000/api/voice/sessions/voice-a1b2c3d4e5f6
```

---

### 3. Stop Voice Session

**Endpoint**: `POST /api/voice/sessions/{session_id}/stop`

Stops an active voice session.

**Path Parameters**:
- `session_id` (string, required): Voice session ID

**Response** (200 OK):
```json
{
  "ok": true,
  "data": {
    "session_id": "voice-a1b2c3d4e5f6",
    "state": "STOPPED",
    "stopped_at": "2026-02-01T12:35:00.123456Z"
  },
  "error": null,
  "hint": null,
  "reason_code": null
}
```

**Error Response** (409 Conflict):
```json
{
  "ok": false,
  "data": null,
  "error": "Session already stopped",
  "hint": "Session is already in STOPPED state",
  "reason_code": "BAD_STATE"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/api/voice/sessions/voice-a1b2c3d4e5f6/stop
```

---

### 4. List Voice Sessions

**Endpoint**: `GET /api/voice/sessions`

Lists all voice sessions (for debugging).

**Query Parameters**:
- `state` (string, optional): Filter by state (ACTIVE, STOPPED)
- `limit` (integer, optional): Maximum results (1-1000, default: 100)

**Response** (200 OK):
```json
{
  "ok": true,
  "data": {
    "sessions": [
      {
        "session_id": "voice-a1b2c3d4e5f6",
        "project_id": "proj-abc123",
        "provider": "local",
        "stt_provider": "whisper_local",
        "state": "ACTIVE",
        "created_at": "2026-02-01T12:34:56.789012Z"
      }
    ],
    "total": 1,
    "filters_applied": {
      "state": "ACTIVE",
      "limit": 100
    }
  },
  "error": null,
  "hint": null,
  "reason_code": null
}
```

**Example**:
```bash
curl "http://localhost:8000/api/voice/sessions?state=ACTIVE&limit=10"
```

---

## WebSocket API

### Connection

**Endpoint**: `WS /api/voice/sessions/{session_id}/events`

Connect to the WebSocket after creating a session via REST API.

**Example**:
```javascript
const ws = new WebSocket('ws://localhost:8000/api/voice/sessions/voice-a1b2c3d4e5f6/events');
```

---

### Server Events

Events sent from server to client.

#### 1. voice.session.ready

Sent immediately after connection is established.

```json
{
  "type": "voice.session.ready",
  "session_id": "voice-a1b2c3d4e5f6",
  "timestamp": "2026-02-01T12:34:56.789012Z"
}
```

#### 2. voice.stt.partial

Partial transcription result (for real-time feedback).

```json
{
  "type": "voice.stt.partial",
  "text": "Hello, I am...",
  "timestamp": "2026-02-01T12:34:57.123456Z"
}
```

#### 3. voice.stt.final

Final transcription result.

```json
{
  "type": "voice.stt.final",
  "text": "Hello, I am testing the voice API",
  "timestamp": "2026-02-01T12:34:58.456789Z"
}
```

#### 4. voice.assistant.text

Assistant text response (MVP: echo response).

```json
{
  "type": "voice.assistant.text",
  "text": "[MVP Echo] You said: Hello, I am testing the voice API",
  "timestamp": "2026-02-01T12:34:58.567890Z"
}
```

#### 5. voice.error

Error message.

```json
{
  "type": "voice.error",
  "error": "Failed to process audio: Invalid format",
  "timestamp": "2026-02-01T12:34:59.012345Z"
}
```

---

### Client Events

Events sent from client to server.

#### 1. voice.audio.chunk

Send an audio data chunk.

```json
{
  "type": "voice.audio.chunk",
  "session_id": "voice-a1b2c3d4e5f6",
  "seq": 0,
  "format": {
    "codec": "pcm_s16le",
    "sample_rate": 16000,
    "channels": 1
  },
  "payload_b64": "AQIDBAUG...",
  "t_ms": 1738329600000
}
```

**Fields**:
- `type`: Event type (always `"voice.audio.chunk"`)
- `session_id`: Voice session ID
- `seq`: Sequence number for ordering chunks
- `format`: Audio format specification
  - `codec`: Audio codec (e.g., `pcm_s16le`, `opus`)
  - `sample_rate`: Sample rate in Hz (e.g., 16000)
  - `channels`: Number of channels (1=mono, 2=stereo)
- `payload_b64`: Base64-encoded audio data
- `t_ms`: Client timestamp in milliseconds since epoch

#### 2. voice.audio.end

Signal end of audio stream.

```json
{
  "type": "voice.audio.end",
  "session_id": "voice-a1b2c3d4e5f6",
  "t_ms": 1738329601000
}
```

---

## Audio Format

### Supported Codecs

**MVP**:
- `pcm_s16le`: 16-bit signed little-endian PCM (recommended)

**Future**:
- `opus`: Opus codec (compressed)
- `mp3`: MP3 codec
- `aac`: AAC codec

### Recommended Settings

For best quality and compatibility:
- **Codec**: `pcm_s16le`
- **Sample Rate**: `16000` Hz
- **Channels**: `1` (mono)
- **Bit Depth**: 16-bit

### Chunk Size Recommendations

- **Minimum**: 4000 bytes (~0.125 seconds at 16kHz)
- **Recommended**: 8000-16000 bytes (~0.25-0.5 seconds)
- **Maximum**: 64000 bytes (~2 seconds)

Smaller chunks provide more real-time feedback but increase overhead.

---

## Code Examples

### Python Client

```python
import asyncio
import json
import base64
import websockets
import requests

# 1. Create session
response = requests.post(
    "http://localhost:8000/api/voice/sessions",
    json={"project_id": "test", "provider": "local", "stt_provider": "whisper_local"}
)
session = response.json()["data"]
session_id = session["session_id"]

# 2. Connect to WebSocket
async def stream_audio():
    ws_url = f"ws://localhost:8000/api/voice/sessions/{session_id}/events"

    async with websockets.connect(ws_url) as ws:
        # Wait for ready
        ready = await ws.recv()
        print(f"Ready: {ready}")

        # Send audio chunk
        audio_data = b"\x00\x01\x02\x03" * 1000  # Mock audio
        event = {
            "type": "voice.audio.chunk",
            "session_id": session_id,
            "seq": 0,
            "format": {"codec": "pcm_s16le", "sample_rate": 16000, "channels": 1},
            "payload_b64": base64.b64encode(audio_data).decode('utf-8'),
            "t_ms": int(time.time() * 1000)
        }
        await ws.send(json.dumps(event))

        # Send end signal
        await ws.send(json.dumps({
            "type": "voice.audio.end",
            "session_id": session_id,
            "t_ms": int(time.time() * 1000)
        }))

        # Receive responses
        while True:
            response = await ws.recv()
            data = json.loads(response)
            print(f"Received: {data['type']}")
            if data['type'] == 'voice.assistant.text':
                break

asyncio.run(stream_audio())

# 3. Stop session
requests.post(f"http://localhost:8000/api/voice/sessions/{session_id}/stop")
```

### JavaScript (Browser)

```javascript
// 1. Create session
const response = await fetch('http://localhost:8000/api/voice/sessions', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    project_id: 'test',
    provider: 'local',
    stt_provider: 'whisper_local'
  })
});
const session = (await response.json()).data;

// 2. Connect to WebSocket
const ws = new WebSocket(`ws://localhost:8000${session.ws_url}`);

ws.onopen = () => {
  console.log('WebSocket connected');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data.type, data);

  if (data.type === 'voice.session.ready') {
    // Send audio chunk
    const audioData = new Uint8Array([0, 1, 2, 3]); // Mock audio
    const chunk = {
      type: 'voice.audio.chunk',
      session_id: session.session_id,
      seq: 0,
      format: {codec: 'pcm_s16le', sample_rate: 16000, channels: 1},
      payload_b64: btoa(String.fromCharCode(...audioData)),
      t_ms: Date.now()
    };
    ws.send(JSON.stringify(chunk));

    // Send end signal
    ws.send(JSON.stringify({
      type: 'voice.audio.end',
      session_id: session.session_id,
      t_ms: Date.now()
    }));
  }
};

// 3. Stop session (later)
await fetch(`http://localhost:8000/api/voice/sessions/${session.session_id}/stop`, {
  method: 'POST'
});
```

---

## Testing

### Unit Tests

```bash
# Run voice API unit tests
python3 test_voice_api.py
```

### REST API Tests

```bash
# Start server
uvicorn agentos.webui.app:app --reload

# Run curl tests
bash test_voice_rest_api.sh
```

### WebSocket Tests

```bash
# Start server
uvicorn agentos.webui.app:app --reload

# Run WebSocket demo
python3 examples/voice_websocket_demo.py
```

### Manual Testing with websocat

```bash
# Install websocat
cargo install websocat
# or: brew install websocat

# Create session first
SESSION_ID=$(curl -s -X POST http://localhost:8000/api/voice/sessions \
  -H "Content-Type: application/json" \
  -d '{"provider":"local","stt_provider":"mock"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['session_id'])")

# Connect to WebSocket
websocat ws://localhost:8000/api/voice/sessions/$SESSION_ID/events
```

---

## Error Handling

All API responses follow the standard AgentOS error format:

```json
{
  "ok": false,
  "data": null,
  "error": "Human-readable error message",
  "hint": "Suggestion for fixing the error",
  "reason_code": "MACHINE_READABLE_CODE"
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_INPUT` | 400 | Invalid request parameters |
| `NOT_FOUND` | 404 | Session not found |
| `BAD_STATE` | 409 | Invalid session state |
| `INTERNAL_ERROR` | 500 | Server error |

---

## Future Enhancements

### Phase 2: Chat Integration
- Connect STT output to AgentOS chat engine
- Replace mock echo with real assistant responses
- Support conversation context and memory

### Phase 3: TTS Integration
- Add Text-to-Speech capability
- Stream audio responses back to client
- Support multiple TTS providers (OpenAI, ElevenLabs, etc.)

### Phase 4: Advanced Features
- Voice Activity Detection (VAD)
- Real-time streaming STT with partial results
- Multi-turn conversation support
- Voice cloning and personalization
- Emotion detection in voice

---

## Implementation Notes

### MVP Scope

Current implementation (MVP):
- ✅ Session management (create, get, stop, list)
- ✅ WebSocket audio streaming
- ✅ Mock STT service
- ✅ Echo assistant response
- ✅ Error handling
- ✅ Comprehensive documentation

Not implemented (future):
- ❌ Real Whisper STT integration
- ❌ Chat engine integration
- ❌ TTS support
- ❌ Voice Activity Detection
- ❌ Real-time partial transcription

### Architecture Decisions

1. **In-Memory Session Store**: MVP uses in-memory storage for simplicity. Future: migrate to Redis or database.

2. **Mock STT Service**: MVP returns mock transcriptions. Future: integrate with local Whisper model or OpenAI API.

3. **Echo Response**: MVP echoes user input. Future: integrate with chat engine for real conversations.

4. **No Authentication**: MVP has no auth. Future: integrate with AgentOS auth system.

---

## API Contract

This API follows AgentOS API design principles:

- ✅ Unified response format (`ok`, `data`, `error`, `hint`, `reason_code`)
- ✅ ISO 8601 UTC timestamps with 'Z' suffix
- ✅ RESTful resource naming
- ✅ Comprehensive error messages
- ✅ Validation with helpful hints
- ✅ Consistent HTTP status codes

---

## Troubleshooting

### WebSocket Connection Fails

**Problem**: Cannot connect to WebSocket

**Solution**:
1. Ensure session exists: `GET /api/voice/sessions/{session_id}`
2. Verify session is ACTIVE (not STOPPED)
3. Check WebSocket URL format: `ws://` not `wss://` for local dev
4. Check firewall/proxy settings

### Audio Not Transcribed

**Problem**: No STT results received

**Solution**:
1. MVP uses mock STT - check logs for "[MVP STT]" messages
2. Verify audio format: must be 16-bit PCM, 16kHz, mono
3. Ensure audio.end event is sent to trigger transcription
4. Check audio payload is base64-encoded

### Session State Issues

**Problem**: Session shows STOPPED but shouldn't be

**Solution**:
1. Stop is idempotent - check stopped_at timestamp
2. Create new session if needed
3. Sessions persist in memory until server restart

---

## Related Documentation

- [AgentOS API Contracts](./API_CONTRACTS.md)
- [WebSocket Protocol](./WEBSOCKET_PROTOCOL.md)
- [Time Format Contract](./adr/ADR-011-time-timestamp-contract.md)
- [Error Handling](./ERROR_HANDLING.md)

---

**Version**: 1.0.0
**Last Updated**: 2026-02-01
**Status**: MVP Complete
