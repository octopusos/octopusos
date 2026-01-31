# Setup Wizard Implementation Guide

## Overview

The Setup Wizard is a multi-step guided interface for configuring communication channels in AgentOS CommunicationOS. It provides a user-friendly experience for connecting external messaging platforms like WhatsApp, Telegram, Slack, etc.

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend Layer                        │
├─────────────────────────────────────────────────────────┤
│  ChannelsView.js         │  Channel marketplace & list  │
│  ChannelSetupWizard.js   │  5-step setup wizard         │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    Backend Layer                         │
├─────────────────────────────────────────────────────────┤
│  channels.py API         │  REST endpoints              │
│    - GET /manifests      │  List available channels     │
│    - GET /manifests/:id  │  Get full manifest           │
│    - POST /validate      │  Validate configuration      │
│    - POST /test          │  Test channel connection     │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    Core Layer                            │
├─────────────────────────────────────────────────────────┤
│  ChannelRegistry         │  Manifest management         │
│  ChannelManifest         │  Channel metadata            │
│  ChannelConfigStore      │  Configuration storage       │
└─────────────────────────────────────────────────────────┘
```

## Setup Wizard Steps

### Step 1: Provider Variant Selection

**Purpose:** Display channel information and allow variant selection (if multiple providers available)

**Features:**
- Channel icon and branding
- Provider information
- Capabilities list
- Privacy & security badges
- Link to official documentation

**UI Elements:**
```javascript
{
  name: "WhatsApp (Twilio)",
  provider: "Twilio",
  capabilities: ["inbound_text", "outbound_text", ...],
  privacy_badges: ["No Auto Provisioning", "Chat-only", ...]
}
```

### Step 2: Webhook URL Generation

**Purpose:** Display and copy the webhook URL for external configuration

**Features:**
- Auto-generated webhook URL based on manifest
- One-click copy to clipboard
- Webhook configuration details (method, content-type)
- Security notice for signature verification
- Rate limit information

**Example Output:**
```
Webhook URL: https://yourdomain.com/api/channels/whatsapp_twilio/webhook
Method: POST
Content-Type: application/x-www-form-urlencoded
Rate Limit: 20 req/min
```

### Step 3: Setup Steps Guide

**Purpose:** Animated checklist of setup steps with instructions

**Features:**
- Interactive checklist items
- Expandable instructions
- Optional animation/video guides
- Sub-checklist for each step
- Progress tracking

**Example:**
```javascript
{
  title: "Get Twilio Credentials",
  description: "Sign up for Twilio and get your Account SID and Auth Token",
  instruction: "1. Go to https://www.twilio.com/console\n2. Create an account...",
  checklist: [
    "Created Twilio account",
    "Found Account SID in console",
    "Copied Auth Token securely"
  ],
  auto_check: false
}
```

### Step 4: Configuration Form

**Purpose:** Collect required configuration parameters with validation

**Features:**
- Auto-generated form from manifest
- Field type support (text, password, select, textarea)
- Real-time validation
- Regex pattern matching
- Help text for each field
- Secret field encryption indicator

**Validation:**
- Client-side HTML5 validation
- Server-side manifest validation
- Custom regex patterns
- Required field checks

**Example Field:**
```javascript
{
  name: "account_sid",
  label: "Account SID",
  type: "text",
  required: true,
  placeholder: "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  help_text: "Your Twilio Account SID (found in Twilio Console)",
  validation_regex: "^AC[a-f0-9]{32}$",
  validation_error: "Account SID must start with AC and be 34 characters"
}
```

### Step 5: Test Connection

**Purpose:** Verify configuration before saving

**Features:**
- Test connection button
- Real-time test results
- Diagnostics on failure
- Common error suggestions
- Success confirmation

**Test Flow:**
1. Validate configuration format
2. Create test adapter instance
3. Verify credentials (if possible)
4. Display results with diagnostics

**Example Response:**
```javascript
{
  success: true,
  message: "Configuration appears valid. Webhook is ready to receive messages.",
  diagnostics: {
    step: "validation",
    details: "Credentials format validated successfully"
  }
}
```

## API Endpoints

### GET /api/channels/manifests

List all available channel manifests.

**Response:**
```json
{
  "ok": true,
  "data": {
    "manifests": [
      {
        "id": "whatsapp_twilio",
        "name": "WhatsApp (Twilio)",
        "description": "...",
        "provider": "Twilio",
        "capabilities": [...],
        "setup_steps": [...],
        ...
      }
    ]
  }
}
```

### GET /api/channels/manifests/{manifest_id}

Get full manifest for a specific channel.

**Response:**
```json
{
  "ok": true,
  "data": {
    "id": "whatsapp_twilio",
    "name": "WhatsApp (Twilio)",
    "required_config_fields": [...],
    "setup_steps": [...],
    "security_defaults": {...},
    ...
  }
}
```

### POST /api/channels/manifests/{manifest_id}/validate

Validate channel configuration.

**Request:**
```json
{
  "config": {
    "account_sid": "AC...",
    "auth_token": "...",
    "phone_number": "+1..."
  }
}
```

**Response:**
```json
{
  "ok": true,
  "data": {
    "valid": true,
    "error": null
  }
}
```

### POST /api/channels/manifests/{manifest_id}/test

Test channel configuration.

**Request:**
```json
{
  "config": {
    "account_sid": "AC...",
    "auth_token": "...",
    "phone_number": "+1..."
  }
}
```

**Response (Success):**
```json
{
  "ok": true,
  "data": {
    "success": true,
    "message": "Configuration appears valid. Webhook is ready to receive messages.",
    "diagnostics": {
      "step": "validation",
      "details": "Credentials format validated successfully"
    }
  }
}
```

**Response (Failure):**
```json
{
  "ok": false,
  "data": {
    "success": false,
    "error": "Test failed: Invalid credentials",
    "diagnostics": {
      "step": "adapter_creation",
      "details": "Authentication failed",
      "common_issues": [
        "Invalid Account SID or Auth Token",
        "Phone number format incorrect",
        "Network connectivity issues"
      ]
    }
  }
}
```

## Adding New Channels

### 1. Create Channel Manifest

Create a JSON file in `agentos/communicationos/channels/`:

```json
{
  "id": "telegram",
  "name": "Telegram",
  "icon": "telegram",
  "description": "Connect Telegram using Bot API",
  "provider": "Telegram",
  "required_config_fields": [
    {
      "name": "bot_token",
      "label": "Bot Token",
      "type": "password",
      "required": true,
      "secret": true,
      "help_text": "Your Telegram Bot Token from @BotFather"
    }
  ],
  "webhook_paths": ["/api/channels/telegram/webhook"],
  "setup_steps": [
    {
      "title": "Create Bot",
      "description": "Create a new bot using @BotFather",
      "instruction": "1. Open Telegram\n2. Search for @BotFather\n3. Send /newbot",
      "checklist": ["Created bot", "Received bot token"]
    }
  ],
  ...
}
```

### 2. Implement Channel Adapter

Create adapter in `agentos/communicationos/channels/`:

```python
from agentos.communicationos.channels.base import ChannelAdapter

