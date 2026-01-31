# Twilio Voice Integration (Task #13)

## Overview

The Twilio Voice Integration enables AgentOS to receive and process phone calls via Twilio's Voice API. This implementation provides:

1. **Inbound Call Webhook** - Handles incoming calls and returns TwiML to establish Media Streams
2. **Media Streams WebSocket** - Receives real-time audio from Twilio, transcribes with Whisper STT, and sends assistant responses

## Architecture

```
┌─────────────┐         ┌──────────────┐         ┌──────────────┐
│   Caller    │────────>│    Twilio    │────────>│   AgentOS    │
│   (Phone)   │  PSTN   │  Voice API   │  Media  │   WebUI      │
└─────────────┘         └──────────────┘ Streams └──────────────┘
                              │                         │
                              │ 1. POST /inbound       │
                              │    (form-encoded)      │
                              │<────────────────────────│
                              │ 2. TwiML Response      │
                              │    <Stream url="...">  │
                              │                         │
                              │ 3. WebSocket /stream   │
                              │    (μ-law audio)       │
                              │<───────────────────────>│
                              │                         │
                              │ 4. Media events        │
                              │    - start             │
                              │    - media (audio)     │
                              │    - stop              │
                              └─────────────────────────┘
```

## API Endpoints

### 1. POST /api/voice/twilio/inbound

**Purpose**: Twilio inbound call webhook that returns TwiML to establish Media Stream.

**Called by**: Twilio Voice API when an inbound call arrives.

**Request** (form-encoded from Twilio):
```
CallSid=CA1234567890abcdef1234567890abcdef
From=+14155551234
To=+14155555678
CallStatus=ringing
```

**Response** (TwiML XML):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Connecting to agent.</Say>
    <Start>
        <Stream url="wss://your-domain.com/api/voice/twilio/stream/twilio-CA123..." />
    </Start>
</Response>
```

**Implementation**:
- Parses Twilio webhook parameters
- Creates VoiceSession with Twilio metadata
- Generates TwiML with WebSocket URL
- Returns XML response

### 2. WebSocket /api/voice/twilio/stream/{session_id}

**Purpose**: Receives Twilio Media Streams audio, transcribes with STT, sends responses.

**Protocol**: Twilio Media Streams WebSocket Protocol

**Events from Twilio**:

1. **start** - Stream initialization
```json
{
  "event": "start",
  "sequenceNumber": "1",
  "start": {
    "streamSid": "MZ...",
    "callSid": "CA...",
    "tracks": ["inbound"],
    "mediaFormat": {
      "encoding": "audio/x-mulaw",
      "sampleRate": 8000,
      "channels": 1
    }
  }
}
```

2. **media** - Audio data chunk
```json
{
  "event": "media",
  "sequenceNumber": "4",
  "media": {
    "track": "inbound",
    "chunk": "4",
    "timestamp": "5000",
    "payload": "base64-encoded-mulaw-audio"
  },
  "streamSid": "MZ..."
}
```

3. **stop** - Stream termination
```json
{
  "event": "stop",
  "sequenceNumber": "100",
  "stop": {
    "callSid": "CA..."
  },
  "streamSid": "MZ..."
}
```

**Events to Client**:

1. **voice.stt.final** - STT transcription result
```json
{
  "type": "voice.stt.final",
  "text": "Hello, how are you?",
  "session_id": "twilio-CA123...",
  "timestamp": "2026-02-01T12:34:56.789012Z"
}
```

2. **voice.assistant.text** - Assistant response
```json
{
  "type": "voice.assistant.text",
  "text": "You said: Hello, how are you?",
  "session_id": "twilio-CA123...",
  "timestamp": "2026-02-01T12:34:57.123456Z"
}
```

3. **error** - Error message
```json
{
  "type": "error",
  "error": "STT processing failed: ...",
  "timestamp": "2026-02-01T12:34:58.000000Z"
}
```

## Audio Processing Pipeline

### 1. Audio Format Conversion

Twilio Media Streams sends audio in **μ-law (G.711)** format:
- Encoding: μ-law (8-bit compressed)
- Sample Rate: 8 kHz
- Channels: 1 (mono)

Whisper STT expects **PCM 16-bit linear** audio:
- Encoding: PCM signed 16-bit
- Sample Rate: 8 kHz (or higher)
- Channels: 1 (mono)

**Transcoding**:
```python
def transcode_mulaw_to_pcm(mulaw_bytes: bytes) -> bytes:
    """Convert μ-law to PCM 16-bit."""
    # Uses numpy-based μ-law decompression
    # Formula: linear = (mantissa * 2 + 33) * 2^magnitude - 33
    # Then scale to 16-bit range
