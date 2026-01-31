# SMS Channel Developer Integration Guide

**Audience:** AgentOS developers integrating SMS channel into applications
**Version:** v2.0.0 (Bidirectional)
**Last Updated:** 2026-02-01

---

## Overview

This guide covers programmatic integration of the SMS Channel v2 with inbound webhook support.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Your Application                      │
│                                                          │
│  ┌────────────┐         ┌──────────────┐               │
│  │   WebAPI   │────────>│  MessageBus  │               │
│  │  (webhook) │         │              │               │
│  └────────────┘         └───────┬──────┘               │
│                                 │                        │
│                         ┌───────▼──────────┐            │
│                         │   SmsAdapter     │            │
│                         │  ┌─────────────┐ │            │
│                         │  │ Twilio      │ │            │
│                         │  │ Provider    │ │            │
│                         │  └─────────────┘ │            │
│                         └──────────────────┘            │
└─────────────────────────────────────────────────────────┘
                                 │
                                 │ HTTPS
                                 ▼
                          ┌─────────────┐
                          │   Twilio    │
                          │   Server    │
                          └─────────────┘
```

---

## Programmatic Setup

### 1. Create SMS Adapter

```python
from agentos.communicationos.channels.sms import SmsAdapter
from agentos.communicationos.providers.sms import TwilioSmsProvider
from agentos.communicationos.audit import AuditStore

# Create provider
provider = TwilioSmsProvider(
    account_sid="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    auth_token="your_32_char_auth_token",
    from_number="+15551234567"
)

# Create adapter with webhook support
adapter = SmsAdapter(
    channel_id="sms_app_001",
    provider=provider,
    audit_store=AuditStore(),
    max_length=480,
    webhook_auth_token="your_32_char_auth_token"  # For signature verification
)

print(f"SMS Adapter created: {adapter.channel_id}")
```

### 2. Register with MessageBus

```python
from agentos.communicationos.message_bus import MessageBus

# Initialize MessageBus
message_bus = MessageBus()

# Register adapter
message_bus.register_adapter("sms_app_001", adapter)

print("SMS Adapter registered with MessageBus")
```

### 3. Process Webhook (FastAPI Example)

```python
from fastapi import APIRouter, Request, HTTPException, Header, BackgroundTasks
from typing import Optional

router = APIRouter()

@router.post("/webhook/{path_token}")
async def sms_webhook(
    path_token: str,
    request: Request,
    background_tasks: BackgroundTasks,
    x_twilio_signature: Optional[str] = Header(None)
):
    """Handle Twilio SMS webhook."""

    # 1. Verify path token
    expected_token = get_config("SMS_WEBHOOK_PATH_TOKEN")
    if path_token != expected_token:
        raise HTTPException(status_code=404)

    # 2. Parse form data
    form_data = await request.form()
    post_data = dict(form_data)

    # 3. Verify signature
    url = str(request.url)
    if not adapter.verify_twilio_signature(url, post_data, x_twilio_signature or ""):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # 4. Parse webhook
    inbound = adapter.parse_inbound_webhook(post_data)
    if not inbound:
        return {"status": "ok"}  # Duplicate or invalid

    # 5. Process in background
    background_tasks.add_task(process_inbound, inbound)

    # 6. Return 200 immediately
    return {"status": "ok"}


async def process_inbound(inbound):
    """Background processing."""
    context = await message_bus.process_inbound(inbound)

    if context.status == "continue":
        # Forward to chat, generate reply, etc.
        reply = await generate_reply(inbound)
        adapter.handle_outbound(reply)
```

---

## Send Outbound SMS

### Basic Usage

```python
from agentos.communicationos.models import OutboundMessage, MessageType

# Create message
message = OutboundMessage(
    channel_id="sms_app_001",
    user_key="+15559876543",  # Recipient phone (E.164)
    conversation_key="+15559876543",  # Same for 1:1 SMS
    type=MessageType.TEXT,
    text="Hello from AgentOS!"
)

