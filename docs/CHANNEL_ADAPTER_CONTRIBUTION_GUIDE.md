# Channel Adapter Contribution Guide

**CommunicationOS Protocol v1 - Frozen 2026-02-01**

This guide helps you contribute new channel adapters to AgentOS CommunicationOS while respecting the frozen protocol (ADR-014).

## Table of Contents

- [Protocol Freeze Overview](#protocol-freeze-overview)
- [Quick Start](#quick-start)
- [Adapter Architecture](#adapter-architecture)
- [Extension Points](#extension-points)
- [Implementation Checklist](#implementation-checklist)
- [Testing Requirements](#testing-requirements)
- [Submission Process](#submission-process)

---

## Protocol Freeze Overview

### ⚠️ What is Frozen?

As of 2026-02-01, the following are **FROZEN** (see [ADR-014](adr/ADR-014-protocol-freeze-v1.md)):

**InboundMessage v1**:
- `channel_id`, `user_key`, `conversation_key`, `message_id`
- `timestamp`, `type`, `text`
- `attachments`, `location`, `raw`, `metadata`

**OutboundMessage v1**:
- `channel_id`, `user_key`, `conversation_key`
- `reply_to_message_id`, `type`, `text`
- `attachments`, `location`, `metadata`

**MessageType Enum** (8 values):
- TEXT, IMAGE, AUDIO, VIDEO, FILE, LOCATION, INTERACTIVE, SYSTEM

**SessionRouter Key Formats**:
- USER: `{channel_id}:{user_key}`
- USER_CONVERSATION: `{channel_id}:{user_key}:{conversation_key}`

### ✅ What Can You Extend?

You **CAN** extend via:
1. **Metadata Dictionary**: Add custom fields to `InboundMessage.metadata` and `OutboundMessage.metadata`
2. **Channel Manifest**: Add configuration fields in `ChannelManifest`
3. **Adapter Logic**: Custom validation, transformation, and error handling
4. **Provider Layer**: Platform-specific API mappings

You **CANNOT**:
- Remove or rename frozen fields
- Change frozen field types or semantics
- Modify SessionRouter key formats
- Change MessageType enum values

---

## Quick Start

### 1. Choose Your Channel

Identify the messaging platform you want to integrate:
- Real-time messaging (e.g., Discord, Matrix)
- Team collaboration (e.g., Microsoft Teams, Google Chat)
- SMS/MMS gateways (e.g., Nexmo, MessageBird)
- Social platforms (e.g., Facebook Messenger, Instagram)
- Custom enterprise systems

### 2. Create Channel Structure

```bash
# Create channel directory
mkdir -p agentos/communicationos/channels/your_channel/

# Create required files
touch agentos/communicationos/channels/your_channel/__init__.py
touch agentos/communicationos/channels/your_channel/adapter.py
touch agentos/communicationos/channels/your_channel/provider.py
touch agentos/communicationos/channels/your_channel/manifest.py
```

### 3. Implement Core Components

See [Adapter Architecture](#adapter-architecture) below for detailed implementation.

---

## Adapter Architecture

### Component Overview

```
your_channel/
├── __init__.py         # Package exports
├── manifest.py         # Channel manifest definition
├── adapter.py          # Protocol adapter (InboundMessage/OutboundMessage)
├── provider.py         # Platform API client
└── webhook.py          # Optional: Webhook handler
```

### 1. Manifest Definition

**File**: `manifest.py`

```python
from agentos.communicationos.manifest import (
    ChannelManifest,
    SessionScope,
    ChannelCapability,
    SecurityDefaults,
    SecurityMode,
    ConfigField,
    SetupStep,
)

def get_manifest() -> ChannelManifest:
    """Return channel manifest."""
    return ChannelManifest(
        id="your_channel",
        name="Your Channel",
        icon="your_icon",  # Font Awesome icon name or URL
        description="Short description of your channel",
        long_description="Detailed setup instructions...",
        version="1.0.0",
        provider="Provider Name",
        docs_url="https://docs.yourchannel.com",

        # Configuration fields (shown in WebUI setup wizard)
        required_config_fields=[
            ConfigField(
                name="api_key",
                label="API Key",
                type="password",
                required=True,
                secret=True,
                help_text="Your API key from channel dashboard",
            ),
            ConfigField(
                name="workspace_id",
                label="Workspace ID",
                type="text",
                required=True,
                placeholder="ws-123456",
            ),
        ],

        # Webhook paths (if your channel uses webhooks)
        webhook_paths=["/webhook/your_channel"],

        # Session scope (choose one)
        session_scope=SessionScope.USER_CONVERSATION,
        # USER: One session per user (e.g., Email, SMS)
        # USER_CONVERSATION: One session per conversation (e.g., Slack, Discord)

        # Capabilities your channel supports
        capabilities=[
            ChannelCapability.INBOUND_TEXT,
            ChannelCapability.OUTBOUND_TEXT,
            ChannelCapability.INBOUND_IMAGE,
            ChannelCapability.OUTBOUND_IMAGE,
            # Add others as supported
        ],

        # Security settings
        security_defaults=SecurityDefaults(
            mode=SecurityMode.CHAT_ONLY,
            allow_execute=False,
            rate_limit_per_minute=20,
            retention_days=7,
            require_signature=True,
        ),

        # Setup wizard steps
        setup_steps=[
            SetupStep(
                title="Create API Account",
                description="Sign up for Your Channel API access",
                instruction="1. Go to https://yourchannel.com/api\n2. Create new application...",
                checklist=[
                    "Created API account",
                    "Generated API key",
                    "Noted workspace ID",
                ],
            ),
            # Add more steps...
        ],
    )
```

### 2. Provider Implementation

**File**: `provider.py`

```python
from typing import Dict, Any, Optional
import httpx

class YourChannelProvider:
    """API client for Your Channel platform.

    Handles all platform-specific API calls.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize provider with configuration.

        Args:
            config: Channel configuration from manifest
        """
        self.api_key = config["api_key"]
        self.workspace_id = config["workspace_id"]
        self.base_url = "https://api.yourchannel.com/v1"
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )

    async def send_message(
        self,
        user_id: str,
        conversation_id: str,
        text: str,
        reply_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a text message.

        Args:
            user_id: Target user identifier
            conversation_id: Target conversation identifier
            text: Message text content
            reply_to: Optional message ID to reply to

        Returns:
            API response with message_id
        """
        payload = {
            "workspace_id": self.workspace_id,
            "conversation_id": conversation_id,
            "text": text,
        }
        if reply_to:
            payload["reply_to"] = reply_to

        response = await self.client.post(
            f"{self.base_url}/messages",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def send_image(
        self,
        user_id: str,
        conversation_id: str,
        image_url: str,
        caption: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an image message.

        Args:
            user_id: Target user identifier
            conversation_id: Target conversation identifier
            image_url: URL of image to send
            caption: Optional caption text

        Returns:
            API response with message_id
        """
        payload = {
            "workspace_id": self.workspace_id,
            "conversation_id": conversation_id,
            "image_url": image_url,
        }
        if caption:
            payload["text"] = caption

        response = await self.client.post(
            f"{self.base_url}/messages",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Clean up resources."""
        await self.client.aclose()
```

### 3. Adapter Implementation

**File**: `adapter.py`

```python
from typing import Dict, Any
from datetime import datetime, timezone

from agentos.communicationos.models import (
    InboundMessage,
    OutboundMessage,
    MessageType,
    Attachment,
    AttachmentType,
)
from agentos.core.time import utc_now
from .provider import YourChannelProvider


class YourChannelAdapter:
    """Adapter between Your Channel platform and AgentOS protocol.

    Converts platform-specific messages to/from frozen protocol models.
    """

    def __init__(self, channel_id: str, config: Dict[str, Any]):
        """Initialize adapter.

        Args:
            channel_id: Unique channel instance ID
            config: Channel configuration
        """
        self.channel_id = channel_id
        self.config = config
        self.provider = YourChannelProvider(config)

    def to_inbound(self, platform_message: Dict[str, Any]) -> InboundMessage:
        """Convert platform message to InboundMessage.

        ⚠️ FROZEN v1 - See ADR-014
        Must populate all frozen required fields.
        Use metadata for platform-specific fields.

        Args:
            platform_message: Raw message from Your Channel API

        Returns:
            Standardized InboundMessage
        """
        # Extract required fields (adapt to your platform's structure)
        message_type = self._determine_message_type(platform_message)

        # Build metadata with platform-specific fields
        metadata = {
            # Add any platform-specific fields here
            "platform": "your_channel",
            "workspace_id": self.config["workspace_id"],
            # Example: Thread/reply information
            "thread_id": platform_message.get("thread_id"),
            # Example: User profile info
            "user_display_name": platform_message.get("user", {}).get("name"),
        }

        # Handle attachments
        attachments = []
        if "attachments" in platform_message:
            for att in platform_message["attachments"]:
                attachments.append(Attachment(
                    type=AttachmentType(att["type"]),
                    url=att["url"],
                    mime_type=att.get("mime_type"),
                    filename=att.get("filename"),
                    size_bytes=att.get("size"),
                    metadata=att.get("metadata", {}),
                ))

        return InboundMessage(
            channel_id=self.channel_id,
            user_key=platform_message["user_id"],
            conversation_key=platform_message["conversation_id"],
            message_id=platform_message["message_id"],
            timestamp=self._parse_timestamp(platform_message["timestamp"]),
            type=message_type,
            text=platform_message.get("text"),
            attachments=attachments,
            raw=platform_message,  # Preserve original for debugging
            metadata=metadata,
        )

    async def send_outbound(self, message: OutboundMessage) -> str:
        """Send OutboundMessage to platform.

        ⚠️ FROZEN v1 - See ADR-014
        Must handle all frozen MessageType values.
        Use message.metadata for delivery options.

        Args:
            message: Standardized OutboundMessage

        Returns:
            Platform message ID
        """
        if message.type == MessageType.TEXT:
            response = await self.provider.send_message(
                user_id=message.user_key,
                conversation_id=message.conversation_key,
                text=message.text,
                reply_to=message.reply_to_message_id,
            )
            return response["message_id"]

        elif message.type == MessageType.IMAGE:
            if not message.attachments:
                raise ValueError("IMAGE message must have attachments")

            image_att = message.attachments[0]
            response = await self.provider.send_image(
                user_id=message.user_key,
                conversation_id=message.conversation_key,
                image_url=image_att.url,
                caption=message.text,
            )
            return response["message_id"]

        # Add handlers for other MessageType values...
        else:
            raise NotImplementedError(
                f"MessageType.{message.type.name} not yet supported by this adapter"
            )

    def _determine_message_type(self, platform_message: Dict[str, Any]) -> MessageType:
        """Determine MessageType from platform message.

        Maps platform-specific types to frozen MessageType enum.
        """
        if platform_message.get("image_url"):
            return MessageType.IMAGE
        elif platform_message.get("audio_url"):
            return MessageType.AUDIO
        elif platform_message.get("video_url"):
            return MessageType.VIDEO
        elif platform_message.get("file_url"):
            return MessageType.FILE
        else:
            return MessageType.TEXT

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse platform timestamp to UTC-aware datetime.

        ⚠️ Time Contract (ADR-011): MUST return timezone-aware UTC datetime.
        """
        # Adapt to your platform's timestamp format
        # Example: ISO 8601
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc)

    async def close(self):
        """Clean up resources."""
        await self.provider.close()
```

---

## Extension Points

### 1. Metadata Dictionary (Recommended)

Use `metadata` for platform-specific fields:

```python
# In adapter.to_inbound()
metadata = {
    # Platform identification
    "platform": "your_channel",
    "platform_version": "v2.1",

    # Threading information
    "thread_id": platform_message.get("thread_id"),
    "thread_name": platform_message.get("thread_name"),

    # User context
    "user_display_name": user["name"],
    "user_avatar_url": user["avatar"],
    "user_role": user.get("role"),

    # Message context
    "is_edited": platform_message.get("edited", False),
    "is_forwarded": platform_message.get("forwarded", False),
    "forward_from": platform_message.get("forward_from"),

    # Platform features
    "reactions": platform_message.get("reactions", []),
    "mentions": platform_message.get("mentions", []),

    # Custom fields (any JSON-serializable data)
    "custom_data": {...},
}
```

### 2. Channel Manifest Metadata

Add adapter-specific configuration:

```python
manifest = ChannelManifest(
    # ... frozen fields ...
    metadata={
        # Feature flags
        "supports_threading": True,
        "supports_reactions": True,
        "supports_editing": False,

        # Limits
        "max_message_length": 4096,
        "max_attachment_size_mb": 50,
        "max_attachments_per_message": 10,

        # Rate limits
        "rate_limit_per_second": 5,
        "burst_limit": 10,

        # Custom configuration
        "custom_emoji_enabled": True,
        "webhook_retry_count": 3,
    }
)
```

### 3. Validation and Error Handling

Add custom validation in adapter:

```python
def to_inbound(self, platform_message: Dict[str, Any]) -> InboundMessage:
    # Custom validation
    if len(platform_message.get("text", "")) > 10000:
        raise ValueError("Message text exceeds protocol limit of 10,000 chars")

    if not platform_message.get("user_id"):
        raise ValueError("Missing required user_id field")

    # Convert to InboundMessage
    return InboundMessage(...)
```

---

## Implementation Checklist

### Required Components

- [ ] **Manifest** (`manifest.py`):
  - [ ] Unique channel ID
  - [ ] Configuration fields defined
  - [ ] Session scope chosen (USER or USER_CONVERSATION)
  - [ ] Capabilities listed
  - [ ] Setup steps documented

- [ ] **Provider** (`provider.py`):
  - [ ] API client implementation
  - [ ] Authentication handling
  - [ ] Send message methods
  - [ ] Error handling and retries
  - [ ] Resource cleanup (async context manager or close method)

- [ ] **Adapter** (`adapter.py`):
  - [ ] `to_inbound()`: Platform → InboundMessage
  - [ ] `send_outbound()`: OutboundMessage → Platform
  - [ ] All frozen fields populated correctly
  - [ ] Metadata used for platform-specific fields
  - [ ] MessageType mapping complete
  - [ ] Timestamp handling (UTC-aware per ADR-011)

### Protocol Compliance

- [ ] **InboundMessage**:
  - [ ] `channel_id` set to unique instance ID
  - [ ] `user_key` is unique and stable per user
  - [ ] `conversation_key` is unique per conversation
  - [ ] `message_id` is globally unique
  - [ ] `timestamp` is timezone-aware UTC datetime
  - [ ] `type` maps correctly to MessageType enum
  - [ ] `metadata` contains platform-specific fields
  - [ ] `raw` preserves original message

- [ ] **OutboundMessage**:
  - [ ] All frozen MessageType values handled (TEXT minimum)
  - [ ] `reply_to_message_id` respected if provided
  - [ ] Metadata delivery options honored
  - [ ] Returns platform message ID

- [ ] **SessionRouter Compatibility**:
  - [ ] Session scope correctly configured in manifest
  - [ ] `user_key` and `conversation_key` are consistent and deterministic

### Testing Requirements

- [ ] **Unit Tests**:
  - [ ] `to_inbound()` conversion tests
  - [ ] `send_outbound()` for each MessageType
  - [ ] Metadata handling
  - [ ] Error cases

- [ ] **Integration Tests**:
  - [ ] End-to-end message flow
  - [ ] Webhook handling (if applicable)
  - [ ] Session routing
  - [ ] Multi-message conversations

- [ ] **Protocol Contract Tests**:
  - [ ] Run `pytest tests/protocol/test_frozen_protocol_v1.py`
  - [ ] Verify no frozen fields modified
  - [ ] Verify InboundMessage/OutboundMessage serialization

### Documentation

- [ ] **README** in channel directory:
  - [ ] Channel description
  - [ ] Setup instructions
  - [ ] Configuration examples
  - [ ] Known limitations

- [ ] **Code Documentation**:
  - [ ] Docstrings for all public methods
  - [ ] Type hints
  - [ ] ADR-014 references where relevant

---

## Testing Requirements

### Unit Tests

Create `tests/unit/communicationos/channels/test_your_channel.py`:

```python
import pytest
from agentos.communicationos.channels.your_channel.adapter import YourChannelAdapter
from agentos.communicationos.models import MessageType

def test_to_inbound_text_message():
    """Test converting platform text message to InboundMessage."""
    adapter = YourChannelAdapter("your_channel_001", {"api_key": "test"})

    platform_message = {
        "message_id": "msg_123",
        "user_id": "user_456",
        "conversation_id": "conv_789",
        "text": "Hello world",
        "timestamp": "2026-02-01T12:34:56Z",
    }

    inbound = adapter.to_inbound(platform_message)

    assert inbound.channel_id == "your_channel_001"
    assert inbound.user_key == "user_456"
    assert inbound.conversation_key == "conv_789"
    assert inbound.message_id == "msg_123"
    assert inbound.type == MessageType.TEXT
    assert inbound.text == "Hello world"
    assert inbound.timestamp.tzinfo is not None  # UTC-aware

@pytest.mark.asyncio
async def test_send_outbound_text_message():
    """Test sending OutboundMessage to platform."""
    adapter = YourChannelAdapter("your_channel_001", {"api_key": "test"})

    outbound = OutboundMessage(
        channel_id="your_channel_001",
        user_key="user_456",
        conversation_key="conv_789",
        type=MessageType.TEXT,
        text="Response message",
    )

    # Mock provider
    adapter.provider.send_message = AsyncMock(return_value={"message_id": "sent_123"})

    message_id = await adapter.send_outbound(outbound)

    assert message_id == "sent_123"
```

### Protocol Contract Tests

Run the frozen protocol test suite:

```bash
pytest tests/protocol/test_frozen_protocol_v1.py -v
```

All tests MUST pass. Failures indicate protocol violations.

---

## Submission Process

### 1. Pre-Submission Checklist

- [ ] All implementation checklist items complete
- [ ] Tests pass: `pytest tests/unit/communicationos/channels/test_your_channel.py -v`
- [ ] Protocol tests pass: `pytest tests/protocol/test_frozen_protocol_v1.py -v`
- [ ] Code linted: `ruff check . && ruff format --check .`
- [ ] Documentation complete
- [ ] Example configuration provided

### 2. Pull Request

1. **Fork and Create Branch**:
   ```bash
   git checkout -b feature/channel-your-channel
   ```

2. **Commit Changes**:
   ```bash
   git add agentos/communicationos/channels/your_channel/
   git add tests/unit/communicationos/channels/test_your_channel.py
   git commit -m "feat(communicationos): add Your Channel adapter"
   ```

3. **Create Pull Request** with:
   - Clear title: `feat(communicationos): Add Your Channel adapter`
   - Description:
     - What channel this adds
     - What capabilities are supported
     - Setup instructions
     - Testing performed
   - Reference: `Implements #<issue_number>`
   - Checklist from template

### 3. Review Process

Your PR will be reviewed for:
- Protocol compliance (ADR-014)
- Code quality and style
- Test coverage
- Documentation completeness
- Security considerations

### 4. Post-Merge

After merge:
- Your channel will appear in AgentOS channel marketplace
- Update any external documentation
- Consider writing a blog post or tutorial

---

## Examples

### Example Channels

Study these existing implementations:

- **Slack**: `agentos/communicationos/channels/slack/`
- **Telegram**: `agentos/communicationos/channels/telegram/`
- **Discord**: `agentos/communicationos/channels/discord/`
- **Email**: `agentos/communicationos/channels/email/`
- **SMS**: `agentos/communicationos/channels/sms/`

### Common Patterns

**Pattern 1: Rich Metadata**
```python
# Slack adapter preserves threading
metadata = {
    "slack_thread_ts": message.get("thread_ts"),
    "slack_team_id": message["team"]["id"],
    "slack_channel_name": channel_info["name"],
}
```

**Pattern 2: Attachment Handling**
```python
# Telegram adapter converts media types
if "photo" in message:
    attachments = [Attachment(
        type=AttachmentType.IMAGE,
        url=message["photo"][-1]["file_url"],  # Largest size
        metadata={"telegram_file_id": message["photo"][-1]["file_id"]},
    )]
```

**Pattern 3: Error Recovery**
```python
# Discord adapter with retry logic
async def send_outbound(self, message: OutboundMessage) -> str:
    for attempt in range(3):
        try:
            return await self.provider.send_message(...)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:  # Rate limit
                await asyncio.sleep(int(e.response.headers["Retry-After"]))
            else:
                raise
```

---

## Getting Help

- **Questions**: Open a [Discussion](https://github.com/seacow-technology/agentos/discussions)
- **Issues**: Report bugs via [Issues](https://github.com/seacow-technology/agentos/issues)
- **Slack/Discord**: Join our community channels
- **Email**: dev@seacow.tech

---

## References

- [ADR-014: Protocol Freeze](adr/ADR-014-protocol-freeze-v1.md) - Protocol v1 freeze details
- [ADR-011: Time & Timestamp Contract](adr/ADR-011-time-timestamp-contract.md) - Timestamp handling
- [CONTRIBUTING.md](../CONTRIBUTING.md) - General contribution guidelines

---

**Happy Contributing!** 🚀

Your channel adapter will help AgentOS connect with more platforms and communities.
