# ADR-015: Voice Worker Sidecar - gRPC Architecture

**Status**: Accepted

**Date**: 2026-02-01

**Authors**: AgentOS Team

**Deciders**: Architecture Team, Voice Team

---

## Context

AgentOS is transitioning from Python 3.13 to Python 3.14 as its main runtime environment. However, critical voice processing libraries, particularly `faster-whisper` (used for Speech-to-Text), require Python 3.13 and are not yet compatible with Python 3.14.

### Problem Statement

We need to support voice processing capabilities (STT/TTS) while the main AgentOS process runs on Python 3.14. The voice processing must be:

1. **Low-latency**: Voice interactions require near-real-time processing (< 100ms total latency)
2. **Isolated**: Voice processing failures should not crash the main process
3. **Scalable**: Support multiple concurrent voice sessions (up to 10 simultaneously)
4. **Maintainable**: Clear separation of concerns between main process and voice processing

### Requirements

- Bidirectional audio streaming (client sends audio, receives STT/TTS events)
- Buffer protection to prevent memory exhaustion
- Health monitoring to detect sidecar failures
- Graceful degradation if sidecar is unavailable
- Cross-version Python compatibility (3.14 ↔ 3.13)

---

## Decision

We will implement a **Voice Worker Sidecar** architecture using **gRPC** for inter-process communication.

### Architecture Overview

```
┌─────────────────────────────────────┐
│   Main Process (Python 3.14)       │
│                                     │
│   ┌─────────────────────────────┐  │
│   │  VoiceWorkerClient          │  │
│   │  - Session management       │  │
│   │  - gRPC client              │  │
│   │  - Health monitoring        │  │
│   │  - Fallback logic           │  │
│   └─────────────┬───────────────┘  │
└─────────────────┼───────────────────┘
                  │ gRPC
                  │ (localhost:50051)
┌─────────────────┼───────────────────┐
│   Sidecar Process (Python 3.13)    │
│                                     │
│   ┌─────────────┴───────────────┐  │
│   │  VoiceWorkerServicer        │  │
│   │  - Audio streaming          │  │
│   │  - STT processing           │  │
│   │  - TTS generation           │  │
│   │  - Buffer management        │  │
│   └─────────────────────────────┘  │
│                                     │
│   ┌─────────────────────────────┐  │
│   │  faster-whisper             │  │
│   │  (Python 3.13 only)         │  │
│   └─────────────────────────────┘  │
└─────────────────────────────────────┘
```

### gRPC Service Definition

The `VoiceWorker` service provides four RPCs:

1. **CreateSession**: Unary call to create a voice session
2. **ProcessAudio**: Bidirectional streaming for audio processing
3. **StopSession**: Unary call to gracefully stop a session
4. **HealthCheck**: Unary call for liveness monitoring

### Key Design Choices

1. **gRPC over HTTP/REST**: Strong typing, bidirectional streaming, low latency
2. **Separate process, not thread**: True isolation, independent crash domains
3. **Client-managed lifecycle**: Main process starts/stops sidecar automatically
4. **Fallback to embedded**: If sidecar fails, fall back to embedded mode (best effort)
5. **10MB buffer limit per session**: Prevents memory exhaustion from malicious/broken clients
6. **10 concurrent session limit**: Prevents resource exhaustion on single sidecar

---

## Alternatives Considered

### Alternative 1: HTTP/REST with Server-Sent Events (SSE)

**Pros**:
- Simpler debugging (curl, browser dev tools)
- More familiar to web developers
- No additional tooling (no protoc compilation)

**Cons**:
- Higher latency due to HTTP overhead
- No bidirectional streaming (SSE is server→client only)
- Weak typing (JSON schemas not enforced at compile time)
- More complex error handling

**Decision**: Rejected due to latency requirements and lack of bidirectional streaming.

---

### Alternative 2: WebSocket

**Pros**:
- Bidirectional streaming
- Lower latency than HTTP/REST
- Wide adoption and tooling

**Cons**:
- Custom protocol required (no standardized schema)
- Manual serialization/deserialization
- No built-in flow control
- Weaker type safety

**Decision**: Rejected due to lack of standardized schema and type safety.

---

### Alternative 3: Shared Memory / Named Pipes

**Pros**:
- Lowest possible latency (no network stack)
- Native OS support

**Cons**:
- Platform-specific (complex cross-platform support)
- No built-in serialization (manual protocol design)
- Complex buffer management
- Difficult to version and evolve protocol
- Hard to debug

**Decision**: Rejected due to complexity and platform dependence.

---

### Alternative 4: Embedded Mode Only (No Sidecar)

**Pros**:
- Simplest architecture (no IPC)
- No process management overhead