# Send via adapter
result = adapter.handle_outbound(message)

if result.success:
    print(f"SMS sent: {result.message_sid}")
    print(f"Segments: {result.segments_count}")
    print(f"Cost: ${result.cost}")
else:
    print(f"Error: {result.error_message}")
```

### With Error Handling

```python
from agentos.communicationos.models import OutboundMessage, MessageType

def send_sms_with_retry(adapter, to_number, text, max_retries=3):
    """Send SMS with automatic retry on transient errors."""

    for attempt in range(max_retries):
        message = OutboundMessage(
            channel_id=adapter.channel_id,
            user_key=to_number,
            conversation_key=to_number,
            type=MessageType.TEXT,
            text=text
        )

        result = adapter.handle_outbound(message)

        if result.success:
            return result

        # Check if error is retryable
        if result.error_code in ["TIMEOUT", "CONNECTION_ERROR"]:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue

        # Non-retryable error
        raise Exception(f"SMS send failed: {result.error_message}")

    raise Exception("Max retries exceeded")
```

---

## Signature Verification (Manual)

If you need to verify signatures outside the adapter:

```python
import hmac
import hashlib
import base64

def verify_twilio_signature(url, post_data, signature, auth_token):
    """Verify Twilio webhook signature.

    Args:
        url: Full webhook URL (e.g., "https://example.com/webhook/token")
        post_data: Dictionary of POST parameters
        signature: X-Twilio-Signature header value
        auth_token: Twilio Auth Token

    Returns:
        True if valid, False otherwise
    """
    # Build data string
    sorted_params = sorted(post_data.items())
    data_string = url + ''.join(f"{k}{v}" for k, v in sorted_params)

    # Compute HMAC-SHA1
    computed_sig = hmac.new(
        auth_token.encode('utf-8'),
        data_string.encode('utf-8'),
        hashlib.sha1
    ).digest()

    # Base64 encode
    computed_sig_b64 = base64.b64encode(computed_sig).decode('ascii')

    # Constant-time comparison
    return hmac.compare_digest(computed_sig_b64, signature)


# Usage
is_valid = verify_twilio_signature(
    url="https://example.com/webhook/token123",
    post_data={"From": "+1234", "To": "+5678", "Body": "Hi"},
    signature="base64_signature_from_header",
    auth_token="your_auth_token"
)
```

---

## Custom Middleware

### Rate Limiting Example

```python
from agentos.communicationos.message_bus import Middleware, ProcessingContext, ProcessingStatus
from agentos.communicationos.models import InboundMessage, OutboundMessage
from datetime import datetime, timedelta

class SmsRateLimitMiddleware(Middleware):
    """Rate limit SMS per user (e.g., 10 per minute)."""

    def __init__(self, max_per_minute=10):
        self.max_per_minute = max_per_minute
        self.user_timestamps = {}  # user_key -> [timestamp]

    async def process_inbound(
        self,
        message: InboundMessage,
        context: ProcessingContext
    ) -> ProcessingContext:
        """Check rate limit for inbound SMS."""

        user_key = message.user_key
        now = datetime.utcnow()

        # Get user's recent messages
        timestamps = self.user_timestamps.get(user_key, [])

        # Remove old timestamps (older than 1 minute)
        cutoff = now - timedelta(minutes=1)
        timestamps = [t for t in timestamps if t > cutoff]

        # Check rate limit
        if len(timestamps) >= self.max_per_minute:
            context.status = ProcessingStatus.REJECT
            context.error = f"Rate limit exceeded: {self.max_per_minute}/min"
            return context

        # Add current timestamp
        timestamps.append(now)
        self.user_timestamps[user_key] = timestamps

        return context

    async def process_outbound(
        self,
        message: OutboundMessage,
        context: ProcessingContext
    ) -> ProcessingContext:
        """No rate limiting for outbound (for now)."""
        return context


