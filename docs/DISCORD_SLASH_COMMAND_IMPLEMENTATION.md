# Discord Slash Command Implementation (Hour 4)

## Implementation Summary

This document describes the Discord Slash Command implementation with proper defer mechanism to avoid Discord's 3-second timeout.

## Files Created/Modified

### 1. Core Adapter Files

#### `/agentos/communicationos/channels/discord/adapter.py`
Discord channel adapter with full slash command support.

**Key Features:**
- ✅ `handle_slash_command()`: Returns immediate defer (type=5)
- ✅ `process_slash_command_async()`: Background async processing
- ✅ `parse_interaction()`: Converts Discord interaction to InboundMessage
- ✅ `verify_signature()`: Ed25519 signature verification
- ✅ `handle_ping()`: PING/PONG for Discord endpoint verification
- ✅ Idempotency: Tracks interaction.id to prevent duplicates

**Key Methods:**

```python
def handle_slash_command(self, interaction: Dict[str, Any]) -> Dict[str, Any]:
    """Return immediate defer (type=5) within 3 seconds."""
    return {"type": 5}  # DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE

async def process_slash_command_async(self, interaction: Dict[str, Any], message_bus):
    """
    Background processing after defer:
    1. Parse interaction -> InboundMessage
    2. Process through MessageBus (dedupe, rate limit, audit)
    3. Get reply from chat/business logic
    4. Edit original response via client.edit_original_response()
    """
```

#### `/agentos/communicationos/channels/discord/client.py`
HTTP client for Discord Interactions API (already existed, reused).

**Key Functions:**
- `edit_original_response()`: Edit the deferred response with actual reply
- `create_followup_message()`: Send additional messages
- Message truncation (2000 char limit)
- Error handling (rate limits, expired tokens, auth failures)

#### `/agentos/communicationos/channels/discord/__init__.py`
Module exports for Discord adapter and client.

### 2. API Route Integration

#### `/agentos/webui/api/channels.py`
Added Discord webhook endpoint.

**New Route:**
```python
@router.post("/discord/interactions")
async def discord_interactions(
    request: Request,
    background_tasks: BackgroundTasks,
    x_signature_ed25519: str = Header(None, alias="X-Signature-Ed25519"),
    x_signature_timestamp: str = Header(None, alias="X-Signature-Timestamp")
):
    """
    Discord Interactions webhook endpoint.

    Flow:
    1. Read headers: X-Signature-Ed25519, X-Signature-Timestamp
    2. Verify signature (adapter.verify_signature)
    3. Parse body JSON
    4. type=1 → handle_ping() (return PONG immediately)
    5. type=2 → handle_slash_command() (return defer immediately)
    6. background_tasks.add_task(process_slash_command_async)
    """
```

**Integration Points:**
- Added `DiscordAdapter` import
- Added Discord adapter loading in `_load_enabled_channels()`
- Added async background task handler `_process_discord_interaction_async()`

## Architecture Flow

### Synchronous Flow (< 3 seconds)
```
Discord → POST /api/channels/discord/interactions
       → Verify signature
       → type=1? → handle_ping() → return {"type": 1}
       → type=2? → handle_slash_command() → return {"type": 5}
       → Return 200 OK within 3 seconds ✅
```

### Asynchronous Flow (background)
```
background_tasks.add_task(process_slash_command_async)
  → parse_interaction() → InboundMessage
  → message_bus.process_inbound() → dedupe, rate limit, audit
  → Forward to chat/command processor
  → Get reply text
  → client.edit_original_response(interaction_token, reply_text)
  → User sees reply in Discord ✅
```

## Key Discord Complexities Handled

### 1. 3-Second Timeout
**Problem:** Discord requires response within 3 seconds or marks interaction as failed.

**Solution:**
- Immediately return type=5 (DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE)
- Discord shows "Bot is thinking..." to user
- Process in background
- Edit original response when done

### 2. Ed25519 Signature Verification
**Problem:** Discord uses Ed25519 (not HMAC-SHA256 like other platforms).

**Solution:**
- Use `nacl` library (PyNaCl)
- Verify signature: `VerifyKey(public_key).verify(timestamp + body, signature)`
- Reject if signature invalid (prevents spoofing)

### 3. Interaction Token Expiry
**Problem:** Interaction tokens expire after 15 minutes.

**Solution:**
- Process slash commands promptly
- Handle `DiscordInteractionExpiredError` gracefully
- Log warning if processing takes > 15 minutes

### 4. Idempotency
**Problem:** Discord may retry failed interactions.

