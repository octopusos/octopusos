# Setup Wizard - Quick Start Guide

## For Users: Setting Up a Channel

### 1. Access the Channels View

1. Open AgentOS WebUI
2. Click **"Channels"** in the Communication section of the sidebar
3. Browse available channels in the marketplace

### 2. Start Setup

1. Find the channel you want (e.g., WhatsApp via Twilio)
2. Click **"Setup Channel"** button
3. The Setup Wizard opens

### 3. Complete the Wizard

#### Step 1: Review Channel Info (1/5)
- Review provider, capabilities, and privacy badges
- Click "Next" to continue

#### Step 2: Copy Webhook URL (2/5)
- Click the copy button next to the webhook URL
- You'll need this URL in your provider's settings
- Click "Next" to continue

#### Step 3: Follow Setup Steps (3/5)
- Read each setup step carefully
- Complete the tasks in your provider's console
- Check off each item as you complete it
- Click "Next" when all items are checked

#### Step 4: Enter Configuration (4/5)
- Fill in all required fields (marked with *)
- Secret fields (like passwords) will be encrypted
- The form validates as you type
- Click "Next" to continue

#### Step 5: Test Connection (5/5)
- Click "Run Test" button
- Wait for test results
- If test passes, click "Finish"
- If test fails, review diagnostics and fix issues

### 4. Done!

Your channel is now configured and ready to receive messages.

## For Developers: Adding a New Channel

### Quick Steps

1. **Create Manifest** (`agentos/communicationos/channels/mychannel_manifest.json`)
2. **Implement Adapter** (`agentos/communicationos/channels/mychannel.py`)
3. **Register in API** (`agentos/webui/api/channels.py`)
4. **Test** (Wizard automatically works!)

### Manifest Template

```json
{
  "id": "mychannel",
  "name": "My Channel",
  "icon": "message",
  "description": "Connect My Channel messaging platform",
  "provider": "MyProvider",
  "docs_url": "https://docs.myprovider.com",

  "required_config_fields": [
    {
      "name": "api_key",
      "label": "API Key",
      "type": "password",
      "required": true,
      "secret": true,
      "help_text": "Your API key from MyProvider dashboard"
    }
  ],

  "webhook_paths": ["/api/channels/mychannel/webhook"],

  "setup_steps": [
    {
      "title": "Get API Key",
      "description": "Create API key in provider dashboard",
      "instruction": "1. Go to dashboard\n2. Click API Keys\n3. Generate new key",
      "checklist": [
        "Created account",
        "Generated API key",
        "Copied key"
      ]
    }
  ],

  "capabilities": ["inbound_text", "outbound_text"],

  "security_defaults": {
    "mode": "chat_only",
    "rate_limit_per_minute": 20,
    "require_signature": true
  }
}
```

### Adapter Template

```python
from agentos.communicationos.channels.base import ChannelAdapter
from agentos.communicationos.models import InboundMessage, OutboundMessage

class MyChannelAdapter(ChannelAdapter):
    def __init__(self, channel_id: str, api_key: str):
        super().__init__(channel_id)
        self.api_key = api_key

    def parse_event(self, webhook_data: dict) -> InboundMessage:
        """Parse webhook data to InboundMessage."""
        return InboundMessage(
            channel_id=self.channel_id,
            message_id=webhook_data["id"],
            user_key=webhook_data["from"],
            conversation_key=webhook_data["conversation"],
            text=webhook_data["text"],
            timestamp=webhook_data["timestamp"]
        )

    async def send_message(self, outbound: OutboundMessage) -> dict:
        """Send outbound message via API."""
        # Implement API call
        pass

    def verify_webhook_signature(self, signature: str, url: str, data: dict) -> bool:
        """Verify webhook authenticity."""
        # Implement signature verification
        pass
```

## Common Issues

### Wizard Won't Open
- Check browser console for errors
- Verify JavaScript files are loaded
- Refresh the page

### Validation Errors
- Check regex patterns in manifest
- Ensure all required fields are filled
- Review field format requirements

### Test Fails
- Verify credentials are correct
- Check network connectivity
- Review provider documentation
- Check diagnostics message

### Webhook Not Receiving
- Verify webhook URL is correct
- Check provider webhook configuration
- Ensure webhook signature is valid
- Review rate limiting settings

## Tips

### For Users
- Keep credentials secure
- Test thoroughly before production use
- Monitor channel health after setup
- Check official documentation if stuck

### For Developers
- Start with the WhatsApp Twilio manifest as a template
- Test validation regex patterns carefully
- Provide clear help text for each field
- Include detailed setup steps
- Add common error diagnostics

## Support

### Documentation
- Full implementation guide: `docs/SETUP_WIZARD_IMPLEMENTATION.md`
- Test suite: `test_setup_wizard.py`
- API documentation: See inline comments in `channels.py`

### Testing
Run backend tests:
```bash
python3 test_setup_wizard.py
```

### Debugging
Enable debug logging:
```python
import logging
logging.getLogger('agentos.communicationos').setLevel(logging.DEBUG)
```

## Example: WhatsApp (Twilio) Setup

1. **Click "Setup Channel"** on WhatsApp (Twilio)
2. **Review info** → Next
3. **Copy webhook URL** → Paste in Twilio Console → Next
4. **Complete setup steps:**
   - ☑ Create Twilio account
   - ☑ Get Account SID and Auth Token
   - ☑ Request WhatsApp sender
   - ☑ Configure webhook in console
5. **Enter configuration:**
   - Account SID: `AC...`
   - Auth Token: `***`
   - Phone Number: `+14155238886`
6. **Run test** → Success! → Finish

Done! Your WhatsApp channel is now active.

## Architecture Overview

```
User → ChannelsView → Setup Wizard → API → Registry → Adapter → Provider
                          ↓
                      Manifest drives:
                      - Step content
                      - Form generation
                      - Validation rules
                      - Test logic
```

## Field Types Supported

- `text` - Single-line text input
- `password` - Password input (masked)
- `textarea` - Multi-line text input
- `select` - Dropdown selection
- `number` - Numeric input
- `url` - URL input with validation

## Validation Options

- `required` - Field must be filled
- `validation_regex` - Pattern matching
- `validation_error` - Custom error message
- `min`/`max` - Numeric ranges
- `options` - Select dropdown options

## Security Features

- ✓ Secret field encryption
- ✓ Webhook signature verification
- ✓ Rate limiting
- ✓ HTTPS recommended
- ✓ Credentials never logged
- ✓ Audit trail

## Next Steps

After completing the wizard:
1. Monitor incoming messages
2. Test sending responses
3. Configure commands (optional)
4. Set up notifications
5. Review audit logs

---

**Need Help?** Check the full documentation or run the test suite.
