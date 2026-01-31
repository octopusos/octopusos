# SMS Bidirectional Setup Guide (AgentOS + Twilio + Cloudflare)

**Goal**: Configure SMS bidirectional communication in 30 minutes

## Prerequisites

- ✅ Twilio account (with usable phone number)
- ✅ Cloudflare account (Zero Trust plan, free)
- ✅ AgentOS installed and running
- ✅ A domain name (for HTTPS configuration)

## Step 1: Configure Cloudflare Tunnel (10 minutes)

### 1.1 Create Tunnel

```bash
agentos networkos create \
  --name sms-tunnel \
  --hostname sms.your-domain.com \
  --target http://127.0.0.1:8000 \
  --token YOUR_CLOUDFLARE_TOKEN
```

**Get Cloudflare Token:**
1. Login to https://dash.cloudflare.com
2. Go to Zero Trust → Networks → Tunnels
3. Click "Create a Tunnel"
4. Copy Token (format: eyJhIjoi...)

### 1.2 Start Tunnel

```bash
agentos networkos start TUNNEL_ID
agentos networkos status TUNNEL_ID  # Confirm status=up
```

### 1.3 Verify

Visit https://sms.your-domain.com/api/health - should return AgentOS health status.

## Step 2: Configure SMS Channel (5 minutes)

### 2.1 Generate Webhook Token

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Output: abc123_XyZ789_RandomToken_32PlusChars
```

**IMPORTANT**: Save this token - you'll need it in steps 2.2 and 3.1.

### 2.2 Configure SMS Channel

In AgentOS, configure the SMS channel:

**Configuration:**
- `account_sid`: Your Twilio Account SID
- `auth_token`: Your Twilio Auth Token
- `from_number`: Your Twilio phone number (+1234567890)
- `webhook_path_token`: Token from step 2.1

**Via WebUI:**
1. Go to Channels → Add Channel
2. Select "SMS" from marketplace
3. Fill in configuration
4. Click "Save"

**Via Config File:**
```json
{
  "channel_id": "sms_prod",
  "manifest_id": "sms",
  "enabled": true,
  "config": {
    "twilio_account_sid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "twilio_auth_token": "your_32_char_auth_token",
    "twilio_from_number": "+15551234567",
    "sms_max_len": 480,
    "webhook_path_token": "abc123_XyZ789_RandomToken_32PlusChars"
  }
}
```

### 2.3 Verify Configuration

```bash
# Send test SMS (outbound)
agentos sms send +1234567890 "Hello from AgentOS"
```

You should receive the message on the specified phone.

## Step 3: Configure Twilio Webhook (10 minutes)

### 3.1 Construct Webhook URL

**Format:**
```
https://sms.your-domain.com/api/channels/sms/twilio/webhook/YOUR_PATH_TOKEN
```

**Example:**
```
https://sms.example.com/api/channels/sms/twilio/webhook/abc123_XyZ789_RandomToken_32PlusChars
```

### 3.2 Configure Twilio

1. Login to https://console.twilio.com/
2. Go to Phone Numbers → Manage → Active Numbers
3. Click your phone number
4. Scroll to "Messaging Configuration"
5. In "A MESSAGE COMES IN" section:
   - Webhook URL: Paste URL from 3.1
   - HTTP Method: **POST** (Important!)
6. Click "Save Configuration"

### 3.3 Verify Configuration

In Twilio Console:
- Status should show "Webhook configured"
- No error messages

## Step 4: Test Bidirectional SMS (5 minutes)

### 4.1 Send Test SMS

From any phone, send SMS to your Twilio number:
```
Text: "Hello AgentOS"
```

### 4.2 Verify Receipt

```bash
# View AgentOS logs
tail -f logs/agentos.log | grep SMS

# Expected output:
# [INFO] Received SMS from +1234567890: "Hello AgentOS"
# [INFO] Processing inbound SMS, MessageSid=SM...
# [INFO] Reply sent: "Thanks for your message..."
```

### 4.3 Verify Reply

Your phone should receive an automatic reply from AgentOS.

## Troubleshooting

### Q: Send SMS but get no reply

**Diagnostic Steps:**

1. Check Tunnel Status:
   ```bash
   agentos networkos status TUNNEL_ID
   # Status should be: up
   ```

2. Check Twilio Webhook Logs:
   - Go to Twilio Console → Monitor → Logs → Messaging
   - Look for recent webhook requests
   - Check response code (should be 200)

3. Check AgentOS Logs:
   ```bash
   grep "sms/twilio/webhook" logs/agentos.log
   ```

4. Verify Signature:
   ```bash
   grep "Invalid signature" logs/agentos.log
   # Should be empty
   ```

### Q: Twilio reports Webhook failed (503/404)

**Cause**: Tunnel not running or path_token incorrect

**Solution:**
```bash
# Confirm Tunnel is running
agentos networkos list

