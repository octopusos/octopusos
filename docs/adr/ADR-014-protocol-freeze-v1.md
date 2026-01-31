# ADR-014: CommunicationOS Protocol Freeze (v1)

## Status
✅ **ACCEPTED & FROZEN** - 2026-02-01

**Authors**: AgentOS Team
**Semantic Freeze**: YES - This is a protocol-level contract

## Context

### Background

AgentOS CommunicationOS has successfully completed 7 channel implementations across diverse communication platforms:
- Slack (enterprise messaging)
- Telegram (bot platform)
- Discord (community platform)
- Email (SMTP/IMAP)
- SMS (Twilio)
- Voice (WebRTC/STT/TTS)
- WhatsApp (future implementation ready)

Through these implementations, the core protocol models (`InboundMessage`, `OutboundMessage`) and routing logic (`SessionRouter`) have been validated across:
- Real-time messaging (Slack, Telegram, Discord)
- Asynchronous messaging (Email, SMS)
- Rich media support (Voice, attachments)
- Various session scoping strategies (USER, USER_CONVERSATION)

### Business Drivers

1. **Ecosystem Stability**: Third-party channel adapters need stable protocols
2. **Community Extensions**: External developers building custom channels need guarantees
3. **Production Readiness**: Protocol freeze signals production-grade maturity
4. **Backward Compatibility**: Protect existing channel implementations from breaking changes

### Problem Statement

Without a protocol freeze:
- Third-party developers risk adapters breaking on AgentOS updates
- Community contributions hesitate due to uncertainty
- Internal changes may inadvertently break existing channels
- Lack of clear extension guidelines

## Decision

We are **freezing the CommunicationOS Protocol v1** effective 2026-02-01. This freeze covers:

### Frozen Scope

#### 1. InboundMessage v1 (FROZEN)

**Core Fields** (MUST NOT be removed or change semantics):

```python
@dataclass
class InboundMessage(BaseModel):
    # Identity fields
    channel_id: str              # Channel identifier (e.g., "slack_workspace_abc")
    user_key: str                # User identifier within channel (e.g., "U12345")
    conversation_key: str        # Conversation/thread identifier
    message_id: str              # Platform-specific unique message ID

    # Content fields
    timestamp: datetime          # Message timestamp (UTC-aware)
    type: MessageType            # TEXT, IMAGE, AUDIO, VIDEO, FILE, LOCATION, INTERACTIVE, SYSTEM
    text: Optional[str]          # Text content (max 10000 chars)

    # Structured data
    attachments: List[Attachment]     # Media attachments
    location: Optional[Location]      # Geographic location data

    # Extensibility
    raw: Dict[str, Any]          # Platform-specific raw message data
    metadata: Dict[str, Any]     # Extension point for adapter-specific metadata
```

**Frozen Semantics**:
- `channel_id` + `user_key` + `conversation_key`: Session routing identifiers
- `message_id`: Globally unique within channel, used for deduplication
- `timestamp`: MUST be timezone-aware UTC (per ADR-011 Time Contract)
- `type`: Enum values are frozen (see MessageType below)
- `metadata`: Safe extension point (adapters can add custom fields)
- `raw`: Safe extension point (preserves platform-specific data)

#### 2. OutboundMessage v1 (FROZEN)

**Core Fields** (MUST NOT be removed or change semantics):

```python
@dataclass
class OutboundMessage(BaseModel):
    # Routing fields
    channel_id: str              # Target channel
    user_key: str                # Target user
    conversation_key: str        # Target conversation/thread

    # Reply context
    reply_to_message_id: Optional[str]  # ID of message being replied to

    # Content fields
    type: MessageType            # Message type to send
    text: Optional[str]          # Text content (max 10000 chars)

    # Structured data
    attachments: List[Attachment]     # Media to send
    location: Optional[Location]      # Location to send

    # Extensibility
    metadata: Dict[str, Any]     # Extension point (priority, delivery options, etc.)
```

**Frozen Semantics**:
- `channel_id` + `user_key` + `conversation_key`: Must match InboundMessage routing
- `reply_to_message_id`: Optional threading support
- `type`: Must match InboundMessage MessageType enum
- `metadata`: Safe extension point for adapter-specific delivery options

#### 3. MessageType Enum (FROZEN)

```python
class MessageType(str, Enum):
    TEXT = "text"                    # Plain text messages
    IMAGE = "image"                  # Image attachments
    AUDIO = "audio"                  # Audio messages/voice notes
    VIDEO = "video"                  # Video files
    FILE = "file"                    # Document/file attachments
    LOCATION = "location"            # Geographic location
    INTERACTIVE = "interactive"      # Rich UI (buttons, menus, forms)
    SYSTEM = "system"               # System notifications/events
```