# Register middleware
message_bus.add_middleware(SmsRateLimitMiddleware(max_per_minute=10))
```

---

## Inbound Message Handler

### Custom Handler Example

```python
from agentos.communicationos.models import InboundMessage, OutboundMessage, MessageType

def handle_sms_commands(inbound: InboundMessage):
    """Custom command handler for SMS."""

    text = inbound.text.strip().lower()

    # Command: /help
    if text == "/help":
        reply = OutboundMessage(
            channel_id=inbound.channel_id,
            user_key=inbound.user_key,
            conversation_key=inbound.conversation_key,
            type=MessageType.TEXT,
            text="Available commands:\n/help - Show this help\n/status - Check status"
        )
        adapter.handle_outbound(reply)
        return

    # Command: /status
    if text == "/status":
        reply = OutboundMessage(
            channel_id=inbound.channel_id,
            user_key=inbound.user_key,
            conversation_key=inbound.conversation_key,
            type=MessageType.TEXT,
            text="Status: All systems operational"
        )
        adapter.handle_outbound(reply)
        return

    # Not a command - forward to chat
    print(f"Forwarding to chat: {text}")


# Register handler
message_bus.add_inbound_handler(handle_sms_commands)
```

---

## Testing Utilities

### Mock Provider

```python
from agentos.communicationos.providers.sms import SendResult

class MockSmsProvider:
    """Mock SMS provider for testing."""

    def __init__(self):
        self.sent_messages = []

    def send_sms(self, to_number, message_text, from_number=None, max_segments=3):
        """Mock send (stores in memory)."""
        self.sent_messages.append({
            "to": to_number,
            "text": message_text,
            "from": from_number
        })
        return SendResult(
            success=True,
            message_sid=f"SM_test_{len(self.sent_messages)}",
            segments_count=1
        )

    def validate_config(self):
        return True, None

    def test_connection(self, test_to_number=None):
        return True, None


# Usage in tests
mock_provider = MockSmsProvider()
adapter = SmsAdapter(
    channel_id="test",
    provider=mock_provider,
    webhook_auth_token="test_token"
)

# Send test message
adapter.handle_outbound(message)

# Check mock
assert len(mock_provider.sent_messages) == 1
assert mock_provider.sent_messages[0]["to"] == "+15559876543"
```

### Webhook Simulator

```python
import requests

def simulate_twilio_webhook(url, from_number, to_number, body, auth_token):
    """Simulate Twilio webhook with valid signature."""

    # Build POST data
    post_data = {
        "MessageSid": f"SM_test_{int(time.time())}",
        "From": from_number,
        "To": to_number,
        "Body": body,
        "NumMedia": "0"
    }

    # Compute signature
    signature = compute_twilio_signature(url, post_data, auth_token)

    # Send request
    response = requests.post(
        url,
        data=post_data,
        headers={"X-Twilio-Signature": signature}
    )

    return response


# Usage
response = simulate_twilio_webhook(
    url="https://example.com/webhook/token123",
    from_number="+15559876543",
    to_number="+15551234567",
    body="Test message",
    auth_token="your_auth_token"
)

assert response.status_code == 200
```

---

## Performance Optimization

### 1. Connection Pooling (Twilio API)

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Create session with connection pooling
session = requests.Session()
retry = Retry(total=3, backoff_factor=1)
adapter_http = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
session.mount('https://', adapter_http)

# Use session in TwilioSmsProvider (custom implementation)
class OptimizedTwilioProvider(TwilioSmsProvider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session

    def send_sms(self, *args, **kwargs):
        # Use self.session instead of requests.post
        pass
```

### 2. Batch Deduplication Check

```python
def batch_dedupe_check(adapter, message_sids):
    """Check multiple MessageSids at once."""

    duplicates = []
    new_sids = []

    for sid in message_sids:
        if sid in adapter._processed_message_sids:
            duplicates.append(sid)
        else:
            new_sids.append(sid)
            adapter._processed_message_sids.add(sid)

    return new_sids, duplicates
```