# Confirm path_token matches
grep webhook_path_token ~/.agentos/config/sms_channel.json
```

### Q: Receive SMS but no reply

**Cause**: MessageBus processing failed

**Solution:**
```bash
# View detailed error
grep ERROR logs/agentos.log | tail -20
```

### Q: Signature verification failed

**Cause**: Auth Token mismatch

**Solution:**
1. Confirm Twilio Auth Token is correct
2. Ensure webhook URL is complete (includes path_token)
3. Check URL for special characters that need encoding

## Security Checklist

- ✅ path_token is at least 32 characters random
- ✅ Auth Token is confidential (not committed to Git)
- ✅ Webhook URL uses HTTPS (Cloudflare Tunnel auto-configures)
- ✅ Regularly check Twilio logs for anomalous requests
- ✅ Test MessageSid deduplication (duplicate requests should not trigger multiple replies)

## Cost Considerations

- **Cloudflare Tunnel**: Free (Zero Trust plan)
- **Twilio SMS**: Pay-per-use (US $0.0075/message)
- **AgentOS LLM Calls**: Charged based on model used

Recommended: Set up budget alerts in Twilio.

## Architecture Overview

```
┌──────────┐                           ┌──────────┐
│  Sender  │                           │  Twilio  │
│ +1555*** │                           │  Server  │
└────┬─────┘                           └────┬─────┘
     │                                      │
     │ 1. Send SMS "Hello"                  │
     │─────────────────────────────────────>│
     │                                      │
     │                                      │ 2. POST webhook
     │                                      │    X-Twilio-Signature: hmac...
     │                                      │
     │                                      ▼
     │                           ┌──────────────────┐
     │                           │ Cloudflare Tunnel│
     │                           │  (NetworkOS)     │
     │                           └────────┬─────────┘
     │                                    │
     │                                    │ 3. Forward to AgentOS
     │                                    ▼
     │                           ┌──────────────────┐
     │                           │  AgentOS WebAPI  │
     │                           │                  │
     │                           │  1. Verify token │
     │                           │  2. Verify sig   │
     │                           │  3. Parse webhook│
     │                           │  4. Return 200   │◄─── FAST (<5ms)
     │                           └────────┬─────────┘
     │                                    │
     │                                    │ 5. Background Task
     │                                    ▼
     │                           ┌──────────────────┐
     │                           │   MessageBus     │
     │                           │  - Dedupe check  │
     │                           │  - Rate limit    │
     │                           │  - Forward chat  │
     │                           └────────┬─────────┘
     │                                    │
     │                                    │ 6. Generate reply
     │                                    ▼
     │                           ┌──────────────────┐
     │                           │   Chat Pipeline  │
     │                           └────────┬─────────┘
     │                                    │
     │                                    │ 7. Send reply
     │                                    ▼
     │                           ┌──────────────────┐
     │                           │   SmsAdapter     │
     │                           └────────┬─────────┘
     │                                    │
     │                                    │ 8. Twilio API
     │                                    ▼
     │                                ┌────────┐
     │                                │ Twilio │
     │                                └────┬───┘
     │                                     │
     │ 9. Receive reply                    │
     │<────────────────────────────────────┘
```

## Security Layers

SMS Webhook has 3 security layers:

1. **Path Token**: Random string in URL (32+ chars) - prevents URL scanning
2. **Twilio Signature**: HMAC-SHA1 verification - confirms request from Twilio
3. **MessageSid Deduplication**: Prevents replay attacks

## Next Steps

After successful setup:

1. **Configure chat integration**: Set up chat pipeline to handle SMS messages
2. **Set up monitoring**: Configure alerts for webhook failures
3. **Enable rate limiting**: Configure per-user SMS rate limits
4. **Review logs regularly**: Check for anomalous patterns

## Related Documentation

- [SMS Webhook Quick Start](/docs/SMS_WEBHOOK_QUICK_START.md)
- [NetworkOS Security Best Practices](/docs/NETWORKOS_SECURITY.md)
- [SMS Developer Integration Guide](/docs/SMS_DEVELOPER_INTEGRATION.md)
- [Twilio Security Best Practices](https://www.twilio.com/docs/usage/security)

---

**Last Updated:** 2026-02-01
**Version:** SMS Channel v2.0 + NetworkOS v1.0
**Support:** AgentOS CommunicationOS Team