**Frozen Values**: These 8 message types MUST NOT be removed. New types may be added with community RFC.

#### 4. Attachment and Location Models (FROZEN)

```python
@dataclass
class Attachment(BaseModel):
    type: AttachmentType         # IMAGE, AUDIO, VIDEO, DOCUMENT, LOCATION, CONTACT, STICKER, INTERACTIVE
    url: Optional[str]           # URL to access media
    mime_type: Optional[str]     # MIME type
    filename: Optional[str]      # Original filename
    size_bytes: Optional[int]    # File size
    metadata: Dict[str, Any]     # Platform-specific metadata

@dataclass
class Location(BaseModel):
    latitude: float              # Latitude coordinate
    longitude: float             # Longitude coordinate
    address: Optional[str]       # Human-readable address
    name: Optional[str]          # Location name/label
```

#### 5. SessionRouter Rules (FROZEN)

**Session Scope Computation**:

```python
class SessionScope(str, Enum):
    USER = "user"                          # One session per user across all conversations
    USER_CONVERSATION = "user_conversation"  # One session per user-conversation pair

# Frozen routing logic:
def compute_session_lookup_key(message: InboundMessage, scope: SessionScope) -> str:
    if scope == SessionScope.USER:
        # Format: "{channel_id}:{user_key}"
        return f"{message.channel_id}:{message.user_key}"

    elif scope == SessionScope.USER_CONVERSATION:
        # Format: "{channel_id}:{user_key}:{conversation_key}"
        return f"{message.channel_id}:{message.user_key}:{message.conversation_key}"
```

**Frozen Semantics**:
- `USER`: Single persistent session per user (e.g., Email, SMS)
- `USER_CONVERSATION`: Separate sessions per conversation (e.g., Slack channels, Telegram groups)
- Key format: Colon-delimited, deterministic, reversible
- Channel manifest specifies scope (see ChannelManifest.session_scope)

### Change Policy

#### ✅ ALLOWED: Non-Breaking Extensions

**1. Add New Optional Fields** (with defaults):
```python
# OK: New optional field with default
class InboundMessage(BaseModel):
    # ... existing fields ...
    priority: Optional[str] = None  # New in v1.1
```

**2. Extend metadata/raw Dictionaries**:
```python
# OK: Adapter-specific metadata
inbound_msg = InboundMessage(
    # ... required fields ...
    metadata={
        "slack_thread_ts": "1234567890.123456",  # Slack-specific
        "telegram_forward_from": "user_id",      # Telegram-specific
    }
)
```

**3. Add New MessageType Values** (via RFC):
```python
# OK: New message type (requires community RFC)
class MessageType(str, Enum):
    # ... existing 8 types ...
    POLL = "poll"  # New in v1.2 (after RFC approval)
```

**4. Extend Adapter/Provider/Manifest**:
```python
# OK: Channel-specific extensions via manifest
manifest = ChannelManifest(
    # ... core fields ...
    metadata={
        "supports_reactions": True,
        "max_attachment_size_mb": 25,
        "custom_emoji_enabled": True,
    }
)
```

#### ❌ FORBIDDEN: Breaking Changes

**1. Remove Frozen Fields**:
```python
# ❌ FORBIDDEN: Remove channel_id
class InboundMessage(BaseModel):
    # channel_id: str  <- Cannot remove!
    user_key: str
    # ...
```

**2. Change Field Semantics**:
```python
# ❌ FORBIDDEN: Change timestamp to naive datetime
timestamp: datetime  # Was: timezone-aware UTC
                    # Now: naive datetime <- BREAKING!
```

**3. Change Field Types**:
```python
# ❌ FORBIDDEN: Change user_key type
user_key: int  # Was: str <- BREAKING!
```

**4. Change SessionRouter Logic**:
```python
# ❌ FORBIDDEN: Change lookup key format
# Was: "{channel_id}:{user_key}"
# Now: "{channel_id}#{user_key}" <- BREAKING!
```

**5. Remove MessageType Values**:
```python
# ❌ FORBIDDEN: Remove TEXT message type
class MessageType(str, Enum):
    # TEXT = "text"  <- Cannot remove!
    IMAGE = "image"
```

**6. Make Optional Fields Required**:
```python
# ❌ FORBIDDEN: Remove default value
text: str  # Was: Optional[str] <- BREAKING!
```

#### ⚠️ CAUTION: Requires RFC + Compatibility Verification

**1. Add New Required Fields**:
- MUST provide migration path for old adapters
- MUST document in release notes
- MUST version protocol (e.g., v1.1)
- Example: Adding `language_code: str` would require RFC

**2. Add New Enum Values**:
- MUST ensure backward compatibility (old code ignores unknown values)
- MUST document fallback behavior
- Example: New MessageType.POLL requires RFC defining TEXT fallback

