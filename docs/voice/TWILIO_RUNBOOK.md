---
title: Twilio Voice Runbook
version: v0.2
date: 2026-02-01
---

# Twilio Voice Operations Runbook

This runbook provides operational procedures for managing Twilio voice integration in production environments.

## Table of Contents

1. [Monitoring & Metrics](#monitoring--metrics)
2. [Alerting Thresholds](#alerting-thresholds)
3. [Capacity Planning](#capacity-planning)
4. [Security Configuration](#security-configuration)
5. [Cost Optimization](#cost-optimization)
6. [Incident Response](#incident-response)
7. [Common Issues & Solutions](#common-issues--solutions)
8. [Maintenance Procedures](#maintenance-procedures)

---

## Monitoring & Metrics

### Key Performance Indicators (KPIs)

| Metric | Target | Warning | Critical | Description |
|--------|--------|---------|----------|-------------|
| **Call Success Rate** | ≥99% | <98% | <95% | % of calls that successfully connect |
| **End-to-End Latency** | <500ms | >600ms | >1000ms | Time from speech to STT result |
| **STT Accuracy** | ≥95% | <90% | <85% | % of correctly transcribed words |
| **Webhook Response Time** | <200ms | >500ms | >1000ms | `/api/voice/twilio/inbound` response time |
| **WebSocket Connection Time** | <1s | >2s | >5s | Time to establish Media Streams WS |
| **Transcoding Error Rate** | <0.1% | >1% | >5% | % of audio chunks failing to transcode |
| **Daily Active Calls** | - | - | - | Total calls per day (trending) |
| **Concurrent Calls** | - | - | >80 | Current simultaneous calls (capacity) |

### Prometheus Metrics

```python
# Define metrics in voice_twilio.py
from prometheus_client import Counter, Histogram, Gauge

# Call metrics
twilio_calls_total = Counter(
    'twilio_calls_total',
    'Total Twilio voice calls',
    ['status', 'from_country']
)

twilio_call_duration = Histogram(
    'twilio_call_duration_seconds',
    'Call duration in seconds',
    buckets=[10, 30, 60, 120, 300, 600]
)

twilio_active_calls = Gauge(
    'twilio_active_calls',
    'Currently active Twilio calls'
)

# Audio metrics
twilio_audio_chunks_received = Counter(
    'twilio_audio_chunks_received_total',
    'Total audio chunks received from Twilio'
)

twilio_transcoding_errors = Counter(
    'twilio_transcoding_errors_total',
    'Total audio transcoding errors',
    ['error_type']
)

# STT metrics
twilio_stt_latency = Histogram(
    'twilio_stt_latency_seconds',
    'STT transcription latency',
    buckets=[0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
)

twilio_stt_transcript_length = Histogram(
    'twilio_stt_transcript_length_chars',
    'Length of transcribed text in characters',
    buckets=[10, 50, 100, 200, 500]
)

# WebSocket metrics
twilio_websocket_connections = Gauge(
    'twilio_websocket_connections',
    'Currently connected Twilio WebSockets'
)

twilio_websocket_errors = Counter(
    'twilio_websocket_errors_total',
    'Total WebSocket errors',
    ['error_type']
)
```

### Grafana Dashboard

Create dashboard with panels for:

**Call Volume & Status**
```promql
# Total calls per hour
rate(twilio_calls_total[1h]) * 3600

# Call success rate
sum(rate(twilio_calls_total{status="completed"}[5m]))
  /
sum(rate(twilio_calls_total[5m]))

# Active calls (real-time)
twilio_active_calls
```

**Latency & Performance**
```promql
# STT latency (p50, p95, p99)
histogram_quantile(0.50, twilio_stt_latency)
histogram_quantile(0.95, twilio_stt_latency)
histogram_quantile(0.99, twilio_stt_latency)

# Webhook response time
histogram_quantile(0.95, http_request_duration_seconds{
  endpoint="/api/voice/twilio/inbound"
})
```

**Errors & Failures**
```promql
# Transcoding error rate
rate(twilio_transcoding_errors_total[5m])

# WebSocket disconnects
rate(twilio_websocket_errors_total{error_type="disconnect"}[5m])

# STT failures
rate(twilio_stt_errors_total[5m])
```

### Log Queries (Splunk/ELK)

```
# Find failed calls
index=agentos source=*voice_twilio.py* level=ERROR
| stats count by call_sid, error_message

# Analyze STT latency
index=agentos source=*voice_twilio.py* "STT latency"
| rex field=_raw "latency=(?<latency>\d+)ms"
| stats avg(latency) p50(latency) p95(latency) p99(latency)

# Track calls by phone number
index=agentos source=*voice_twilio.py* "Twilio inbound call"
| rex field=_raw "from=(?<from_number>\+\d+)"
| stats count by from_number
| sort -count

# Identify rate-limited callers
index=agentos level=WARNING "Rate limit exceeded"
| rex field=_raw "from_number=(?<from_number>\+\d+)"
| stats count by from_number
```

---

## Alerting Thresholds

### Critical Alerts (PagerDuty)

**High Error Rate**
```yaml
alert: TwilioHighErrorRate
expr: rate(twilio_calls_total{status="failed"}[5m]) / rate(twilio_calls_total[5m]) > 0.05
for: 5m
labels:
  severity: critical
annotations:
  summary: "Twilio error rate >5% for 5 minutes"
  description: "{{ $value | humanizePercentage }} of calls failing"
  runbook: https://docs.agentos.dev/voice/runbook#high-error-rate
```

**Webhook Unavailable**
```yaml
alert: TwilioWebhookDown
expr: up{job="agentos_webui"} == 0
for: 1m
labels:
  severity: critical
annotations:
  summary: "Twilio webhook endpoint is down"
  description: "Inbound calls will fail"
  runbook: https://docs.agentos.dev/voice/runbook#webhook-down
```

**High Latency**
```yaml
alert: TwilioHighLatency
expr: histogram_quantile(0.95, twilio_stt_latency) > 1.0
for: 10m
labels:
  severity: critical
annotations:
  summary: "STT latency >1s (p95) for 10 minutes"
  description: "User experience degraded"
```

### Warning Alerts (Slack)

**Approaching Capacity**
```yaml
alert: TwilioHighConcurrentCalls
expr: twilio_active_calls > 80
for: 5m
labels:
  severity: warning
annotations:
  summary: "Concurrent Twilio calls >80"
  description: "Approaching account limit (100)"
  action: "Review capacity and consider upgrade"
```

**Transcoding Errors**
```yaml
alert: TwilioTranscodingErrors
expr: rate(twilio_transcoding_errors_total[5m]) > 0.01
for: 10m
labels:
  severity: warning
annotations:
  summary: "Audio transcoding errors detected"
  description: "{{ $value }} errors/sec"
```

**Unusual Call Volume**
```yaml
alert: TwilioUnusualCallVolume
expr: |
  abs(
    rate(twilio_calls_total[1h])
    - avg_over_time(rate(twilio_calls_total[1h])[7d:1h])
  ) > 2 * stddev_over_time(rate(twilio_calls_total[1h])[7d:1h])
for: 30m
labels:
  severity: warning
annotations:
  summary: "Call volume deviates >2σ from 7-day average"
  description: "Possible attack or campaign"
```

---

## Capacity Planning

### Twilio Account Limits

| Resource | Limit (Standard) | Limit (Enterprise) | Upgrade Path |
|----------|------------------|-------------------|--------------|
| **Concurrent Calls** | 100 | Custom | Contact Twilio Sales |
| **Calls/Second** | 10 | Custom | Submit support ticket |
| **Phone Numbers** | Unlimited | Unlimited | - |
| **Call Recording Storage** | 1 year | Custom | Configure S3 export |

### AgentOS Server Capacity

**Per-Instance Limits:**
- **Concurrent WebSockets**: 1000 (FastAPI/uvicorn default)
- **STT Processing**: 10-20 concurrent (CPU-bound, depends on model)
- **Memory per Call**: ~50 MB (audio buffer + model)

**Scaling Guidelines:**

| Concurrent Calls | CPU Cores | Memory | STT Workers | Notes |
|------------------|-----------|--------|-------------|-------|
| 1-10 | 2 | 4 GB | 1 | Development |
| 10-50 | 4 | 8 GB | 2 | Small production |
| 50-100 | 8 | 16 GB | 4 | Medium production |
| 100-500 | 16+ | 32 GB+ | 8+ | Large production, load balancer required |

### Cost Projections

**Example Monthly Costs (US numbers):**

| Calls/Day | Avg Duration | Minutes/Month | Twilio Cost | Total Monthly |
|-----------|--------------|---------------|-------------|---------------|
| 10 | 3 min | 900 | ~$11 | ~$12 (with number) |
| 100 | 3 min | 9,000 | ~$108 | ~$109 |
| 1,000 | 3 min | 90,000 | ~$1,080 | ~$1,081 |
| 10,000 | 3 min | 900,000 | ~$10,800 | ~$10,801 |

**Cost breakdown:**
- Phone number: $1/month (US local)
- Inbound calls: $0.0085/minute (US)
- Outbound calls: $0.013/minute (US)

---

## Security Configuration

### 1. Webhook Signature Verification

Verify requests are from Twilio (prevents spoofing):

```python
from twilio.request_validator import RequestValidator

def verify_twilio_signature(request: Request) -> bool:
    """Verify Twilio webhook request signature.

    Twilio signs all webhook requests with HMAC-SHA1.
    This prevents attackers from spoofing webhook calls.
    """
    validator = RequestValidator(os.getenv("TWILIO_AUTH_TOKEN"))

    # Get signature from header
    signature = request.headers.get("X-Twilio-Signature", "")

    # Build full URL
    url = str(request.url)

    # Get POST parameters
    params = dict(await request.form())

    # Verify signature
    return validator.validate(url, params, signature)

# In webhook handler:
@router.post("/api/voice/twilio/inbound")
async def twilio_inbound_call(request: Request):
    # Verify signature
    if not verify_twilio_signature(request):
        logger.warning("Invalid Twilio signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Process webhook...
```

### 2. IP Whitelisting (Optional)

Restrict webhook access to Twilio IP ranges:

```nginx
# nginx.conf
location /api/voice/twilio/ {
    # Twilio IP ranges (as of 2026)
    allow 54.172.60.0/23;
    allow 54.244.51.0/24;
    allow 54.171.127.192/26;
    # ... (see https://www.twilio.com/docs/voice/ip-addresses)

    deny all;

    proxy_pass http://agentos_backend;
}
```

### 3. Rate Limiting

Implemented in `VoicePolicy`:

```python
# Per-phone-number rate limit
CALLS_PER_HOUR_LIMIT = 10

# Adjust based on use case:
# - Customer service: 20-50 calls/hour
# - Emergency hotline: No limit (or very high)
# - Marketing: 5-10 calls/hour
```

### 4. Admin Token for High-Risk Operations

```python
# Required for operations accessing sensitive data
ADMIN_TOKEN_FORMAT = "admin-{random_string}"
ADMIN_TOKEN_MIN_LENGTH = 20

# Example: admin-7f8a9b2c3d4e5f6g7h8i
```

### 5. TLS/HTTPS Requirements

- ✅ All webhooks must use HTTPS (Twilio requirement)
- ✅ WebSockets must use WSS (secure WebSocket)
- ✅ Minimum TLS 1.2 (1.3 recommended)

---

## Cost Optimization

### 1. Right-Size Call Duration

```python
# Implement call timeout to prevent long-running calls
MAX_CALL_DURATION = timedelta(minutes=5)

# In WebSocket handler:
async def check_call_timeout(session: VoiceSession, websocket: WebSocket):
    """Terminate call if exceeds max duration."""
    duration = utc_now() - session.created_at
    if duration > MAX_CALL_DURATION:
        logger.info(f"Call timeout: {session.session_id} ({duration})")
        await websocket.close()
        return True
    return False
```

### 2. Choose Cost-Effective Numbers

| Number Type | Monthly Cost | Best For |
|-------------|--------------|----------|
| **Local** | $1.00 | Single-region service |
| **Toll-Free** | $2.00 | National hotlines |
| **Mobile** | $1.00 | SMS + Voice |
| **Short Code** | $1,000 | High-volume SMS (not voice) |

### 3. Minimize Recording Usage

```python
# Only record calls when necessary
RECORD_CALLS = os.getenv("TWILIO_RECORD_CALLS", "false").lower() == "true"

# Recording adds $0.0025/minute
# For 1000 minutes/month: $2.50 extra
```

### 4. Monitor for Fraud

```python
# Detect unusual patterns:
# - Calls to expensive international destinations
# - High call volume from single number
# - Calls outside business hours

def detect_fraud_patterns(from_number: str, to_number: str) -> bool:
    """Check for fraud indicators."""
    # Block premium-rate numbers (e.g., 900 numbers)
    if to_number.startswith("+1900"):
        return True

    # Check call rate from this number
    call_count = get_call_count_last_hour(from_number)
    if call_count > 20:  # Unusually high
        return True

    return False
```

### 5. Set Budget Alerts

In Twilio Console:
1. Go to **Usage → Triggers**
2. Create trigger:
   - **Usage**: Total Cost
   - **Threshold**: $100 (adjust for your budget)
   - **Alert**: Email/SMS/Webhook

---

## Incident Response

### High Error Rate

**Symptoms:**
- >5% of calls failing to connect
- "Session not found" errors
- Webhook timeouts

**Diagnosis:**
```bash
# Check webhook health
curl -X POST https://your-domain.com/api/voice/twilio/inbound \
  -d "CallSid=TEST" -d "From=+1234567890" -d "To=+0987654321"

# Check recent errors
tail -f /var/log/agentos/webui.log | grep ERROR

# Check metrics
curl http://localhost:9090/metrics | grep twilio_calls_total
```

**Resolution:**
1. Verify AgentOS is running: `systemctl status agentos-webui`
2. Check server resources: `top`, `df -h`, `free -m`
3. Restart service: `systemctl restart agentos-webui`
4. Check Twilio status: https://status.twilio.com/

### Webhook Timeout

**Symptoms:**
- Twilio webhook requests timing out (>10s)
- Calls immediately disconnecting

**Diagnosis:**
```bash
# Test webhook response time
time curl -X POST https://your-domain.com/api/voice/twilio/inbound \
  -d "CallSid=TEST" -d "From=+1234567890" -d "To=+0987654321"

# Should complete in <200ms
```

**Resolution:**
1. Check database latency (session creation)
2. Optimize TwiML generation (pre-generate if possible)
3. Scale horizontally (add more instances)
4. Enable caching for static responses

### WebSocket Connection Failures

**Symptoms:**
- "WebSocket connection failed" errors
- Audio not streaming

**Diagnosis:**
```bash
# Test WebSocket endpoint
wscat -c wss://your-domain.com/api/voice/twilio/stream/test-session

# Check WebSocket connections
netstat -an | grep :8000 | grep ESTABLISHED | wc -l
```

**Resolution:**
1. Verify WebSocket route is exposed
2. Check load balancer WebSocket support
3. Increase WebSocket timeout (nginx: `proxy_read_timeout 3600s;`)
4. Check firewall rules allow WebSocket (port 8000/443)

### STT Latency Spike

**Symptoms:**
- STT taking >2 seconds
- Users experiencing long delays

**Diagnosis:**
```bash
# Check Whisper model status
curl http://localhost:8000/api/voice/health

# Check CPU usage
mpstat 1 10

# Check memory
free -m
```

**Resolution:**
1. Use faster model: `base` instead of `large`
2. Enable GPU acceleration (if available)
3. Scale STT workers horizontally
4. Pre-load models on startup (avoid cold-start)

---

## Common Issues & Solutions

### Issue: "Invalid signature" Error

**Cause:** Twilio signature verification failing

**Solution:**
1. Verify `TWILIO_AUTH_TOKEN` is correct
2. Check webhook URL matches exactly (including protocol, path, query params)
3. Ensure POST parameters are being validated correctly

### Issue: Call Connects but No Audio

**Cause:** WebSocket not connecting or audio not streaming

**Solution:**
1. Check Media Streams are enabled in Twilio Console
2. Verify WebSocket URL is correct (wss://, not ws://)
3. Test WebSocket manually: `wscat -c wss://your-domain.com/...`
4. Check audio transcoding: Enable debug logs

### Issue: STT Returns Empty Transcripts

**Cause:** Audio quality too low or silence detected

**Solution:**
1. Check audio buffer size (should be ≥48000 bytes)
2. Verify μ-law transcoding is working correctly
3. Test with known audio sample
4. Adjust VAD (Voice Activity Detection) thresholds

### Issue: Rate Limit Exceeded

**Cause:** Phone number exceeds 10 calls/hour limit

**Solution:**
1. Review call patterns: Legitimate user or abuse?
2. Increase limit if legitimate: `policy.calls_per_hour_limit = 20`
3. Blacklist number if abuse: Add to `BLOCKED_NUMBERS` list
4. Implement CAPTCHA for suspicious patterns

---

## Maintenance Procedures

### Updating Twilio Webhook URL

```bash
# Use Twilio CLI
twilio phone-numbers:update +14155551234 \
  --voice-url https://new-domain.com/api/voice/twilio/inbound

# Or via Console:
# 1. Go to Phone Numbers → Active Numbers
# 2. Click your number
# 3. Update "A Call Comes In" URL
# 4. Save
```

### Rotating Auth Token

```bash
# 1. Generate new auth token in Twilio Console
# 2. Update environment variable
export TWILIO_AUTH_TOKEN="new_token_here"

# 3. Restart service
systemctl restart agentos-webui

# 4. Verify
curl -X POST https://your-domain.com/api/voice/twilio/inbound \
  -d "CallSid=TEST" -d "From=+1234567890" -d "To=+0987654321"
```

### Upgrading Twilio Account

```bash
# Contact Twilio Sales for:
# - Higher concurrent call limit (>100)
# - Higher calls/second rate (>10)
# - Custom pricing for high volume
# - Enterprise SLA (99.99% uptime)

# Via Console:
# 1. Go to Console → Billing
# 2. Click "Upgrade to Paid Account"
# 3. Add payment method
```

### Database Cleanup (Call History)

```python
# Clean up old call history (>30 days)
from datetime import timedelta

def cleanup_old_call_history():
    """Remove call history older than 30 days."""
    cutoff = utc_now() - timedelta(days=30)

    for from_number in list(policy.call_history.keys()):
        policy.call_history[from_number] = [
            ts for ts in policy.call_history[from_number]
            if datetime.fromtimestamp(ts) > cutoff
        ]

        # Remove empty entries
        if not policy.call_history[from_number]:
            del policy.call_history[from_number]

# Run daily via cron:
# 0 2 * * * python -c "from cleanup import cleanup_old_call_history; cleanup_old_call_history()"
```

---

## References

- [Twilio Status Page](https://status.twilio.com/)
- [Twilio Support](https://support.twilio.com/)
- [AgentOS Voice Docs](./MVP.md)
- [Twilio Best Practices](https://www.twilio.com/docs/voice/best-practices)

---

*Last Updated: 2026-02-01*
*Version: v0.2*
*Next Review: 2026-03-01*
