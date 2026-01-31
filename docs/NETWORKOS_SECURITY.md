# NetworkOS + SMS Security Best Practices

## Core Principles

### 1. Separation of Concerns

- **NetworkOS**: Only handles network layer forwarding, doesn't inspect business content
- **SMS Channel**: Handles protocol validation (signature) and deduplication
- **MessageBus**: Handles business logic and auditing

### 2. Minimal Exposure

- Only expose necessary webhook endpoints
- Use random path_token to prevent URL scanning
- Configure Tunnel precisely to path (don't forward entire site)

### 3. Defense in Depth

SMS Webhook has 3 security layers:

1. **Path Token**: Random string in URL (32+ chars)
2. **Twilio Request Signature**: Validates request authenticity via X-Twilio-Signature header
3. **MessageSid Deduplication**: Prevents replay attacks

## Secrets Management

### ✅ Current Implementation (Schema v55+)

**NetworkOS now uses secret_ref pattern:**

- Database stores only a reference key (e.g., `networkos:tunnel:abc123`)
- Actual tokens stored in encrypted secure storage (`~/.agentos/secrets.json`)
- File permissions enforced to 0600 (owner read/write only)
- Diagnostic bundles never export secrets
- Logs never print plaintext tokens

### Migration from v54 (Legacy Plaintext Storage)

If you're upgrading from v54 and have existing tunnels:

```bash
# Check migration status
agentos networkos migrate-secrets --check

# Migrate all tunnels to secure storage
agentos networkos migrate-secrets

# Migrate specific tunnel
agentos networkos migrate-secrets TUNNEL_ID

# Verify migration completed
agentos networkos migrate-secrets --check
```

**Migration is automatic and safe:**
- Old tokens preserved during migration (backward compatibility)
- Migration can be run multiple times (idempotent)
- No downtime required
- Automatic rollback if migration fails

### Security Architecture (v55+)

```
┌─────────────────────────────────────────────────┐
│ NetworkOS Database (networkos/db.sqlite)        │
│ ┌─────────────────────────────────────────────┐ │
│ │ tunnel_secrets table                        │ │
│ │ ┌───────────┬──────────────┬─────────────┐ │ │
│ │ │ tunnel_id │ secret_ref   │ is_migrated │ │ │
│ │ ├───────────┼──────────────┼─────────────┤ │ │
│ │ │ cf-abc    │ networkos:.. │ 1           │ │ │
│ │ └───────────┴──────────────┴─────────────┘ │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
                      ↓
                  (reference)
                      ↓
┌─────────────────────────────────────────────────┐
│ Secure Storage (~/.agentos/secrets.json)        │
│ ┌─────────────────────────────────────────────┐ │
│ │ {                                           │ │
│ │   "networkos:tunnel:cf-abc": {             │ │
│ │     "api_key": "eyJhbGci...",  ← encrypted │ │
│ │     "updated_at": "2026-02-01T..."         │ │
│ │   }                                         │ │
│ │ }                                           │ │
│ └─────────────────────────────────────────────┘ │
│ Permissions: 0600 (owner read/write only)       │
└─────────────────────────────────────────────────┘
```

### ❌ Don't Do (Security Anti-patterns)

- Commit tokens to Git
- Print complete tokens in logs
- Store secrets in plaintext in DB (v54 pattern)
- Include secrets in diagnostic exports
- Share secrets via unencrypted channels

### ✅ Do (Security Best Practices)

- Use secret_ref pattern (v55+)
- Migrate legacy tunnels ASAP
- Only log redacted forms (`***abc1`)
- Enforce 0600 permissions on secrets file
- Auto-redact secrets in diagnostic exports
- Rotate tokens periodically (every 90 days)

### Verification Commands

```bash
# Check if any tunnels still use legacy storage
agentos networkos migrate-secrets --check

# Verify secrets file permissions (Unix-like systems)
ls -l ~/.agentos/secrets.json
# Should show: -rw------- (0600)

# Check for tokens in database (should be empty after migration)
sqlite3 ~/.agentos/store/networkos/db.sqlite \
  "SELECT COUNT(*) as legacy_count FROM tunnel_secrets WHERE is_migrated = 0;"

# Verify secret references (should show references, not tokens)
sqlite3 ~/.agentos/store/networkos/db.sqlite \
  "SELECT tunnel_id, secret_ref FROM tunnel_secrets WHERE is_migrated = 1 LIMIT 5;"
```

### Backward Compatibility

Schema v55 maintains backward compatibility for 1 release cycle:

- ✅ Legacy tunnels (plaintext token) still work
- ⚠️  Warning logged when accessing legacy token
- 📅 token column will be removed in v0.next (after grace period)
- 🔄 Recommended: Migrate ASAP

### Secure Storage Integration

NetworkOS uses AgentOS secure storage module:

- **Storage backend**: `~/.agentos/secrets.json`
- **Encryption**: File-level encryption (0600 permissions)
- **Access control**: Owner-only read/write
- **Audit trail**: All accesses logged to network_events

For custom secure storage providers:
```python
from agentos.networkos.service import NetworkOSService

def custom_save_fn(key: str, value: str):
    # Your custom secure storage implementation
    # Examples: AWS Secrets Manager, HashiCorp Vault, etc.
    pass

service = NetworkOSService()
service.migrate_tunnel_secrets(
    tunnel_id="your-tunnel-id",
    secure_storage_save_fn=custom_save_fn
)
```

## Tunnel Security

### Configuration Best Practices

```bash
# ✅ Good: Only expose SMS webhook path
agentos networkos create \
  --target http://127.0.0.1:8000/api/channels/sms \
  --routes "/twilio/webhook/*"

# ❌ Avoid: Exposing entire AgentOS
agentos networkos create \
  --target http://127.0.0.1:8000  # Exposes all APIs
```

### Monitoring Recommendations

```bash
# Regularly check Tunnel event logs
agentos networkos logs TUNNEL_ID | grep -i "error\|warn"

# Check for anomalous access
agentos networkos logs TUNNEL_ID | grep -v "MessageSid"  # Non-Twilio requests
```

## Webhook Security

### Path Token Generation

```python
# ✅ Good: Cryptographically random
import secrets
path_token = secrets.token_urlsafe(32)  # 43 characters

# ❌ Bad: Predictable
path_token = "my-webhook-123"  # Easy to guess
```

### Signature Verification

- **Must verify**: All inbound webhooks using X-Twilio-Signature header
- **Constant-time comparison**: Prevents timing attacks (already implemented)
- **Failure strategy**: Return 401, don't provide error details
- **Implementation**: Uses Twilio Request Signature verification per official specification

### IP Whitelist (Optional)

Twilio IP ranges: https://www.twilio.com/docs/usage/webhooks/ip-addresses

Can configure IP whitelist in Cloudflare Access.

## Audit and Compliance

### Privacy Compliance

- **Phone Numbers**: Hash after storage (don't log in plaintext)
- **Message Content**: Don't persist to DB (only in MessageBus memory)
- **Audit Logs**: Only record metadata (MessageSid, length, timestamp)

### Audit Queries

```bash
# View recent SMS webhook access
sqlite3 ~/.agentos/store/networkos/db.sqlite \
  "SELECT * FROM network_events WHERE event_type='webhook_received' ORDER BY created_at DESC LIMIT 10;"

# View signature verification failures
grep "Invalid signature" logs/agentos.log | tail -20
```

## Incident Response

### If Token Leaked

1. **Immediately rotate path_token:**
   ```bash
   # Generate new token
   NEW_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
   # Update configuration
   agentos config set sms.webhook_path_token "$NEW_TOKEN"
   # Update Twilio Webhook URL
   ```

2. **Check for anomalous access:**
   ```bash
   agentos networkos logs TUNNEL_ID --since 1h | grep -v "Twilio"
   ```

3. **If necessary, rotate Twilio Auth Token**

### If Anomalous SMS Detected

1. **Check source:**
   ```bash
   grep "Received SMS" logs/agentos.log | grep -v "+1234567890"  # Replace with known numbers
   ```

2. **Temporarily disable webhook:**
   ```bash
   agentos networkos stop TUNNEL_ID
   ```

3. **Re-enable after investigation**

## Regular Security Checklist

- [ ] Path token strength check (>=32 chars random)
- [ ] Secrets not committed to Git (`git grep -i "auth.*token\|secret"`)
- [ ] Tunnel only exposes necessary paths
- [ ] Signature verification tests pass (`pytest tests/security/`)
- [ ] Audit logs show no anomalous patterns
- [ ] Twilio Console shows high webhook success rate
- [ ] Doctor check passes (`agentos doctor`)

## Threat Model

### Threat 1: URL Scanning

**Attack**: Attacker scans for webhook URLs
**Mitigation**: 32+ char random path_token
**Detection**: Monitor for 404s in NetworkOS logs

### Threat 2: Request Spoofing

**Attack**: Attacker sends fake Twilio webhooks
**Mitigation**: HMAC-SHA1 signature verification
**Detection**: Signature verification failures in logs

### Threat 3: Replay Attacks

**Attack**: Attacker replays valid webhook requests
**Mitigation**: MessageSid deduplication
**Detection**: Duplicate MessageSid warnings in logs

### Threat 4: Token Leakage

**Attack**: Tokens exposed in Git/logs/exports
**Mitigation**: Secret management best practices
**Detection**: Git history scan, log review

### Threat 5: Man-in-the-Middle

**Attack**: Attacker intercepts webhook traffic
**Mitigation**: HTTPS enforced by Cloudflare Tunnel
**Detection**: Certificate validation failures

## Security Testing

### Test 1: Invalid Token

```bash
curl -X POST https://sms.your-domain.com/api/channels/sms/twilio/webhook/WRONG_TOKEN \
  -d "MessageSid=SM123&From=+1234&To=+5678&Body=Test"
# Expected: 404 Not Found
```

### Test 2: Missing Signature

```bash
curl -X POST https://sms.your-domain.com/api/channels/sms/twilio/webhook/VALID_TOKEN \
  -d "MessageSid=SM123&From=+1234&To=+5678&Body=Test"
# Expected: 401 Unauthorized
```

### Test 3: Invalid Signature

```bash
curl -X POST https://sms.your-domain.com/api/channels/sms/twilio/webhook/VALID_TOKEN \
  -H "X-Twilio-Signature: invalid_signature" \
  -d "MessageSid=SM123&From=+1234&To=+5678&Body=Test"
# Expected: 401 Unauthorized
```

### Test 4: Duplicate MessageSid

```bash
# Send same MessageSid twice
curl -X POST ... -d "MessageSid=SM123..."  # First: processed
curl -X POST ... -d "MessageSid=SM123..."  # Second: ignored (200 but not processed)
# Expected: Both return 200, only first is processed
```

### Test 5: Valid Request

```bash
# Compute valid signature first
python3 -c "
import hmac, hashlib, base64
url = 'https://sms.your-domain.com/api/channels/sms/twilio/webhook/VALID_TOKEN'
params = {'MessageSid': 'SM123', 'From': '+1234', 'To': '+5678', 'Body': 'Test'}
data = url + ''.join(f'{k}{v}' for k, v in sorted(params.items()))
sig = base64.b64encode(hmac.new(b'YOUR_AUTH_TOKEN', data.encode(), hashlib.sha1).digest()).decode()
print(sig)
"

curl -X POST https://sms.your-domain.com/api/channels/sms/twilio/webhook/VALID_TOKEN \
  -H "X-Twilio-Signature: COMPUTED_SIGNATURE" \
  -d "MessageSid=SM123&From=+1234&To=+5678&Body=Test"
# Expected: 200 OK
```

## Production Hardening

### 1. Rate Limiting

```bash
# Configure per-user rate limits
agentos config set sms.rate_limit.per_user 10/minute
```

### 2. Monitoring

```bash
# Set up alerts for:
# - Signature verification failures (>1% rate)
# - Webhook response time (>100ms)
# - Tunnel health (status != up)
# - Duplicate rate (>5%)
```

### 3. Token Rotation

```bash
# Rotate tokens every 90 days
# Add to cron:
0 0 1 */3 * /usr/local/bin/agentos-rotate-tokens.sh
```

### 4. Backup Path Token

```bash
# Support 2 valid tokens during rotation (24h overlap)
# Old token expires after 24h
agentos config set sms.webhook_path_token_backup "OLD_TOKEN"
agentos config set sms.webhook_path_token_backup_expires_at "2026-02-02T00:00:00Z"
```

### 5. Audit Log Retention

```bash
# Keep audit logs for 90 days minimum
agentos config set audit.retention_days 90
```

## Compliance Considerations

### GDPR (EU)

- ✅ Phone numbers hashed before storage
- ✅ Message content not persisted
- ✅ Right to erasure implemented
- ✅ Audit trail for all processing

### CCPA (California)

- ✅ Opt-out mechanism for SMS
- ✅ Data disclosure on request
- ✅ No selling of user data

### HIPAA (Healthcare)

- ⚠️ SMS is NOT HIPAA-compliant by default
- ✅ If needed, add encryption layer
- ✅ Use BAA-compliant Twilio account

### PCI DSS (Payment)

- ❌ Never send payment card data via SMS
- ✅ Only send transaction confirmations

## Emergency Procedures

### Procedure: Token Compromise

1. Immediately rotate path_token (Step 1 in Incident Response)
2. Review logs for past 7 days
3. Identify compromised timeframe
4. Notify security team
5. Document incident

### Procedure: Tunnel Outage

1. Stop tunnel: `agentos networkos stop TUNNEL_ID`
2. Check Cloudflare status page
3. Verify cloudflared process: `ps aux | grep cloudflared`
4. Check logs: `agentos networkos logs TUNNEL_ID`
5. Restart if needed: `agentos networkos start TUNNEL_ID`

### Procedure: Twilio Account Compromise

1. Immediately change Auth Token in Twilio Console
2. Update Auth Token in AgentOS config
3. Review Twilio audit logs
4. Check for unauthorized SMS sends
5. Contact Twilio support

## Enterprise Security Checklist

### Token Rotation (企业必问)

**问题**："如果token泄漏,怎么轮换?"

**答案**(当前v1):
```bash
# 手动轮换流程(v1)
# 1. 在Cloudflare生成新token
# 2. 更新AgentOS配置
agentos networkos update TUNNEL_ID --token NEW_TOKEN

# 3. 重启tunnel
agentos networkos stop TUNNEL_ID
agentos networkos start TUNNEL_ID

# 4. 验证
agentos networkos status TUNNEL_ID
# 应看到新的last_heartbeat_at
```

**路线图**(v2计划):
```bash
# 一键轮换(计划中)
agentos networkos rotate-secret TUNNEL_ID
# 自动：获取新token → 更新secret_ref → 重启tunnel → 记录event
```

**审计**:
- 所有轮换操作记录到 network_events
- 事件类型：`secret_rotated`
- 包含：旧secret_ref、新secret_ref、操作者、时间戳

---

### Minimal Visibility (最小可见性原则)

**问题**："运维排障需要看token,但又不能完全暴露?"

**答案**：Token Fingerprint(指纹)

**CLI显示**(安全):
```bash
$ agentos networkos status TUNNEL_ID

Token: ****...a3f2 (fingerprint: sha256:1a2b3c...)
Secret Ref: networkos:tunnel:abc-123
```

**日志记录**(安全):
```
[INFO] Using token fingerprint: sha256:1a2b3c... for tunnel abc-123
[WARN] Token validation failed for fingerprint: sha256:9x8y7z...
```

**实现**(Store层):
```python
def get_token_fingerprint(token: str) -> str:
    """生成token指纹(用于日志/显示)

    返回：sha256 hash的前12位
    """
    import hashlib
    hash_obj = hashlib.sha256(token.encode('utf-8'))
    return f"sha256:{hash_obj.hexdigest()[:12]}"
```

**好处**:
- ✅ 运维可区分不同token(排障)
- ✅ 日志无完整token(安全)
- ✅ 支持人员可验证token未泄漏(匹配fingerprint)

---

### Compliance Mapping

| 标准 | 要求 | 实现 |
|------|------|------|
| **OWASP API Security** | A2:认证破坏 | ✅ Twilio Request Signature verification |
| | A7:安全配置错误 | ✅ 默认chat-only |
| | A8:注入 | ✅ 参数化查询 |
| **NIST 800-53** | AC-6:最小权限 | ✅ secret_ref模式 |
| | AU-2:审计事件 | ✅ network_events表 |
| | SC-28:存储保护 | ✅ 0600权限+加密 |
| **ISO 27001** | A.9.4.1:访问限制 | ✅ Path token |
| | A.10.1.1:密码策略 | ✅ 无明文存储 |
| **GDPR** | Art.32:安全处理 | ✅ 电话号码哈希 |
| | Art.17:删除权 | ✅ Cascade delete |
| **HIPAA** | §164.312(a)(1) | ✅ 访问控制 |
| | §164.312(b) | ✅ 审计日志 |

**注意**：以上为技术基础,完整合规需额外流程(如BAA、风险评估、员工培训)。

---

## References

- [Twilio Security Best Practices](https://www.twilio.com/docs/usage/security)
- [Cloudflare Tunnel Security](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [NIST Cryptographic Standards](https://csrc.nist.gov/publications/)

---

**Last Updated:** 2026-02-01
**Version:** NetworkOS v1.0 + SMS Channel v2.0
**Classification:** Internal Use - Security Guidelines
