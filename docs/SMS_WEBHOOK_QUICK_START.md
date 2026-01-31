# SMS Webhook Quick Start Guide

**Version:** SMS Channel v2.0.0 (Bidirectional)
**Last Updated:** 2026-02-01

---

## 🚀 Quick Setup (5 Minutes)

### 1. Generate Webhook Path Token

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Example Output:**
```
abc123_XyZ789_RandomToken_32PlusChars
```

⚠️ **Save this token securely** - you'll need it in steps 3 and 4.

---

### 2. Configure SMS Channel in AgentOS

**Channel Config:**
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

**CLI:**
```bash
agentos channel enable sms_prod
```

---

### 3. Configure Twilio Webhook

**URL Format:**
```
https://YOUR_DOMAIN.com/api/channels/sms/twilio/webhook/YOUR_PATH_TOKEN
```

**Example:**
```
https://app.example.com/api/channels/sms/twilio/webhook/abc123_XyZ789_RandomToken_32PlusChars
```

**Twilio Console Steps:**
1. Go to: https://console.twilio.com
2. Navigate: Phone Numbers → Manage → Active Numbers
3. Click your SMS-enabled phone number
4. Scroll to: **Messaging Configuration**
5. Set **"A MESSAGE COMES IN"**:
   - Webhook URL: (paste URL above)
   - HTTP Method: **POST**
6. Click **Save**

---

### 4. Test Inbound SMS

**Send Test Message:**
```
From any phone, send SMS to: +15551234567
Message: "Hello AgentOS"
```

**Check Logs:**
```bash
tail -f logs/agentos.log | grep SMS
```

**Expected Output:**
```
INFO Received SMS webhook: path_token=abc12345...
INFO Twilio signature verified for SMS channel: sms_prod
INFO Received SMS: from=+1******9876, to=+1******4567, length=13
INFO SMS webhook acknowledged: MessageSid=SM...
INFO Forwarding SMS to chat pipeline
```

✅ **Success!** Your SMS channel is now bidirectional.

---

## 🔐 Security Architecture

### Two-Layer Defense

```
┌─────────────────┐
│  Twilio Server  │
└────────┬────────┘
         │
         │ POST /api/channels/sms/twilio/webhook/{path_token}
         │ Header: X-Twilio-Signature
         │
         ▼
┌────────────────────────────────────────┐
│  Layer 1: Path Token Verification      │
│  - Check {path_token} in URL           │
│  - 32+ char random string              │
│  - Prevents URL scanning               │
└────────┬───────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│  Layer 2: Signature Verification       │
│  - HMAC-SHA1(auth_token, url+params)  │
│  - Constant-time comparison            │
│  - Prevents spoofing & timing attacks  │
└────────┬───────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│  Deduplication (MessageSid)            │
│  - In-memory set (10,000 limit)        │
│  - Prevents duplicate processing       │
└────────┬───────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│  MessageBus Processing                 │
│  - Rate limiting                       │
│  - Audit logging                       │
│  - Command detection                   │
│  - Chat forwarding                     │
└────────────────────────────────────────┘
```

---

## 📋 Webhook Flow Diagram

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
     │                                      │    /api/channels/sms/twilio/webhook/TOKEN
     │                                      │    X-Twilio-Signature: hmac...
     │                                      │    MessageSid=SM123&From=+1555...
     │                                      │
     │                                      ▼
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
     │                           │                  │
     │                           │  - Dedupe check  │
     │                           │  - Rate limit    │
     │                           │  - Audit log     │
     │                           └────────┬─────────┘
     │                                    │
     │                                    │ 6. Forward to chat
     │                                    ▼
     │                           ┌──────────────────┐
     │                           │  Chat Pipeline   │
     │                           │                  │
     │                           │  - LLM process   │
     │                           │  - Generate reply│
     │                           └────────┬─────────┘
     │                                    │
     │                                    │ 7. Send reply
     │                                    ▼
     │                           ┌──────────────────┐
     │                           │   SmsAdapter     │
     │                           │                  │
     │                           │  handle_outbound │
     │                           └────────┬─────────┘
     │                                    │
     │                                    │ 8. Twilio API
     │                                    ▼
     │                                ┌────────┐
     │                                │ Twilio │
     │                                └────┬───┘
     │                                     │
     │ 9. Receive reply "Thanks!"          │
     │<────────────────────────────────────┘
     │