### 3. Redis-Backed Deduplication (Production)

```python
import redis

class RedisSmsAdapter(SmsAdapter):
    """SMS Adapter with Redis-backed deduplication."""

    def __init__(self, *args, redis_client=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.redis = redis_client or redis.Redis()
        self.dedupe_ttl = 3600  # 1 hour

    def parse_inbound_webhook(self, post_data):
        """Override with Redis deduplication."""

        message_sid = post_data.get('MessageSid')
        if not message_sid:
            return None

        # Check Redis (atomic operation)
        key = f"sms:dedupe:{message_sid}"
        if self.redis.set(key, "1", nx=True, ex=self.dedupe_ttl):
            # New message - continue processing
            return super().parse_inbound_webhook(post_data)
        else:
            # Duplicate - ignore
            return None


# Usage
import redis
redis_client = redis.Redis(host='localhost', port=6379, db=0)
adapter = RedisSmsAdapter(
    channel_id="sms_prod",
    provider=provider,
    redis_client=redis_client
)
```

---

## Monitoring & Observability

### Metrics Collection

```python
from dataclasses import dataclass
from collections import defaultdict
import time

@dataclass
class SmsMetrics:
    """SMS channel metrics."""

    inbound_count: int = 0
    outbound_count: int = 0
    signature_failures: int = 0
    duplicates: int = 0
    errors: int = 0


class MonitoredSmsAdapter(SmsAdapter):
    """SMS Adapter with metrics collection."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metrics = SmsMetrics()

    def verify_twilio_signature(self, *args, **kwargs):
        """Override to track signature failures."""
        is_valid = super().verify_twilio_signature(*args, **kwargs)
        if not is_valid:
            self.metrics.signature_failures += 1
        return is_valid

    def parse_inbound_webhook(self, post_data):
        """Override to track inbound + duplicates."""
        inbound = super().parse_inbound_webhook(post_data)
        if inbound:
            self.metrics.inbound_count += 1
        else:
            self.metrics.duplicates += 1
        return inbound

    def handle_outbound(self, message):
        """Override to track outbound."""
        result = super().handle_outbound(message)
        if result.success:
            self.metrics.outbound_count += 1
        else:
            self.metrics.errors += 1
        return result

    def get_metrics(self):
        """Get current metrics."""
        return self.metrics


# Usage
adapter = MonitoredSmsAdapter(...)

# Periodically export metrics
def export_metrics():
    metrics = adapter.get_metrics()
    print(f"Inbound: {metrics.inbound_count}")
    print(f"Outbound: {metrics.outbound_count}")
    print(f"Signature Failures: {metrics.signature_failures}")
    print(f"Duplicates: {metrics.duplicates}")
    print(f"Errors: {metrics.errors}")
```

---

## Error Handling Patterns

### Graceful Degradation

```python
def send_sms_with_fallback(adapter, message, fallback_channel=None):
    """Send SMS with fallback to another channel."""

    result = adapter.handle_outbound(message)

    if result.success:
        return result

    # Check if error is permanent
    if result.error_code in ["INVALID_E164", "INVALID_TO"]:
        # Permanent error - don't retry
        raise ValueError(f"Invalid recipient: {message.user_key}")

    # Transient error - try fallback channel
    if fallback_channel:
        logger.warning(f"SMS failed, trying fallback: {result.error_message}")
        return fallback_channel.send_message(message)

    raise Exception(f"SMS send failed: {result.error_message}")
```

### Circuit Breaker