**Cons**:
- Blocks migration to Python 3.14
- Voice processing crashes crash main process
- Cannot isolate resource usage
- Difficult to scale (all voice sessions in main process)

**Decision**: Rejected as it blocks Python 3.14 migration.

---

## Consequences

### Positive

1. **Low Latency**: gRPC's HTTP/2 foundation and binary serialization achieve < 50ms roundtrip latency in testing
2. **Type Safety**: Protobuf schemas provide compile-time type checking and auto-generated code
3. **Isolation**: Sidecar crashes do not affect main process
4. **Scalability**: Can run multiple sidecars if needed (future work)
5. **Streaming**: Native bidirectional streaming simplifies audio pipeline
6. **Versioning**: Protobuf's backward/forward compatibility eases protocol evolution
7. **Cross-Language**: gRPC supports future migration to other languages (Rust, Go, etc.)

### Negative

1. **Complexity**: Adds process management, health checks, and fallback logic
2. **Debugging**: gRPC errors can be cryptic; requires specialized tools (e.g., grpcurl)
3. **Dependencies**: Requires `grpcio` and `protobuf` packages in both processes
4. **Latency Overhead**: Still slower than shared memory (but acceptable for voice use case)
5. **Compilation Step**: Requires `protoc` to generate Python stubs from `.proto` files
6. **Port Management**: Must manage port conflicts if running multiple instances

### Mitigation Strategies

- **Debugging**: Add structured logging at gRPC boundaries; provide `grpcurl` examples in runbook
- **Fallback**: Implement automatic fallback to embedded mode if sidecar fails to start
- **Health Monitoring**: Continuous health checks (every 10s) to detect sidecar failures early
- **Documentation**: Comprehensive runbook for operators (see SIDECAR_RUNBOOK.md)

---

## Performance Expectations

Based on testing and gRPC benchmarks:

| Metric                  | Target      | Observed (Test) |
|-------------------------|-------------|-----------------|
| Roundtrip Latency       | < 50ms      | 15-30ms         |
| Throughput              | > 100 msg/s | 200+ msg/s      |
| Memory per Session      | < 10MB      | 2-8MB           |
| Max Concurrent Sessions | 10          | 10 (enforced)   |
| Startup Time            | < 5s        | 2-3s            |
| Shutdown Time (graceful)| < 5s        | 1-2s            |

---

## Implementation Notes

### Protobuf Schema

See `agentos/core/communication/voice/sidecar/voice_worker.proto` for full schema.

Key messages:
- `CreateSessionRequest`: Session configuration
- `AudioChunk`: Audio data with metadata (sample rate, channels, timestamp)
- `AudioEvent`: STT results, TTS chunks, errors
- `HealthCheckResponse`: Status, active sessions, memory usage, uptime

### gRPC Stubs Generation

Generate Python stubs with:

```bash
python -m grpc_tools.protoc \
  -I agentos/core/communication/voice/sidecar \
  --python_out=. \
  --grpc_python_out=. \
  agentos/core/communication/voice/sidecar/voice_worker.proto
```

### Process Management

- **Startup**: Main process spawns sidecar via `subprocess.Popen`, waits for health check
- **Shutdown**: Main process sends SIGTERM, waits 5s, sends SIGKILL if needed
- **Crash Recovery**: Health check detects failure, logs error, falls back to embedded mode

---

## Security Considerations

1. **Local-only Communication**: gRPC server binds to `localhost` only (no network exposure)
2. **No Authentication**: Not needed for local IPC (process isolation via OS)
3. **Buffer Limits**: 10MB per session prevents memory exhaustion attacks
4. **Session Limits**: Max 10 concurrent sessions prevents resource exhaustion

**Future Work**: If sidecar needs to run on remote host, add TLS and authentication.

---

## Testing Strategy

See test files:
- `tests/unit/communication/voice/test_grpc_session_creation.py` (10+ tests)
- `tests/unit/communication/voice/test_audio_streaming.py` (11+ tests)
- `tests/unit/communication/voice/test_health_check.py` (13+ tests)
- `tests/unit/communication/voice/test_fallback_logic.py` (12+ tests)
- `tests/integration/voice/test_sidecar_lifecycle.py` (12+ tests)
- `tests/integration/voice/test_main_to_sidecar_roundtrip.py` (10+ tests)

---

## References

- [gRPC Documentation](https://grpc.io/docs/)
- [Protocol Buffers Guide](https://developers.google.com/protocol-buffers)
- [faster-whisper GitHub](https://github.com/guillaumekln/faster-whisper)
- ADR-013: Voice Communication Capability
- SIDECAR_RUNBOOK.md: Operational guide

---

## Changelog

| Date       | Change                                      |
|------------|---------------------------------------------|
| 2026-02-01 | Initial version - gRPC architecture decided |