```

---

## 🧪 Testing Checklist

### Unit Tests
```bash
python3 -m pytest tests/integration/communicationos/test_sms_inbound.py -v
```

**Expected:**
```
16 passed in 0.13s
```

### Integration Tests

#### Test 1: Valid Webhook
```bash
curl -X POST https://YOUR_DOMAIN/api/channels/sms/twilio/webhook/YOUR_TOKEN \
  -H "X-Twilio-Signature: COMPUTED_SIGNATURE" \
  -d "MessageSid=SM123&From=+15559876543&To=+15551234567&Body=Test"
```

**Expected:** `200 OK`

#### Test 2: Invalid Token
```bash
curl -X POST https://YOUR_DOMAIN/api/channels/sms/twilio/webhook/WRONG_TOKEN \
  -d "MessageSid=SM123&From=+15559876543&To=+15551234567&Body=Test"
```

**Expected:** `404 Not Found`

#### Test 3: Missing Signature
```bash
curl -X POST https://YOUR_DOMAIN/api/channels/sms/twilio/webhook/YOUR_TOKEN \
  -d "MessageSid=SM123&From=+15559876543&To=+15551234567&Body=Test"
```

**Expected:** `401 Unauthorized`

#### Test 4: Duplicate MessageSid
```bash
# Send same MessageSid twice
curl -X POST ... -d "MessageSid=SM123..."  # First: processed
curl -X POST ... -d "MessageSid=SM123..."  # Second: ignored (200 OK but not processed)
```

**Expected:** Both return `200 OK`, but only first is processed.

---

## 🐛 Troubleshooting

### Issue: "404 Not Found"

**Cause:** Invalid path token

**Fix:**
1. Check `webhook_path_token` in channel config
2. Ensure Twilio webhook URL matches exactly
3. Regenerate token if needed

### Issue: "401 Unauthorized"

**Cause:** Signature verification failed

**Fix:**
1. Check `twilio_auth_token` in channel config
2. Ensure webhook URL is exact (Twilio signs the URL too)
3. Check for URL encoding issues

### Issue: "Duplicate MessageSid"

**Cause:** Twilio retried webhook (normal behavior)

**Fix:**
- No action needed (idempotent deduplication prevents duplicates)
- Check logs to confirm first message was processed

### Issue: No reply sent

**Cause:** Chat pipeline not configured or error

**Fix:**
1. Check logs for processing errors
2. Verify chat integration is enabled
3. Check command processor is running

---

## 📊 Monitoring

### Key Metrics

```bash
# Webhook requests per minute
grep "Received SMS webhook" logs/agentos.log | tail -100

# Signature verification failures
grep "Invalid Twilio signature" logs/agentos.log

# Duplicate messages (normal)
grep "Duplicate MessageSid" logs/agentos.log

# Processing errors
grep "Failed to process SMS inbound" logs/agentos.log
```

### Healthy System Indicators

✅ Signature verification success rate: 100%
✅ Webhook response time: <5ms
✅ Duplicate rate: <5% (Twilio retries)
✅ Processing errors: 0%

---

## 🔧 Advanced Configuration

### Custom Max Length

```json
{
  "sms_max_len": 1600  // Up to ~10 SMS segments
}
```

**Cost Warning:** Longer messages = more segments = higher cost.

### Webhook URL with Custom Domain

```
https://sms.example.com/webhook/YOUR_TOKEN
```

**Requirements:**
- DNS configured
- HTTPS enabled (required by Twilio)
- Valid SSL certificate

### Multiple SMS Channels

```json
[
  {
    "channel_id": "sms_support",
    "twilio_from_number": "+15551111111",
    "webhook_path_token": "token_for_support_channel"
  },
  {
    "channel_id": "sms_marketing",
    "twilio_from_number": "+15552222222",
    "webhook_path_token": "token_for_marketing_channel"
  }
]
```

**Note:** Each channel needs unique `webhook_path_token`.

---

## 📚 API Reference

### Webhook Request

**Endpoint:**
```
POST /api/channels/sms/twilio/webhook/{path_token}
```

**Headers:**
```
X-Twilio-Signature: base64_encoded_hmac_sha1
Content-Type: application/x-www-form-urlencoded
```

**Body (Form-Encoded):**
```
MessageSid=SM1234567890abcdef1234567890abcdef
From=+15559876543
To=+15551234567
Body=Hello, this is a test SMS!
NumMedia=0
NumSegments=1
```

**Response:**
```
200 OK
(empty body)
```

### Signature Algorithm

**Python:**
```python
import hmac
import hashlib
import base64

