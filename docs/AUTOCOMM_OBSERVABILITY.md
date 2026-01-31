# AutoComm Observability Quick Reference

## Overview

AutoComm failures are now **fully observable** through multiple mechanisms. This document provides a quick reference for detecting, debugging, and monitoring AutoComm failures.

---

## 🔍 Detecting Failures

### 1. User-Visible Indicators

When AutoComm fails, users see a clear failure banner:

```
⚠️ **AutoComm Failed**: ImportError

/comm search What's the weather in Beijing?

_Debug info: Auto-search attempted but failed. Check logs for details._
```

**Key Differences from Normal Suggestion Mode**:
- ❌ Normal mode: "🔍 External information required"
- ✅ Failure mode: "⚠️ **AutoComm Failed**"

### 2. Message Metadata Flags

Check the `metadata` field of chat messages:

```python
# Failure case
metadata = {
    "auto_comm_attempted": True,    # ← AutoComm was tried
    "auto_comm_failed": True,       # ← It failed
    "auto_comm_error": "...",       # ← Error message
    "auto_comm_error_type": "...",  # ← Exception type
    "fallback_mode": "suggestion"   # ← Degraded to suggestion
}

# Normal suggestion mode (auto_comm disabled)
metadata = {
    "classification": "require_comm"
    # No auto_comm_* flags
}
```

### 3. Structured Logs

Failures are logged with rich context:

```python
logger.error(
    "AutoComm execution failed: ImportError",
    extra={
        "session_id": "abc123",
        "user_message": "What's the weather?",
        "error_type": "ImportError",
        "execution_phase": "execution",
        "classification": { ... }
    }
)
```

---

## 🏥 Health Monitoring

### Health Check Endpoint

**Endpoint**: `GET /api/health/autocomm`

**Example**:
```bash
curl http://localhost:8000/api/health/autocomm
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-31T10:30:00Z",
  "components": {
    "adapter": {
      "status": "ok",
      "message": "CommunicationAdapter initialized successfully"
    },
    "policy": {
      "status": "ok",
      "enabled": true,
      "message": "AutoCommPolicy initialized (enabled=true)"
    }
  }
}
```

**Status Values**:
- `healthy`: All components operational
- `disabled`: Policy disabled (not an error)
- `unhealthy`: Component failure detected

---

## 🐛 Debugging Guide

### Step 1: Check Logs

```bash
# Search for AutoComm failures
grep "AutoComm execution failed" logs/agentos.log

# View structured context
grep -A 5 "AutoComm execution failed" logs/agentos.log
```

### Step 2: Query Failed Messages

```sql
SELECT
  message_id,
  session_id,
  json_extract(metadata, '$.auto_comm_error') as error,
  json_extract(metadata, '$.auto_comm_error_type') as error_type,
  created_at
FROM chat_messages
WHERE json_extract(metadata, '$.auto_comm_failed') = 1
ORDER BY created_at DESC;
```

### Step 3: Check Component Health

```bash
# Check health endpoint
curl -s http://localhost:8000/api/health/autocomm | jq

# Alert on unhealthy status
STATUS=$(curl -s http://localhost:8000/api/health/autocomm | jq -r '.status')
if [ "$STATUS" != "healthy" ]; then
  echo "ALERT: AutoComm is $STATUS"
fi
```

---

## 📊 Common Error Types

| Error Type | Cause | Fix |
|------------|-------|-----|
| `ImportError` | Missing dependency | Install required package |
| `ConnectionError` | Network issue | Check connectivity |
| `TimeoutError` | Slow external service | Increase timeout |
| `ValueError` | Invalid query format | Check policy rules |

---

## 🔧 Testing Observability

Run the test suite:

```bash
python3 -m pytest tests/core/chat/test_autocomm_observability.py -v
```

**Test Coverage**:
- ✅ Failure produces observable message
- ✅ Normal mode has no failure flags
- ✅ Decision serialization works
- ✅ Classification has to_dict method

---

## 📈 Monitoring Best Practices

### 1. Set Up Alerts

```bash
# Monitor health endpoint
watch -n 30 'curl -s http://localhost:8000/api/health/autocomm | jq'

# Alert on failures
curl -s http://localhost:8000/api/health/autocomm | \
  jq -e '.status == "healthy"' || alert_team
```

### 2. Track Metrics

- **Failure Rate**: % of AutoComm attempts that fail
- **Error Types**: Distribution of error types
- **MTTD**: Mean time to detect failures
- **MTTR**: Mean time to resolve issues

### 3. Dashboard

Create dashboards showing:
- AutoComm success/failure rate over time
- Component health status
- Top error types
- Affected sessions

---

## 🎯 Quick Decision Tree

```
User asks question
  ↓
Is AutoComm enabled?
  ├─ No → Normal suggestion mode (no auto_comm_* flags)
  └─ Yes → AutoComm attempted
      ↓
    Did it succeed?
      ├─ Yes → auto_comm_executed=true
      └─ No → auto_comm_failed=true
          ↓
        Observable failure:
        - User sees "⚠️ AutoComm Failed"
        - Metadata has error details
        - Logs have structured context
        - Health endpoint shows issues
```

---

## 📝 Related Files

| File | Purpose |
|------|---------|
| `agentos/core/chat/engine.py` | AutoComm execution logic with enhanced error handling |
| `agentos/core/chat/auto_comm_policy.py` | Policy decisions and serialization |
| `agentos/webui/api/health.py` | Health check endpoint |
| `tests/core/chat/test_autocomm_observability.py` | Test suite |
| `OBSERVABILITY_IMPROVEMENT_REPORT.md` | Detailed implementation report |

---

**Last Updated**: 2026-01-31
**Version**: v1.0
**Status**: Production Ready ✅
