# NetworkOS + SMS Quick Reference Card

**Version:** 1.0
**Last Updated:** 2026-02-01

---

## 30-Second Overview

NetworkOS manages public tunnels (Cloudflare) for local services. Use it to expose AgentOS webhooks for SMS bidirectional communication.

---

## Essential Commands

### NetworkOS Tunnel Management

```bash
# Create tunnel
agentos networkos create --name NAME --hostname DOMAIN --target URL --token TOKEN

# Start tunnel
agentos networkos start TUNNEL_ID

# Check status
agentos networkos list
agentos networkos status TUNNEL_ID

# View logs
agentos networkos logs TUNNEL_ID

# Stop tunnel
agentos networkos stop TUNNEL_ID
```

### Health Check

```bash
# Check NetworkOS health
agentos doctor
# Look for: ✅ networkos - NetworkOS database healthy
```

---

## SMS Setup Checklist

- [ ] Install cloudflared: `brew install cloudflared`
- [ ] Get Cloudflare token from Zero Trust dashboard
- [ ] Create tunnel: `agentos networkos create ...`
- [ ] Start tunnel: `agentos networkos start TUNNEL_ID`
- [ ] Generate webhook token: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`
- [ ] Configure SMS channel in AgentOS
- [ ] Configure Twilio webhook URL
- [ ] Test: Send SMS to Twilio number
- [ ] Verify: Check logs: `tail -f logs/agentos.log | grep SMS`

---

## Webhook URL Format

```
https://YOUR_DOMAIN/api/channels/sms/twilio/webhook/PATH_TOKEN
```

**Example:**
```
https://sms.example.com/api/channels/sms/twilio/webhook/abc123_XyZ789_RandomToken
```

---

## Troubleshooting Quick Fixes

### Webhook returns 404
```bash
# Check path_token matches
grep webhook_path_token ~/.agentos/config/sms_channel.json
```

### Webhook returns 401
```bash
# Verify auth_token
grep twilio_auth_token ~/.agentos/config/sms_channel.json
# Check logs for signature errors
grep "Invalid signature" logs/agentos.log
```

### Tunnel not running
```bash
# Check tunnel status
agentos networkos list
# Restart if needed
agentos networkos start TUNNEL_ID
```

### No SMS received
```bash
# Check logs
tail -f logs/agentos.log | grep SMS
# Check Twilio logs
# Go to: https://console.twilio.com → Monitor → Logs
```

---

## Security Checklist

- [ ] path_token is 32+ characters random
- [ ] auth_token not in Git: `git grep -i auth_token` (should be empty)
- [ ] HTTPS enabled (automatic with Cloudflare)
- [ ] Signature verification enabled (default)
- [ ] MessageSid deduplication enabled (default)
- [ ] Regular log review: `agentos networkos logs TUNNEL_ID`

---

## Emergency Procedures

### Token Leaked
```bash
# 1. Generate new token
NEW_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# 2. Update config
agentos config set sms.webhook_path_token "$NEW_TOKEN"

# 3. Update Twilio webhook URL

# 4. Check logs for anomalous access
agentos networkos logs TUNNEL_ID --since 24h
```

### Tunnel Down
```bash
# 1. Stop tunnel
agentos networkos stop TUNNEL_ID

# 2. Check logs
agentos networkos logs TUNNEL_ID

# 3. Restart
agentos networkos start TUNNEL_ID
```

---

## Key Files

| File | Purpose |
|------|---------|
| `/agentos/networkos/README.md` | NetworkOS user guide |
| `/docs/SMS_BIDIRECTIONAL_SETUP.md` | 30-min setup guide |
| `/docs/NETWORKOS_SECURITY.md` | Security best practices |

---

## Important URLs

- **Cloudflare Zero Trust**: https://dash.cloudflare.com
- **Twilio Console**: https://console.twilio.com
- **Twilio Webhook Logs**: https://console.twilio.com/monitor/logs/messaging

---

## Support

- Documentation: `/docs/`
- CLI Help: `agentos networkos --help`
- Health Check: `agentos doctor`
- Logs: `tail -f logs/agentos.log`

---

**Print this card for quick reference during setup**