**3. Change Validation Rules**:
- MUST not break existing valid messages
- Example: Changing `text` max length from 10000 to 5000 would be BREAKING

### Extension Strategy

**Priority Order for New Requirements**:

1. **Level 1 - Adapter Layer** (Preferred):
   - Use `metadata` dictionary in InboundMessage/OutboundMessage
   - Channel-specific logic in adapter implementation
   - Example: Slack thread_ts, Telegram forward info

2. **Level 2 - Provider Layer**:
   - New API mappings in provider implementation
   - Example: WhatsApp template messages, Telegram inline keyboards

3. **Level 3 - Manifest Layer**:
   - New configuration fields in ChannelManifest
   - Example: Webhook verification settings, rate limits

4. **Level 4 - Protocol Layer** (Requires RFC):
   - New optional fields in InboundMessage/OutboundMessage
   - New MessageType enum values
   - Must have community consensus

## Consequences

### Positive ✅

1. **Ecosystem Stability**
   - Third-party developers can build adapters with confidence
   - Community contributions won't break on updates
   - AgentOS can be adopted as a standard

2. **Backward Compatibility**
   - Existing 7 channels guaranteed to keep working
   - Future AgentOS versions won't break adapters
   - Smooth upgrade path for users

3. **Clear Extension Model**
   - Developers know where to add custom logic
   - `metadata` provides safe extension point
   - Manifest-driven configuration is flexible

4. **Production Readiness Signal**
   - Protocol freeze indicates maturity
   - Enterprise adoption confidence
   - Marketplace can develop around stable API

5. **Reduced Maintenance Burden**
   - Core protocol doesn't churn
   - Focus innovation on adapters/providers
   - Clearer code review criteria

### Negative ⚠️

1. **Reduced Flexibility**
   - Can't quickly pivot protocol design
   - Need RFC process for changes
   - May accumulate technical debt in frozen design

2. **Extension Complexity**
   - Working around frozen fields may be awkward
   - `metadata` patterns can become inconsistent
   - Need strong conventions to avoid chaos

3. **Migration Burden**
   - If protocol v2 needed, requires migration path
   - Community adapters may lag on updates
   - Versioning complexity

### Mitigation Strategies

1. **RFC Process for Protocol Changes**
   - Documented RFC template
   - Community review period (14 days minimum)
   - Backward compatibility analysis required
   - Breaking changes require major version bump (v2.0)

2. **Metadata Conventions**
   - Document common metadata patterns
   - Provide adapter examples
   - Linting for metadata best practices

3. **Protocol Test Suite**
   - Automated tests detect breaking changes
   - Contract tests for all frozen semantics
   - CI enforces protocol stability

4. **Version Negotiation** (Future):
   - Adapters declare supported protocol version
   - Router can handle multiple protocol versions
   - Graceful degradation for old adapters

## Implementation

### Enforcement Mechanisms

#### 1. Protocol Contract Tests

Location: `/Users/pangge/PycharmProjects/AgentOS/tests/protocol/test_frozen_protocol_v1.py`

Tests verify:
- InboundMessage has all frozen fields
- OutboundMessage has all frozen fields
- Field types match frozen specification
- SessionRouter produces frozen key formats
- MessageType enum has all frozen values
- New optional fields have default values

See implementation section below for full test suite.

#### 2. Documentation Updates

**Files Updated**:
- `CONTRIBUTING.md`: Protocol freeze policy
- `docs/CHANNEL_ADAPTER_CONTRIBUTION_GUIDE.md`: Extension guidelines
- `agentos/communicationos/models.py`: Frozen warning header
- `agentos/communicationos/session_router.py`: Frozen warning header

**Markers**:
- Code comments: `# FROZEN v1 - See ADR-014`
- Docstrings: `⚠️ PROTOCOL FROZEN (v1) - Changes require RFC`
- Git tags: `protocol-v1-freeze`

#### 3. Code Review Checklist

PRs touching frozen files must verify:
- [ ] No frozen fields removed
- [ ] No frozen field types changed
- [ ] No frozen field semantics changed
- [ ] New fields are optional with defaults
- [ ] SessionRouter logic unchanged
- [ ] MessageType enum values unchanged
- [ ] Changes documented in ADR revision

#### 4. CI Gates

Add to `.github/workflows/protocol-freeze-check.yml`:
```yaml
- name: Protocol Freeze Contract
  run: |
    pytest tests/protocol/test_frozen_protocol_v1.py -v
```

### Migration Path (If v2 Needed)

If breaking changes become necessary:

1. **Declare Protocol v2**:
   - New ADR documenting v2 changes
   - Version field in InboundMessage/OutboundMessage
   - 6-month deprecation notice for v1

2. **Dual Protocol Support**:
   - Router handles both v1 and v2
   - Adapters declare supported versions
   - Automatic fallback for old adapters