```

### 2. Audio Buffering

Audio chunks are accumulated until a threshold (3 seconds / 48KB):
```python
BUFFER_THRESHOLD = 48000  # 3 seconds at 8kHz, 16-bit mono
```

When buffer reaches threshold:
1. Transcribe accumulated audio with Whisper STT
2. Send transcript to client
3. Get assistant response (MVP: echo, Production: ChatService)
4. Send response to client
5. Clear buffer

### 3. STT Integration

Uses `WhisperLocalSTT` from `agentos.core.communication.voice.stt.whisper_local`:
```python
stt_service = WhisperLocalSTT(model_name="base", device="cpu")
transcript = await stt_service.transcribe_audio(
    bytes(audio_buffer),
    sample_rate=8000,
)
```

## Configuration

### Twilio Setup

1. **Get Twilio Phone Number**:
   - Sign up at https://www.twilio.com
   - Purchase a phone number with Voice capability

2. **Configure Voice Webhook**:
   - Navigate to Phone Numbers > Active Numbers
   - Select your number
   - Under "Voice & Fax", set:
     - **A Call Comes In**: Webhook
     - **URL**: `https://your-domain.com/api/voice/twilio/inbound`
     - **HTTP Method**: POST

3. **WebSocket Requirements**:
   - Must use `wss://` (secure WebSocket)
   - Must be publicly accessible (use ngrok for local testing)

### Environment Variables

```bash
# Optional: Twilio credentials (for future REST API features)
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
```

### Local Testing with ngrok

```bash
# Start ngrok tunnel
ngrok http 8000

# Use ngrok URL in Twilio webhook configuration
# Example: https://abc123.ngrok.io/api/voice/twilio/inbound
```

## Session Management

### Session Creation

When an inbound call arrives:
```python
session = create_twilio_session(
    call_sid="CA1234567890abcdef1234567890abcdef",
    from_number="+14155551234",
    to_number="+14155555678",
    project_id="default",
)
```

### Session Structure

```python
VoiceSession(
    session_id="twilio-CA123...",
    project_id="default",
    provider=VoiceProvider.TWILIO,
    stt_provider=STTProvider.WHISPER,
    transport=TransportType.TWILIO_STREAM,
    transport_metadata={
        "call_sid": "CA123...",
        "stream_sid": "MZ...",
        "from_number": "+14155551234",
        "to_number": "+14155555678",
    },
    state=VoiceSessionState.ACTIVE,
)
```

### Session Lifecycle

1. **CREATED** - Session created, TwiML returned
2. **ACTIVE** - Media Stream connected, processing audio
3. **STOPPED** - Stream ended, session complete

## Assistant Integration (MVP)

**Current**: Simple echo response
```python
async def get_assistant_response(transcript: str, session_id: str) -> str:
    return f"You said: {transcript}"
```

**Production TODO**:
```python
async def get_assistant_response(transcript: str, session_id: str) -> str:
    # 1. Get session context
    session = get_twilio_session(session_id)
    project_id = session.project_id

    # 2. Call ChatService
    from agentos.core.chat.service import ChatService
    chat_service = ChatService()

    # 3. Create or get chat session
    # 4. Send user message
    # 5. Get assistant response
    # 6. Return text

    return assistant_text
```

## Error Handling

### Inbound Webhook Errors

Returns error TwiML:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Sorry, we encountered an error. Please try again later.</Say>
    <Hangup />
