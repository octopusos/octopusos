---
status: accepted
date: 2026-02-01
decision-makers: AgentOS Voice Team
consulted: Security Team, Network Team
informed: All Developers
---

# ADR-017: Twilio Media Streams Integration

## Context

AgentOS Voice v0.1 provides local WebSocket-based voice communication for browser clients. To extend voice capabilities to traditional phone networks (PSTN), we need to integrate with a telephony provider. This ADR documents the decision to use Twilio Media Streams as the transport layer for phone-based voice sessions.

### Business Requirements

1. **PSTN Connectivity**: Enable agent communication via traditional phone calls
2. **Global Reach**: Support international phone numbers and carriers
3. **Reliability**: 99.95%+ uptime for voice infrastructure
4. **Scalability**: Handle concurrent calls without infrastructure overhead
5. **Compliance**: Meet telecommunication regulations (E911, CALEA, etc.)

### Technical Requirements

1. **Real-time Audio**: Bidirectional audio streaming with <500ms latency
2. **Audio Quality**: Toll-quality audio (8kHz, G.711 μ-law encoding)
3. **Integration**: Seamless integration with existing VoiceOS architecture
4. **Transcoding**: Efficient μ-law ↔ PCM conversion for STT/TTS processing
5. **Governance**: Policy-based access control and rate limiting

## Decision

We will integrate **Twilio Media Streams** as the primary transport provider for PSTN-based voice communication.

### Key Components

#### 1. Architecture Integration

```
┌─────────────────────────────────────────────────────────────┐
│                      VoiceOS Architecture                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐     ┌──────────────────┐                   │
│  │   Browser   │────▶│ Local Provider   │                   │
│  │  (WebRTC)   │     │  (WebSocket)     │                   │
│  └─────────────┘     └──────────────────┘                   │
│                                │                             │
│                                ▼                             │
│                      ┌──────────────────┐                   │
│                      │  VoiceService    │                   │
│                      │   (Core Logic)   │                   │
│                      └──────────────────┘                   │
│                                │                             │
│  ┌─────────────┐     ┌──────────────────┐                   │
│  │   Phone     │────▶│ Twilio Provider  │◀── This ADR       │
│  │   (PSTN)    │     │ (Media Streams)  │                   │
│  └─────────────┘     └──────────────────┘                   │
│                                │                             │
│                                ▼                             │
│                      ┌──────────────────┐                   │
│                      │  STT/TTS Engine  │                   │
│                      │    (Whisper)     │                   │
│                      └──────────────────┘                   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

#### 2. Audio Transcoding Pipeline

Twilio Media Streams uses **μ-law (G.711)** encoding at **8kHz** sample rate. Our internal audio processing (Whisper STT, OpenAI TTS) expects **PCM s16le** at **16kHz**. The provider handles transcoding:

```
Inbound (Phone → Agent):
  Twilio (μ-law, 8kHz)
    ↓ Decode μ-law → PCM s16
    ↓ Upsample 8kHz → 16kHz
  Internal (PCM s16le, 16kHz)
    ↓ Whisper STT
  Text transcript

Outbound (Agent → Phone):
  TTS audio (PCM s16le, 24kHz)
    ↓ Downsample 24kHz → 8kHz
    ↓ Encode PCM s16 → μ-law
  Twilio (μ-law, 8kHz)
```

#### 3. Twilio Media Streams Protocol

Twilio uses a **WebSocket-based protocol** with JSON messages:

**Event Types:**
- `start`: Stream initialization (provides call_sid, stream_sid)
- `media`: Audio payload (base64-encoded μ-law)
- `stop`: Stream termination
- `mark`: Synchronization points (for TTS alignment)

**Example Media Event:**
```json
{
  "event": "media",
  "sequenceNumber": "4",
  "media": {
    "track": "inbound",
    "chunk": "2",
    "timestamp": "5000",
    "payload": "base64-encoded-mulaw-audio"
  },
  "streamSid": "MZ1234567890abcdef"
}
```

#### 4. Call Flow

```
1. Inbound Call → Twilio
2. Twilio → POST /api/voice/twilio/inbound
3. AgentOS → Return TwiML with <Stream> directive
4. Twilio → Connect WebSocket to /api/voice/twilio/stream/{session_id}
5. AgentOS → Accept WebSocket, create VoiceSession
6. Twilio → Send "start" event with call_sid, stream_sid
7. Twilio ↔ AgentOS: Bidirectional audio streaming
   - Twilio sends "media" events (user speech)
   - AgentOS sends TTS audio (agent responses)