def compute_signature(url, params, auth_token):
    data = url + ''.join(f"{k}{v}" for k, v in sorted(params.items()))
    sig = hmac.new(
        auth_token.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha1
    ).digest()
    return base64.b64encode(sig).decode('ascii')
```

**Example:**
```python
url = "https://example.com/webhook/token123"
params = {"From": "+1234", "To": "+5678", "Body": "Hi"}
auth_token = "your_auth_token"

signature = compute_signature(url, params, auth_token)
# Send as X-Twilio-Signature header
```

---

## 🎯 Best Practices

### 1. Token Security

✅ **Do:**
- Generate 32+ character random tokens
- Use `secrets.token_urlsafe()` (not `random`)
- Store in encrypted config
- Rotate tokens periodically

❌ **Don't:**
- Use predictable tokens (e.g., "webhook123")
- Commit tokens to git
- Share tokens across channels
- Reuse tokens from other services

### 2. Error Handling

✅ **Do:**
- Return 200 OK even on processing errors (prevents Twilio retry storm)
- Log all errors with context
- Monitor duplicate rate (normal: <5%)
- Set up alerts for signature failures

❌ **Don't:**
- Return 500 on processing errors (causes retries)
- Ignore signature verification failures
- Process duplicates (wastes resources)

### 3. Performance

✅ **Do:**
- Return 200 OK in <5ms
- Use background tasks for processing
- Monitor webhook latency
- Prune old MessageSids automatically

❌ **Don't:**
- Do heavy processing in webhook handler
- Block waiting for chat response
- Let MessageSid set grow unbounded

---

## 🔗 Related Documentation

- [SMS Channel Manifest](/agentos/communicationos/channels/sms/manifest.json)
- [SMS Adapter Implementation](/agentos/communicationos/channels/sms/adapter.py)
- [Integration Tests](/tests/integration/communicationos/test_sms_inbound.py)
- [Full Implementation Report](/SMS_INBOUND_WEBHOOK_IMPLEMENTATION_REPORT.md)
- [Twilio Webhook Security](https://www.twilio.com/docs/usage/security#validating-requests)

---

## ❓ FAQ

**Q: Does webhook configuration break send-only mode?**
A: No. Webhook is optional. Channel works as send-only if webhook not configured.

**Q: What happens if Twilio retries webhook?**
A: Deduplication prevents duplicate processing. Both requests return 200 OK.

**Q: Can I use ngrok for development?**
A: Yes. Twilio accepts ngrok URLs. Use HTTPS (free tier includes SSL).

**Q: What's the webhook timeout?**
A: Twilio times out after 15 seconds. We respond in <5ms (well under limit).

**Q: How do I debug signature failures?**
A: Check logs for computed vs received signature. Ensure URL is exact (including protocol, domain, path).

**Q: Can I send MMS (media)?**
A: Not in v2. Only text messages supported. MMS planned for v3.

**Q: What if I lose MessageSid deduplication state?**
A: In-memory set is lost on restart. Consider Redis for production. Twilio rarely retries beyond a few minutes.

---

**Last Updated:** 2026-02-01
**Version:** SMS Channel v2.0.0
**Support:** AgentOS CommunicationOS Team
