# Twilio Voice Integration - Quick Start Guide

## 5-Minute Setup

### Prerequisites
- Twilio account (free trial available)
- AgentOS running locally or deployed
- ngrok (for local testing) or public HTTPS endpoint

### Step 1: Get Twilio Phone Number (2 min)

1. Sign up at https://www.twilio.com/try-twilio
2. Go to Console → Phone Numbers → Manage → Buy a number
3. Select a number with **Voice** capability
4. Buy/activate the number

### Step 2: Start AgentOS (1 min)

```bash
# Start WebUI
agentos webui start

# Or if using uvicorn directly:
uvicorn agentos.webui.app:app --host 0.0.0.0 --port 8000
```

### Step 3: Expose Locally with ngrok (1 min)

```bash
# Install ngrok: https://ngrok.com/download
# Or: brew install ngrok (macOS)

# Start tunnel
ngrok http 8000

# Output shows:
# Forwarding: https://abc1-23-45-67-89.ngrok-free.app -> http://localhost:8000
```

**Copy the `https://` URL** (e.g., `https://abc1-23-45-67-89.ngrok-free.app`)

### Step 4: Configure Twilio Webhook (1 min)

1. Go to Twilio Console → Phone Numbers → Manage → Active Numbers
2. Click on your phone number
3. Under **Voice & Fax** section:
   - **A Call Comes In**: Select "Webhook"
   - **URL**: Paste `https://your-ngrok-url.ngrok-free.app/api/voice/twilio/inbound`
   - **HTTP Method**: POST
4. Click **Save**

### Step 5: Test the Call (30 sec)

1. Call your Twilio number from any phone
2. You'll hear: "Connecting to agent."
3. Speak naturally into the phone
4. Every ~3 seconds, your speech will be transcribed
5. Check AgentOS logs to see transcripts

## Verify It's Working

### Check Logs

```bash
# You should see:
INFO: Twilio inbound call: call_sid=CA123..., from=+1234567890
INFO: Created Twilio voice session: twilio-CA123...
INFO: Twilio Media Streams WebSocket connected: twilio-CA123...
INFO: Twilio Media Stream started: stream_sid=MZ456..., call_sid=CA123...
INFO: Transcribing 48000 bytes of audio...
INFO: Transcript: 'Hello, how are you?'
INFO: Sent assistant text to Twilio session: twilio-CA123...
```

### Check Twilio Console

1. Go to Monitor → Logs → Calls
2. Find your call
3. Click to view details
4. Check "Events" tab - should show Stream started/stopped

## Troubleshooting

### Problem: "Call cannot be completed as dialed"
**Solution**: Check webhook URL is correct and publicly accessible

### Problem: No audio received in WebSocket
**Check**:
- ngrok is running and tunnel is active
- WebSocket URL uses `wss://` (not `ws://`)
- Firewall allows WebSocket connections

### Problem: No transcription in logs
**Check**:
- Whisper model is loading (check startup logs)
- You're speaking clearly and long enough (~3 seconds)
- Audio buffer is reaching threshold

### Problem: "Session not found" in WebSocket
**Check**:
- Inbound webhook was called first
- Session ID matches between webhook and WebSocket
- Session wasn't cleaned up too quickly

## Next: Add Real AI Responses

Currently returns echo: "You said: ..."

To add real AI:

1. Edit `agentos/webui/api/voice_twilio.py`
2. Find `get_assistant_response()` function
3. Replace with:

```python
async def get_assistant_response(transcript: str, session_id: str) -> str:
    # TODO: Integrate with ChatService
    from agentos.core.chat.service import ChatService

    chat = ChatService()
    # Create or get chat session
    # Send user message
    # Get assistant response
    # Return text

    return assistant_response
```

## Production Deployment

### Required Changes

1. **Remove ngrok**, use real domain:
   ```
   https://your-domain.com/api/voice/twilio/inbound
   ```

2. **Add HTTPS** (Let's Encrypt recommended):
   ```bash
   certbot --nginx -d your-domain.com
   ```

3. **Add Redis** for session storage:
   ```bash
   pip install redis
   # Update voice_twilio.py to use Redis instead of _twilio_sessions dict
   ```

4. **Enable TTS** for responses:
   ```bash
   pip install twilio
   # Implement send_twilio_say() using Twilio REST API
   ```

5. **Add authentication** (Twilio signature verification):
   ```python
   from twilio.request_validator import RequestValidator
   # Verify X-Twilio-Signature header
   ```

## API Endpoints Reference

### Inbound Webhook
```
POST /api/voice/twilio/inbound
Content-Type: application/x-www-form-urlencoded

CallSid=CA123...
From=+14155551234
To=+14155555678
CallStatus=ringing

→ Returns TwiML XML
```

### Media Streams WebSocket
```
WSS /api/voice/twilio/stream/{session_id}

← start event (from Twilio)
← media event (audio chunks)
← stop event

→ voice.stt.final (transcripts)
→ voice.assistant.text (responses)
→ error (if any)
```

## Cost Estimates (Twilio)

- **Phone number**: $1-2/month
- **Inbound calls**: $0.0085/minute
- **Media Streams**: Included
- **Transcription** (if using Twilio): $0.05/minute (we use local Whisper, so free)

## Resources

- [Full Documentation](./TWILIO_INTEGRATION.md)
- [Twilio Media Streams Docs](https://www.twilio.com/docs/voice/media-streams)
- [AgentOS Voice Docs](./MVP.md)
- [Verification Script](../../scripts/verify_twilio_implementation.py)

## Support

Issues? Questions?
1. Check logs for errors
2. Review [TWILIO_INTEGRATION.md](./TWILIO_INTEGRATION.md)
3. Run verification: `python3 scripts/verify_twilio_implementation.py`
4. Open GitHub issue with logs and error details

---

**Setup Time**: ~5 minutes
**Cost**: Free (trial) or ~$1/month
**Next**: Integrate ChatService for real AI conversations