8. Call ends → Twilio sends "stop" event
9. AgentOS → Close WebSocket, terminate VoiceSession
```

#### 5. Governance and Security

**Risk Assessment:**
- **Provider Risk Tier**: `MEDIUM` (external PSTN connectivity)
- Escalates to `HIGH` with sensitive data, international calls, or recording

**Rate Limiting:**
- **Per-phone-number limit**: 10 calls/hour
- Prevents abuse and controls costs
- Configurable per project

**Admin Token Requirement:**
- High-risk operations (data access) require admin token
- Token format: `admin-{random_string}` (min 20 chars)
- Validated against secure token store

**Audit Trail:**
- All calls logged with call_sid, from_number, to_number
- Transcripts stored in audit database
- Policy verdicts recorded for compliance

## Alternatives Considered

### 1. Vonage Voice API (formerly Nexmo)

**Pros:**
- Similar WebSocket-based streaming
- Competitive pricing
- Good global coverage

**Cons:**
- Less mature Media Streams API
- Smaller ecosystem and community
- Fewer compliance certifications

**Decision:** Rejected due to maturity concerns.

### 2. Plivo Voice API

**Pros:**
- Lower pricing for some regions
- Good API documentation
- Similar capabilities

**Cons:**
- Less reliable uptime (99.9% vs Twilio's 99.95%)
- Limited enterprise support
- Smaller partner network

**Decision:** Rejected due to reliability requirements.

### 3. Self-hosted SIP Infrastructure (Asterisk/FreeSWITCH)

**Pros:**
- Complete control over infrastructure
- No per-minute charges
- Full customization

**Cons:**
- High operational overhead (DevOps, monitoring, scaling)
- Compliance burden (E911, CALEA, carrier agreements)
- Requires telephony expertise
- Capital investment in infrastructure

**Decision:** Rejected due to operational complexity and cost.

### 4. Telnyx Voice API

**Pros:**
- Developer-friendly API
- Real-time WebSocket streaming
- Competitive pricing

**Cons:**
- Newer company, less proven at scale
- Smaller global footprint
- Limited enterprise support

**Decision:** Rejected due to scale and support concerns.

## Consequences

### Positive

1. **Rapid Deployment**: Twilio handles infrastructure, enabling fast launch
2. **Reliability**: 99.95% SLA with proven track record
3. **Global Coverage**: 180+ countries, 80+ local numbers
4. **Compliance**: Twilio handles regulatory requirements (E911, CALEA)
5. **Scalability**: Pay-as-you-go model scales with usage
6. **Developer Experience**: Excellent documentation and SDKs
7. **Security**: Webhook signature verification, TLS encryption

### Negative

1. **Cost**: Per-minute charges (~$0.013-0.024/min for US calls)
2. **Vendor Lock-in**: Tight coupling to Twilio's API and pricing
3. **Latency**: Additional network hop adds ~50-100ms latency
4. **Audio Quality**: Limited to 8kHz (phone network constraint, not Twilio-specific)

### Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| **Cost Overrun** | Implement rate limiting (10 calls/hour/number), budget alerts, cost attribution by project |
| **Vendor Lock-in** | Design abstraction layer (`IVoiceTransportProvider`) to support multi-provider strategy |
| **Service Outage** | Monitor Twilio status page, implement graceful degradation, consider backup provider (future) |
| **Abuse** | Policy engine with rate limiting, phone number blacklist, admin token for high-risk operations |
| **Compliance** | Leverage Twilio's certifications (SOC 2, HIPAA, PCI DSS), implement audit trail |

### Performance Characteristics

**Expected Latency:**
- **E2E latency**: 400-600ms (PSTN network ~200ms + transcoding ~50ms + STT ~150ms)
- **Audio quality**: 8kHz, G.711 μ-law (standard phone quality)
- **Concurrent calls**: Limited by Twilio plan (100+ concurrent for standard account)

**Transcoding Performance:**
- **μ-law → PCM**: ~0.1ms per 100ms audio chunk (negligible)
- **PCM → μ-law**: ~0.1ms per 100ms audio chunk (negligible)
- **Upsampling (8kHz → 16kHz)**: Linear interpolation, ~0.2ms per 100ms chunk

### Integration Points

**Webhook Endpoints:**
- `POST /api/voice/twilio/inbound` - Inbound call webhook (returns TwiML)
- `WS /api/voice/twilio/stream/{session_id}` - Media Streams WebSocket

**Configuration:**
- `TWILIO_ACCOUNT_SID` - Twilio account identifier
- `TWILIO_AUTH_TOKEN` - API authentication token
- `TWILIO_PHONE_NUMBER` - Twilio phone number for outbound calls (future)

**Dependencies:**
- `twilio` Python package (for E2E tests and outbound calls)
- `numpy` (for μ-law transcoding)
- `websockets` (handled by FastAPI)

## Implementation Notes

### Phase 1: Inbound Calls (Current)
- ✅ Inbound call webhook (`/api/voice/twilio/inbound`)
- ✅ TwiML generation with `<Stream>` directive
- ✅ Media Streams WebSocket handler
- ✅ μ-law ↔ PCM transcoding
- ✅ VoiceSession creation with Twilio metadata
- ✅ STT integration (Whisper)
- ✅ Policy engine (rate limiting, risk assessment)

### Phase 2: Outbound Calls (Future)
- ⏳ Outbound call initiation via Twilio API
- ⏳ TTS audio streaming to caller
- ⏳ Call recording and storage
- ⏳ Call transfer and conference

### Phase 3: Advanced Features (Future)
- ⏳ Voice activity detection (VAD) for barge-in
- ⏳ Dual-channel audio (inbound + outbound separate tracks)
- ⏳ Call recording with consent management
- ⏳ SIP trunking for enterprise integration

## Related ADRs

- [ADR-013: Voice Communication Capability](ADR-013-voice-communication-capability.md) - Voice v0.1 architecture
- [ADR-014: Protocol Freeze v1](ADR-014-protocol-freeze-v1.md) - API stability guarantees

## References

- [Twilio Media Streams Documentation](https://www.twilio.com/docs/voice/media-streams)
- [Twilio TwiML Reference](https://www.twilio.com/docs/voice/twiml)
- [ITU-T G.711 Specification](https://www.itu.int/rec/T-REC-G.711/en) - μ-law encoding
- [VoiceOS Architecture Docs](../voice/README.md)

## Approval

- **Date**: 2026-02-01
- **Status**: Accepted
- **Decision Makers**: AgentOS Voice Team
- **Reviewers**: Security Team (approved), Network Team (approved)

---

*Last Updated: 2026-02-01*
*Next Review: 2026-05-01 (3 months)*