</Response>
```

### WebSocket Errors

Sends error event to client:
```json
{
  "type": "error",
  "error": "Description of error",
  "timestamp": "2026-02-01T12:34:56.789012Z"
}
```

## Audit Logging

All voice events are logged with AUDIT prefix:
```
INFO: AUDIT: voice.twilio.session.created session_id=twilio-CA123 call_sid=CA123 from=+14155551234 to=+14155555678
INFO: AUDIT: voice.twilio.stream.connected session_id=twilio-CA123 call_sid=CA123
INFO: AUDIT: voice.twilio.stream.started session_id=twilio-CA123 stream_sid=MZ123 call_sid=CA123
INFO: AUDIT: voice.twilio.transcript session_id=twilio-CA123 stream_sid=MZ123 transcript='Hello' response='You said: Hello'
INFO: AUDIT: voice.twilio.stream.stopped session_id=twilio-CA123 stream_sid=MZ123 reason={...}
```

## Testing

### Unit Tests

Run verification script:
```bash
python3 scripts/verify_twilio_implementation.py
```

Checks:
- ✓ Module import
- ✓ Router endpoints
- ✓ Required functions
- ✓ μ-law transcoding
- ✓ Session management

### Manual Testing

1. **Start AgentOS WebUI**:
   ```bash
   agentos webui start
   ```

2. **Expose via ngrok**:
   ```bash
   ngrok http 8000
   ```

3. **Configure Twilio webhook**:
   - Set webhook URL to: `https://xxx.ngrok.io/api/voice/twilio/inbound`

4. **Call Twilio number**:
   - You should hear: "Connecting to agent."
   - Speak into the phone
   - Every ~3 seconds, your speech will be transcribed
   - You'll hear the transcript echoed back (via TTS in future)

### Troubleshooting

**Problem**: WebSocket connection rejected
- **Check**: Is ngrok running? Is URL publicly accessible?
- **Check**: Does URL use `wss://` (not `ws://`)?

**Problem**: No transcription received
- **Check**: Is Whisper model loaded? Check logs for model loading errors
- **Check**: Is audio buffer reaching threshold? Check debug logs

**Problem**: "Session not found" error
- **Check**: Was inbound webhook called first?
- **Check**: Session ID in WebSocket URL matches created session

## Limitations (MVP)

1. **No TTS for outbound audio** - Assistant responses are sent as text events only
2. **Echo response only** - Not integrated with ChatService yet
3. **No conversation memory** - Each transcript is processed independently
4. **No real-time streaming** - Waits for buffer threshold before processing
5. **In-memory sessions** - Lost on server restart (production: use Redis)

## Future Enhancements

1. **TTS Integration**:
   - Use Twilio `<Say>` for text-to-speech
   - Or stream TTS audio back via Media Streams outbound track

2. **ChatService Integration**:
   - Create chat session for each call
   - Maintain conversation context
   - Support multi-turn conversations

3. **Real-time Streaming**:
   - Implement streaming STT for lower latency
   - Send partial transcripts as user speaks

4. **Persistent Sessions**:
   - Store sessions in database or Redis
   - Support session recovery

5. **Call Control**:
   - Support transfer, hold, mute
   - Conference calls
   - Recording and playback

## References

- [Twilio Voice API](https://www.twilio.com/docs/voice)
- [Twilio Media Streams](https://www.twilio.com/docs/voice/media-streams)
- [TwiML Reference](https://www.twilio.com/docs/voice/twiml)
- [G.711 μ-law](https://en.wikipedia.org/wiki/G.711)
- [Whisper STT](https://github.com/openai/whisper)

## Implementation Files

- `agentos/webui/api/voice_twilio.py` - Main implementation
- `agentos/core/communication/voice/models.py` - Data models
- `agentos/core/communication/voice/stt/whisper_local.py` - STT service
- `scripts/verify_twilio_implementation.py` - Verification script
- `tests/integration/voice/test_twilio_api.py` - Integration tests

## Acceptance Checklist

- ✅ POST /api/voice/twilio/inbound returns correct TwiML
- ✅ WebSocket can accept Twilio Media Streams connections
- ✅ Audio transcoding works correctly (μ-law → PCM)
- ✅ STT integration works (Whisper)
- ✅ Assistant response can be sent (MVP placeholder)
- ✅ Error handling and logging implemented
- ✅ Audit logs include call_sid, stream_sid, provider=twilio
- ✅ Session management (create, retrieve)
- ✅ Verification script passes all checks