```python
from datetime import datetime, timedelta

class CircuitBreaker:
    """Circuit breaker for SMS sending."""

    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open

    def call(self, func, *args, **kwargs):
        """Call function with circuit breaker."""

        # Check if circuit is open
        if self.state == "open":
            if datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.timeout):
                self.state = "half_open"
            else:
                raise Exception("Circuit breaker is open")

        # Try call
        try:
            result = func(*args, **kwargs)
            if result.success:
                # Success - reset
                self.failures = 0
                self.state = "closed"
            else:
                # Failure
                self.failures += 1
                self.last_failure_time = datetime.utcnow()
                if self.failures >= self.failure_threshold:
                    self.state = "open"
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = datetime.utcnow()
            if self.failures >= self.failure_threshold:
                self.state = "open"
            raise


# Usage
breaker = CircuitBreaker()
result = breaker.call(adapter.handle_outbound, message)
```

---

## Security Best Practices

### 1. Token Rotation

```python
import secrets

def rotate_webhook_token(adapter, config_store):
    """Rotate webhook path token."""

    # Generate new token
    new_token = secrets.token_urlsafe(32)

    # Update config
    config = config_store.get_config(adapter.channel_id)
    old_token = config["webhook_path_token"]
    config["webhook_path_token"] = new_token
    config_store.save_config(adapter.channel_id, config)

    # Log rotation
    logger.info(f"Rotated webhook token for channel: {adapter.channel_id}")

    # Return old token (for transition period)
    return old_token, new_token
```

### 2. Request Validation

```python
def validate_twilio_request(request, adapter):
    """Comprehensive request validation."""

    # 1. Check Content-Type
    if request.headers.get("Content-Type") != "application/x-www-form-urlencoded":
        raise HTTPException(status_code=400, detail="Invalid Content-Type")

    # 2. Check User-Agent (optional but recommended)
    user_agent = request.headers.get("User-Agent", "")
    if not user_agent.startswith("TwilioProxy/"):
        logger.warning(f"Unexpected User-Agent: {user_agent}")

    # 3. Verify signature
    signature = request.headers.get("X-Twilio-Signature")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing signature")

    url = str(request.url)
    post_data = dict(await request.form())

    if not adapter.verify_twilio_signature(url, post_data, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    return post_data
```

---

## Common Pitfalls

### ❌ Don't: Block webhook handler

```python
# BAD - Don't do this
@router.post("/webhook/{token}")
async def webhook(token, request: Request):
    inbound = parse_webhook(await request.form())

    # ❌ BLOCKING: Generates reply synchronously
    reply = await generate_chat_response(inbound)  # Slow!
    adapter.handle_outbound(reply)

    return {"status": "ok"}
```

### ✅ Do: Use background tasks

```python
# GOOD - Do this instead
@router.post("/webhook/{token}")
async def webhook(token, request: Request, background_tasks: BackgroundTasks):
    inbound = parse_webhook(await request.form())

    # ✅ NON-BLOCKING: Process in background
    background_tasks.add_task(process_and_reply, inbound)

    return {"status": "ok"}  # Return immediately
```

### ❌ Don't: Ignore duplicates

```python
# BAD - Don't do this
def parse_webhook(post_data):
    # ❌ No deduplication - processes duplicates
    return InboundMessage(...)
```

### ✅ Do: Check MessageSid

```python
# GOOD - Do this instead
def parse_webhook(post_data):
    message_sid = post_data.get("MessageSid")

    # ✅ Deduplicate
    if message_sid in processed_sids:
        return None

    processed_sids.add(message_sid)
    return InboundMessage(...)
```

---

## References

- [SMS Channel Manifest](/agentos/communicationos/channels/sms/manifest.json)
- [SmsAdapter Implementation](/agentos/communicationos/channels/sms/adapter.py)
- [TwilioSmsProvider Implementation](/agentos/communicationos/providers/sms/twilio_provider.py)
- [Integration Tests](/tests/integration/communicationos/test_sms_inbound.py)
- [Twilio Webhook Docs](https://www.twilio.com/docs/sms/webhooks)
- [Twilio Signature Validation](https://www.twilio.com/docs/usage/security#validating-requests)

---

**Last Updated:** 2026-02-01
**Version:** SMS Channel v2.0.0
**Support:** AgentOS CommunicationOS Team