**Solution:**
- Track `interaction.id` in `_processed_interactions` set
- Skip duplicate interactions
- Return defer for duplicates (user already sees "thinking")

### 5. Message Length Limit
**Problem:** Discord messages limited to 2000 characters.

**Solution:**
- Client auto-truncates with "...(truncated)" suffix
- Warns in logs when truncation occurs

## Deduplication Strategy

Discord adapter integrates with existing MessageBus dedupe:

1. **Interaction-level dedupe** (adapter):
   - Track `interaction.id` in `_processed_interactions`
   - Prevent duplicate processing at parse level

2. **Message-level dedupe** (middleware):
   - Use `message_id = f"discord_interaction_{interaction_id}"`
   - DedupeMiddleware checks SQLite store
   - Reject if already processed

## Configuration Example

```python
# Channel configuration for Discord
{
    "channel_id": "discord_bot_001",
    "manifest_id": "discord",
    "enabled": true,
    "config": {
        "application_id": "123456789012345678",
        "public_key": "abcdef123456...",  # For Ed25519 verification
        "bot_token": "MTIzNDU2Nzg5MDEyMzQ1Njc4.GaBcDe.fGhIjKlMnOpQrStUvWxYz..."
    }
}
```

## Security Checklist

- ✅ Ed25519 signature verification (MANDATORY)
- ✅ Public key validated before processing
- ✅ Rate limiting via MessageBus middleware
- ✅ Audit logging via AuditMiddleware
- ✅ Idempotency (no duplicate processing)
- ✅ Error handling (graceful degradation)

## Testing Checklist

### Manual Testing
1. **PING Test:**
   - Discord sends type=1 on webhook URL configuration
   - Should receive type=1 (PONG) response
   - Discord marks URL as verified

2. **Slash Command Test:**
   - User invokes `/ask question: What is AgentOS?`
   - Discord shows "Bot is thinking..." (defer)
   - Response appears after processing
   - Response contains actual reply text

3. **Duplicate Test:**
   - Send same interaction twice (manually)
   - Second should be rejected (dedupe)
   - User sees only one response

4. **Timeout Test:**
   - Simulate slow processing (> 3 seconds)
   - User should still see defer (no timeout error)
   - Response appears when ready

### Integration Testing
- Unit tests for `adapter.py` (parse_interaction, verify_signature)
- Integration tests for webhook flow
- End-to-end tests with Discord API

## V1 Scope Limitations

What's NOT included in v1:
- ❌ Message Components (buttons, select menus)
- ❌ Modal Submits (forms)
- ❌ Context Menu Commands (right-click actions)
- ❌ Embeds (rich messages with images/links)
- ❌ Attachments (files, images)
- ❌ Followup messages (only edit original)
- ❌ Ephemeral messages (only visible to user)
- ❌ Auto-complete for slash command options

These can be added in future iterations.

## Next Steps

1. **Add Discord manifest** to channel registry
2. **Create unit tests** for adapter methods
3. **Add Discord to frontend** channels setup wizard
4. **Test with real Discord bot** (create test server)
5. **Document slash command creation** in Discord Developer Portal
6. **Add chat integration** (forward to AgentOS chat pipeline)

## Related Files

- `/agentos/communicationos/channels/discord/adapter.py` - Main adapter
- `/agentos/communicationos/channels/discord/client.py` - HTTP client
- `/agentos/webui/api/channels.py` - Webhook routes
- `/agentos/communicationos/message_bus.py` - Message processing pipeline
- `/agentos/communicationos/dedupe.py` - Deduplication middleware

## References

- [Discord Interactions API](https://discord.com/developers/docs/interactions/receiving-and-responding)
- [Discord Security](https://discord.com/developers/docs/interactions/receiving-and-responding#security-and-authorization)
- [Slash Commands](https://discord.com/developers/docs/interactions/application-commands)
- [PyNaCl Documentation](https://pynacl.readthedocs.io/)

## Completion Confirmation

✅ **handle_slash_command()** returns `{"type": 5}` (DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE)
✅ **process_slash_command_async()** designed with clear flow:
   - Parse interaction
   - Process through MessageBus
   - Get reply
   - Edit original response
✅ **Route integration** complete:
   - POST /api/channels/discord/interactions
   - Signature verification
   - PING/PONG handling
   - Defer + background processing
   - Proper error handling
✅ **Deduplication** integrated with existing MessageBus mechanism
✅ **Documentation** complete with examples and flow diagrams

The Discord Slash Command implementation is ready for testing and integration.
