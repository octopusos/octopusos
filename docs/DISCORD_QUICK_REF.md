# Discord Adapter Quick Reference

## Core Concepts

### The 3-Second Rule
Discord requires response within 3 seconds. ALWAYS:
1. Return defer immediately: `{"type": 5}`
2. Process in background
3. Edit original response when done

### Key Interaction Types
```python
TYPE_PING = 1                        # Discord verification
TYPE_APPLICATION_COMMAND = 2         # Slash commands (v1)
TYPE_MESSAGE_COMPONENT = 3           # Buttons/menus (future)
TYPE_APPLICATION_COMMAND_AUTOCOMPLETE = 4  # Auto-complete (future)
TYPE_MODAL_SUBMIT = 5                # Forms (future)
```

### Key Response Types
```python
RESPONSE_PONG = 1                              # Reply to PING
RESPONSE_DEFERRED_CHANNEL_MESSAGE = 5          # "Bot is thinking..."
```

## Implementation Pattern

### 1. Webhook Route
```python
@router.post("/discord/interactions")
async def discord_interactions(
    request: Request,
    background_tasks: BackgroundTasks,
    x_signature_ed25519: str = Header(...),
    x_signature_timestamp: str = Header(...)
):
    # Step 1: Verify signature (MANDATORY)
    body = await request.body()
    if not adapter.verify_signature(x_signature_ed25519, x_signature_timestamp, body):
        return Response(status_code=401)

    # Step 2: Parse JSON
    interaction = await request.json()

    # Step 3: Handle PING
    if interaction["type"] == 1:
        return JSONResponse({"type": 1})

    # Step 4: Handle slash command
    if interaction["type"] == 2:
        defer_response = {"type": 5}
        background_tasks.add_task(process_async, interaction)
        return JSONResponse(defer_response)
```

### 2. Async Processing
```python
async def process_async(interaction):
    # Parse to InboundMessage
    inbound = adapter.parse_interaction(interaction)

    # Process through MessageBus
    context = await message_bus.process_inbound(inbound)

    # Get reply
    reply_text = "Your response here"

    # Edit original response
    await client.edit_original_response(
        interaction_token=interaction["token"],
        content=reply_text
    )
```

## Signature Verification

```python
from nacl.signing import VerifyKey

def verify_signature(public_key, signature, timestamp, body):
    message = timestamp.encode() + body
    signature_bytes = bytes.fromhex(signature)
    verify_key = VerifyKey(bytes.fromhex(public_key))

    try:
        verify_key.verify(message, signature_bytes)
        return True
    except:
        return False
```

## Interaction Structure

```json
{
    "id": "123456789012345678",           // Unique interaction ID (for idempotency)
    "type": 2,                             // APPLICATION_COMMAND
    "token": "unique_token_15min_expiry",  // For editing response
    "channel_id": "987654321098765432",    // Where command was invoked
    "guild_id": "111222333444555666",      // Server ID (null in DMs)
    "member": {                             // In guilds
        "user": {
            "id": "777888999000111222",
            "username": "alice"
        }
    },
    "user": {                               // In DMs
        "id": "777888999000111222",
        "username": "alice"
    },
    "data": {
        "name": "ask",                      // Command name
        "options": [                        // Command arguments
            {
                "name": "question",
                "value": "What is AgentOS?"
            }
        ]
    }
}
```

## Common Pitfalls

### ❌ DON'T: Process synchronously
```python
# BAD: Will timeout after 3 seconds
@router.post("/discord/interactions")
async def discord_interactions(request):
    interaction = await request.json()
    reply = await process_command(interaction)  # Slow!
    return {"type": 4, "data": {"content": reply}}  # TOO LATE
```

### ✅ DO: Defer + async processing
```python
# GOOD: Defer immediately, process in background
@router.post("/discord/interactions")
async def discord_interactions(request, background_tasks):
    interaction = await request.json()
    background_tasks.add_task(process_command, interaction)
    return {"type": 5}  # Deferred (< 3 seconds)
```

### ❌ DON'T: Skip signature verification
```python
# INSECURE: Anyone can spoof interactions
@router.post("/discord/interactions")
async def discord_interactions(request):
    interaction = await request.json()  # No verification!
    # Process...
```