3. **Community Communication**:
   - Blog post announcing v2
   - Migration guide with code examples
   - Support channel for adapter authors

## Testing

### Test Coverage

**Unit Tests**:
- Field presence verification
- Type checking
- Enum value validation
- SessionRouter key format
- Default value verification

**Integration Tests**:
- Round-trip message serialization
- Cross-adapter compatibility
- Session routing consistency

**Contract Tests**:
- JSON schema validation
- API compatibility checks
- Breaking change detection

### Test Implementation

See `/Users/pangge/PycharmProjects/AgentOS/tests/protocol/test_frozen_protocol_v1.py` for complete test suite.

Key test scenarios:
1. `test_inbound_message_frozen_fields()`: Verify all frozen fields exist
2. `test_outbound_message_frozen_fields()`: Verify all frozen fields exist
3. `test_message_type_frozen_values()`: Verify enum values unchanged
4. `test_session_router_frozen_logic()`: Verify key computation unchanged
5. `test_new_fields_have_defaults()`: Verify backward compatibility
6. `test_field_type_stability()`: Verify types unchanged

## References

### Related ADRs

- [ADR-011: Time & Timestamp Contract](./ADR-011-time-timestamp-contract.md) - Timestamp handling in messages
- [ADR-012: Memory Capability Contract](./ADR-012-memory-capability-contract.md) - Capability contract pattern
- [ADR-013: Voice Communication Capability](./ADR-013-voice-communication-capability.md) - Voice channel implementation

### Internal Documentation

- [CommunicationOS Models](../../agentos/communicationos/models.py) - Frozen protocol models
- [Session Router](../../agentos/communicationos/session_router.py) - Frozen routing logic
- [Channel Manifest](../../agentos/communicationos/manifest.py) - Manifest specification
- [Channel Adapter Guide](../CHANNEL_ADAPTER_CONTRIBUTION_GUIDE.md) - Extension guidelines

### Implementation Evidence

- **Slack Adapter**: `agentos/communicationos/channels/slack/`
- **Telegram Adapter**: `agentos/communicationos/channels/telegram/`
- **Discord Adapter**: `agentos/communicationos/channels/discord/`
- **Email Adapter**: `agentos/communicationos/channels/email/`
- **SMS Adapter**: `agentos/communicationos/channels/sms/`
- **Voice Adapter**: `agentos/communicationos/channels/voice/`

All 7 adapters validated against frozen protocol.

### External Resources

- [Semantic Versioning](https://semver.org/) - Version numbering strategy
- [API Evolution Patterns](https://www.apievolution.com/) - API compatibility best practices
- [Protocol Buffers](https://developers.google.com/protocol-buffers/docs/overview) - Inspiration for extension model

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-01 | AgentOS Team | Initial protocol freeze |

---

## Appendix: Quick Reference

### Frozen Fields Checklist

**InboundMessage (9 core fields)**:
- ✅ `channel_id: str`
- ✅ `user_key: str`
- ✅ `conversation_key: str`
- ✅ `message_id: str`
- ✅ `timestamp: datetime`
- ✅ `type: MessageType`
- ✅ `text: Optional[str]`
- ✅ `attachments: List[Attachment]`
- ✅ `metadata: Dict[str, Any]`

**OutboundMessage (8 core fields)**:
- ✅ `channel_id: str`
- ✅ `user_key: str`
- ✅ `conversation_key: str`
- ✅ `reply_to_message_id: Optional[str]`
- ✅ `type: MessageType`
- ✅ `text: Optional[str]`
- ✅ `attachments: List[Attachment]`
- ✅ `metadata: Dict[str, Any]`

**MessageType (8 values)**:
- ✅ TEXT, IMAGE, AUDIO, VIDEO, FILE, LOCATION, INTERACTIVE, SYSTEM

**SessionRouter (2 scopes)**:
- ✅ USER: `{channel_id}:{user_key}`
- ✅ USER_CONVERSATION: `{channel_id}:{user_key}:{conversation_key}`

### Extension Decision Tree

```
Need to add channel-specific feature?
│
├─ Is it message-level metadata? → Use InboundMessage.metadata / OutboundMessage.metadata
│
├─ Is it channel configuration? → Use ChannelManifest.metadata
│
├─ Is it provider-specific API? → Implement in Provider layer
│
├─ Is it core protocol field? → Requires RFC + Community Review
│
└─ Is it breaking change? → Requires Protocol v2 (major version bump)
```

---

**⚠️ PROTOCOL FROZEN NOTICE**

This protocol is frozen as of 2026-02-01. Any modifications to frozen fields require:
1. RFC submitted to community
2. 14-day review period
3. Backward compatibility analysis
4. Major version bump if breaking

For questions, contact: dev@seacow.tech