class TelegramAdapter(ChannelAdapter):
    def __init__(self, channel_id: str, bot_token: str):
        super().__init__(channel_id)
        self.bot_token = bot_token

    def parse_event(self, webhook_data: dict) -> InboundMessage:
        # Parse Telegram webhook data
        ...

    async def send_message(self, outbound: OutboundMessage) -> dict:
        # Send message via Telegram API
        ...
```

### 3. Register in API

Add to `channels.py`:

```python
elif manifest_id == "telegram":
    adapter = TelegramAdapter(
        channel_id=channel_id,
        bot_token=config["bot_token"]
    )
    _message_bus.register_adapter(channel_id, adapter)
```

### 4. Add Webhook Endpoint

Add route in `channels.py`:

```python
@router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    # Handle Telegram webhooks
    ...
```

## Styling

The wizard uses a comprehensive CSS theme defined in:
- `static/css/channels.css` - Channel cards and marketplace
- Inline styles in `ChannelSetupWizard.js` - Wizard-specific UI

### Color Scheme

```css
--primary-color: Main action color
--primary-dark: Hover states
--success-color: Success indicators
--error-color: Error states
--warning-color: Warning states
--border-color: Component borders
--bg-secondary: Subtle backgrounds
```

### Responsive Design

- Desktop: Grid layout with 3-4 columns
- Tablet: 2 columns
- Mobile: Single column, full-width wizard

## Testing

### Backend Tests

```bash
python3 test_setup_wizard.py
```

Tests:
- ✓ Manifest loading
- ✓ Configuration validation
- ✓ Manifest structure
- ✓ Serialization/deserialization

### Frontend Testing

1. Start WebUI server
2. Navigate to "Channels" in sidebar
3. Click "Setup Channel" on any channel
4. Complete all 5 steps
5. Verify:
   - Step navigation works
   - Validation catches errors
   - Test endpoint responds
   - Wizard completes successfully

### Integration Testing

Test full workflow:
1. Open wizard
2. Review channel info (Step 1)
3. Copy webhook URL (Step 2)
4. Check off setup steps (Step 3)
5. Fill configuration form (Step 4)
6. Run test (Step 5)
7. Complete setup

## Security Considerations

### Secrets Management

- Secret fields marked with `secret: true`
- Encrypted at rest in database
- Never logged or displayed after input
- Password fields use `type="password"`

### Webhook Security

- Signature verification required (configurable)
- Rate limiting per channel
- Webhook URL includes channel-specific path
- HTTPS recommended for production

### Validation

- Client-side: HTML5 + regex patterns
- Server-side: Manifest validation
- API-side: Adapter creation test
- Test endpoint: Safe credential verification

## Troubleshooting

### Wizard Not Loading

1. Check browser console for JS errors
2. Verify ChannelSetupWizard.js is loaded
3. Check /api/channels/manifests endpoint
4. Verify manifest files exist

### Validation Failing

1. Check regex patterns in manifest
2. Verify required fields are filled
3. Test validation endpoint directly
4. Check error messages in UI

### Test Failing

1. Verify credentials are correct
2. Check network connectivity
3. Review diagnostics in test result
4. Check provider API documentation

## Future Enhancements

### Planned Features

1. **Multi-variant Support:** Select between different provider implementations
2. **Lottie Animations:** Add animated guides for setup steps
3. **Live Validation:** Real-time credential verification
4. **Setup Templates:** Pre-filled configurations for common use cases
5. **Channel Health Dashboard:** Monitor active channels
6. **Bulk Operations:** Enable/disable multiple channels
7. **Configuration Export/Import:** Backup and restore channel configs

### Extension Points

- Custom setup steps per channel
- Channel-specific test implementations
- Advanced configuration UI (e.g., webhook signature setup)
- Integration with external credential stores

## Files Modified

### Backend
- `agentos/webui/api/channels.py` - Added manifest and validation endpoints
- `agentos/communicationos/registry.py` - Channel registry core
- `agentos/communicationos/manifest.py` - Manifest data models

### Frontend
- `agentos/webui/static/js/views/ChannelsView.js` - Channel marketplace
- `agentos/webui/static/js/components/ChannelSetupWizard.js` - Setup wizard
- `agentos/webui/static/css/channels.css` - Channel styling
- `agentos/webui/static/js/main.js` - View routing
- `agentos/webui/templates/index.html` - Script/style includes

### Configuration
- `agentos/communicationos/channels/whatsapp_twilio_manifest.json` - Example manifest

## Summary

The Setup Wizard provides:
✓ User-friendly channel configuration
✓ Step-by-step guided setup
✓ Real-time validation
✓ Connection testing
✓ Extensible architecture
✓ Security best practices

Status: **✅ COMPLETE** (Task #8)