### ✅ DO: Always verify signatures
```python
# SECURE: Verify before processing
@router.post("/discord/interactions")
async def discord_interactions(request, x_signature_ed25519, x_signature_timestamp):
    body = await request.body()
    if not verify_signature(...):
        return Response(status_code=401)
    # Process...
```

## Idempotency

```python
class DiscordAdapter:
    def __init__(self):
        self._processed_interactions = set()

    def parse_interaction(self, interaction):
        interaction_id = interaction["id"]

        # Check duplicate
        if interaction_id in self._processed_interactions:
            logger.info(f"Skipping duplicate: {interaction_id}")
            return None

        # Mark as processed
        self._processed_interactions.add(interaction_id)

        # Parse...
```

## Error Handling

```python
async def process_async(interaction):
    try:
        # Process...
        reply = "Success!"
    except Exception as e:
        logger.exception(f"Error: {e}")
        reply = f"Error: {str(e)}"

    # Always edit response (even on error)
    try:
        await client.edit_original_response(
            interaction_token=interaction["token"],
            content=reply
        )
    except DiscordInteractionExpiredError:
        logger.warning("Interaction expired (>15 min)")
    except Exception as e:
        logger.exception(f"Failed to edit response: {e}")
```

## Configuration

```json
{
    "channel_id": "discord_bot_001",
    "manifest_id": "discord",
    "enabled": true,
    "config": {
        "application_id": "123456789012345678",
        "public_key": "abcdef123456...",
        "bot_token": "MTIzNDU2Nzg5..."
    }
}
```

## Testing

### 1. PING Test (Endpoint Verification)
```bash
curl -X POST https://your-domain.com/api/channels/discord/interactions \
  -H "Content-Type: application/json" \
  -H "X-Signature-Ed25519: YOUR_SIGNATURE" \
  -H "X-Signature-Timestamp: TIMESTAMP" \
  -d '{"type": 1}'

# Expected: {"type": 1}
```

### 2. Slash Command Test
```bash
# Invoke /ask in Discord
# Expected:
# 1. Immediate "Bot is thinking..." (defer)
# 2. Response appears after processing
```

### 3. Duplicate Test
```bash
# Send same interaction twice
# Expected:
# 1. First: Processed normally
# 2. Second: Rejected (duplicate)
```

## Webhook URL Setup

1. Go to Discord Developer Portal
2. Select your application
3. Go to "General Information" → "Interactions Endpoint URL"
4. Enter: `https://your-domain.com/api/channels/discord/interactions`
5. Discord sends PING (type=1)
6. Your endpoint responds with PONG (type=1)
7. Discord verifies URL ✅

## Slash Command Creation

```bash
# Using Discord API
curl -X POST "https://discord.com/api/v10/applications/YOUR_APP_ID/commands" \
  -H "Authorization: Bot YOUR_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ask",
    "description": "Ask AgentOS a question",
    "options": [
      {
        "name": "question",
        "description": "Your question",
        "type": 3,
        "required": true
      }
    ]
  }'
```

## Key Files

```
agentos/communicationos/channels/discord/
├── __init__.py          # Module exports
├── adapter.py           # DiscordAdapter (main logic)
└── client.py            # DiscordClient (HTTP API)

agentos/webui/api/
└── channels.py          # POST /discord/interactions route

docs/
├── DISCORD_SLASH_COMMAND_IMPLEMENTATION.md  # Full docs
└── DISCORD_QUICK_REF.md                      # This file
```

## Summary

1. **3-second rule**: Defer immediately, process async
2. **Signature verification**: MANDATORY (Ed25519)
3. **Idempotency**: Track interaction.id
4. **Error handling**: Always edit response (even on error)
5. **Token expiry**: Process within 15 minutes
6. **V1 scope**: Slash commands only (no buttons/modals)

## Need Help?

- [Discord Interactions API Docs](https://discord.com/developers/docs/interactions/receiving-and-responding)
- [Discord Developer Portal](https://discord.com/developers/applications)
- [PyNaCl Documentation](https://pynacl.readthedocs.io/)
