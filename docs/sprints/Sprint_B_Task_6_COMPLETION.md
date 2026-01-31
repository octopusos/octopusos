# Sprint B · Task #6 - Cloud API Key Configuration

**Status**: ✅ COMPLETED
**Date**: 2026-01-27
**Sprint**: Sprint B (WebUI 增强)
**Task ID**: W-P1-06

---

## 📋 Task Overview

Implement secure API key management for cloud providers (OpenAI, Anthropic) with WebUI integration.

**Goal**: 让 WebUI 能安全地写入/更新 Cloud Provider 的 API Key，且任何日志/事件/返回都不泄露 key。

**Scope**:
- ✅ Secure local storage (~/.agentos/secrets.json)
- ✅ 0600 permission enforcement
- ✅ WebUI API endpoints (save/get/delete)
- ✅ Provider integration (SecretStore → probe)
- ✅ Key redaction in logs/errors/events
- ✅ Last-4 digits for UI verification

---

## 🏗️ Architecture

### Storage Layer

```
┌─────────────────────────────────────────────────────────────┐
│                       SecretStore                           │
│  ~/.agentos/secrets.json (0600)                            │
│                                                             │
│  {                                                          │
│    "openai": {                                             │
│      "api_key": "sk-***",  # Never logged/returned       │
│      "updated_at": "2026-01-27T..."                       │
│    },                                                       │
│    "anthropic": {...}                                      │
│  }                                                          │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ├─────────> save_secret(provider, key)
                  ├─────────> get_secret(provider) → key
                  ├─────────> delete_secret(provider)
                  └─────────> get_status(provider) → {configured, last4}
```

### API Layer

```
POST /api/settings/secrets
  Request:  {"provider": "openai", "api_key": "sk-..."}
  Response: {"ok": true, "configured": true, "last4": "abcd"}

GET /api/settings/secrets/status
  Response: {"secrets": [
    {"provider": "openai", "configured": true, "last4": "abcd"},
    {"provider": "anthropic", "configured": false}
  ]}

DELETE /api/settings/secrets/{provider}
  Response: {"ok": true, "configured": false}
```

### Provider Integration

```
OpenAIProvider / AnthropicProvider
  └─> _get_api_key()
        ├─ Priority 1: SecretStore (Task #6)
        ├─ Priority 2: config_manager (legacy)
        └─ Priority 3: Environment variable

  └─> probe()
        ├─ No key → DISCONNECTED (reason: missing_api_key)
        └─ Has key → Make API call to verify
```

---

## 📦 Implementation

### File Tree

```
agentos/
├── webui/
│   └── secrets/
│       ├── __init__.py                ← NEW (module exports)
│       └── store.py                   ← NEW (SecretStore class)
└── webui/api/
    └── secrets.py                     ← NEW (API endpoints)

agentos/providers/
├── cloud_openai.py                    ← MODIFIED (SecretStore integration)
└── cloud_anthropic.py                 ← MODIFIED (SecretStore integration)

tests/webui/
├── test_secrets_store.py              ← NEW (15 unit tests)
├── test_secrets_api.py                ← NEW (9 logic tests)
└── validate_secrets_api.sh            ← NEW (manual validation)
```

### Key Components

#### 1. SecretStore

**File**: `agentos/webui/secrets/store.py`

```python
class SecretStore:
    def __init__(self, secrets_file: Optional[str] = None):
        self.secrets_file = Path(secrets_file or Path.home() / ".agentos" / "secrets.json")
        self._verify_permissions()  # Enforce 0600

    def save_secret(self, provider: str, api_key: str) -> SecretInfo:
        """Save API key with atomic write"""
        # Validate inputs
        # Redact key in logs
        # Atomic write via tmp file
        # Return metadata only (no key)

    def get_secret(self, provider: str) -> Optional[str]:
        """Get full API key (internal use only)"""

    def delete_secret(self, provider: str) -> SecretInfo:
        """Delete API key"""

    def get_status(self, provider: str) -> SecretInfo:
        """Get status (configured + last4, no key)"""

    @staticmethod
    def _redact_key(api_key: str) -> str:
        """Redact key for logging: sk-*** → ***abcd"""
```

**Security Features**:
- ✅ 0600 permission enforcement (auto-fix if wrong)
- ✅ Atomic writes (tmp file + rename)
- ✅ Key redaction in all logs (`***last4`)
- ✅ Validation (min 8 chars, non-empty provider)
- ✅ Graceful handling of corrupted JSON

#### 2. API Endpoints

**File**: `agentos/webui/api/secrets.py`

```python
@router.post("", response_model=SaveSecretResponse)
async def save_secret(request: SaveSecretRequest):
    """Save API key (never returned in response)"""
    store = get_secret_store()
    info = store.save_secret(request.provider, request.api_key)
    return SaveSecretResponse(ok=True, provider=info.provider, last4=info.last4)

@router.get("/status", response_model=AllSecretsStatusResponse)
async def get_all_secrets_status():
    """Get all secrets status (no actual keys)"""
    store = get_secret_store()
    all_status = store.get_all_status()
    return AllSecretsStatusResponse(secrets=all_status)

@router.delete("/{provider}", response_model=DeleteSecretResponse)
async def delete_secret(provider: str):
    """Delete API key"""
    store = get_secret_store()
    info = store.delete_secret(provider)
    return DeleteSecretResponse(ok=True, configured=info.configured)
```

**Security Enforcement**:
- ✅ Never return actual keys in responses
- ✅ Only supported providers (openai, anthropic)
- ✅ Validation errors → 400 Bad Request
- ✅ Permission errors → 500 with hint
- ✅ All errors redact keys

#### 3. Provider Integration

**Files**: `agentos/providers/cloud_openai.py`, `cloud_anthropic.py`

```python
def _get_api_key(self) -> Optional[str]:
    """Get API key with priority: SecretStore > config > env"""

    # Priority 1: SecretStore (Task #6)
    try:
        from agentos.webui.secrets import SecretStore
        store = SecretStore()
        api_key = store.get_secret(self.id)
        if api_key:
            logger.debug(f"Using API key from SecretStore for {self.id}")
            return api_key
    except Exception as e:
        logger.debug(f"SecretStore not available: {e}")

    # Priority 2: config_manager (legacy)
    if self.config_manager:
        config = self.config_manager.get(self.id)
        if config and config.auth.api_key:
            return config.auth.api_key

    # Priority 3: Environment variable
    return os.getenv("OPENAI_API_KEY")
```

**Integration Points**:
- ✅ Providers check SecretStore first
- ✅ Backward compatible with existing config
- ✅ probe() uses SecretStore keys
- ✅ DISCONNECTED state when key missing

---

## ✅ Testing

### Unit Tests (24 Tests Total)

#### SecretStore Tests (15)

**File**: `tests/webui/test_secrets_store.py`

```bash
pytest tests/webui/test_secrets_store.py -v
```

**Coverage**:
1. ✅ Save secret → configured=True, last4 correct
2. ✅ Get secret → returns full key
3. ✅ Get secret not configured → returns None
4. ✅ Delete secret → configured=False
5. ✅ Persistence across restarts
6. ✅ File permissions 0600
7. ✅ Permission error on insecure file → auto-fix
8. ✅ Key redaction in logs
9. ✅ Get status for configured provider
10. ✅ Get status for unconfigured provider
11. ✅ Get all status
12. ✅ Validation: empty provider → ValueError
13. ✅ Validation: short key → ValueError
14. ✅ Atomic write operation (tmp file)
15. ✅ Corrupted JSON graceful handling

**Result**: ✅ 15/15 passed

#### API Logic Tests (9)

**File**: `tests/webui/test_secrets_api.py`

```bash
pytest tests/webui/test_secrets_api.py -v
```

**Coverage**:
1. ✅ API save secret workflow
2. ✅ API get all status workflow
3. ✅ API get single status workflow
4. ✅ API delete secret workflow
5. ✅ API validation error handling
6. ✅ API permission error handling
7. ✅ API response never contains keys
8. ✅ API supported providers
9. ✅ get_secret() not exposed via API

**Result**: ✅ 9/9 passed

### Manual Validation

**File**: `tests/webui/validate_secrets_api.sh`

```bash
# Start WebUI
python3 -m agentos.cli.main webui

# Run validation (in another terminal)
./tests/webui/validate_secrets_api.sh
```

**Test Sequence**:
1. POST save OpenAI key → configured=true, last4 correct
2. POST save Anthropic key → configured=true, last4 correct
3. GET all status → both secrets, NO actual keys
4. GET single status → metadata only
5. GET /api/providers/status → OpenAI state changed
6. DELETE secret → configured=false
7. GET status after delete → OpenAI removed
8. File permissions → 0600 verification
9. Log safety → NO key leakage

---

## 🎯 Acceptance Criteria (6/6)

| # | Criterion | Status |
|---|-----------|--------|
| 1 | POST save OpenAI key → status configured=true (last4 正确) | ✅ |
| 2 | DELETE delete key → configured=false | ✅ |
| 3 | 重启 WebUI → 状态保持 | ✅ |
| 4 | /api/providers/status 对 OpenAI 由 DISCONNECTED→(READY/DEGRADED) | ✅ |
| 5 | 搜索日志（grep）确认没有 key 泄露（sk- 不出现） | ✅ |
| 6 | 单测覆盖：写入/读取/删除 + 权限错误 + 输出脱敏 | ✅ |

---

## 🔒 Security Guarantees

### Red Lines (All Enforced)

| Red Line | Implementation | Status |
|----------|----------------|--------|
| 1. No keys in logs | `_redact_key()` redacts all log messages | ✅ |
| 2. No keys in API responses | SecretInfo only has `last4` field | ✅ |
| 3. 0600 permissions | `_verify_permissions()` enforces + auto-fix | ✅ |
| 4. Localhost only | WebUI default binding (Task #7 for auth) | ✅ |

### Key Redaction Examples

**Before** (UNSAFE):
```
INFO: Saving API key: sk-test-openai-key-12345678
```

**After** (SAFE):
```
INFO: Saving secret for provider: openai (key: ***5678)
```

### Response Safety

**API Responses NEVER contain**:
- ❌ Full API keys
- ❌ Partial keys (except last4)
- ❌ Key prefixes

**API Responses ONLY contain**:
- ✅ Provider ID
- ✅ configured: true/false
- ✅ last4 digits (for verification)
- ✅ updated_at timestamp

---

## 📊 Error Handling

### Error Codes

| Code | Scenario | HTTP | Recovery |
|------|----------|------|----------|
| `validation_error` | Empty provider / short key | 400 | Fix request |
| `unsupported_provider` | Provider not in [openai, anthropic] | 400 | Use valid provider |
| `permission_error` | Secrets file permissions wrong | 500 | chmod 600 ~/.agentos/secrets.json |
| `json_decode_error` | Corrupted secrets file | 500 | Delete and recreate file |

### Example Error Response

```json
{
  "detail": "API key too short (minimum 8 characters)"
}
```

**Security Note**: Errors never leak key contents

---

## 🔍 Integration Verification

### Provider Status Change

**Before Task #6**:
```bash
curl http://localhost:8000/api/providers/status | jq '.providers[] | select(.id=="openai")'
```

```json
{
  "id": "openai",
  "state": "DISCONNECTED",
  "reason_code": "missing_api_key",
  "last_error": "API key not configured"
}
```

**After Task #6** (with key saved):
```bash
# Save key first
curl -X POST http://localhost:8000/api/settings/secrets \
  -H "Content-Type: application/json" \
  -d '{"provider": "openai", "api_key": "sk-..."}'

# Check status
curl http://localhost:8000/api/providers/status | jq '.providers[] | select(.id=="openai")'
```

```json
{
  "id": "openai",
  "state": "READY",  // or "ERROR" if key invalid
  "reason_code": "ok",
  "latency_ms": 123.45,
  "last_ok_at": "2026-01-27T..."
}
```

---

## 🧪 Testing Commands

### Run All Tests

```bash
# Unit tests (24 total)
python3 -m pytest tests/webui/test_secrets_store.py tests/webui/test_secrets_api.py -v

# Expected: 24 passed
```

### Manual Validation

```bash
# Start WebUI
python3 -m agentos.cli.main webui

# In another terminal
./tests/webui/validate_secrets_api.sh

# Follow prompts to verify all 9 test cases
```

### Security Audit

```bash
# Check file permissions
ls -l ~/.agentos/secrets.json
# Expected: -rw------- (0600)

# Check log safety (no keys leaked)
grep -r "sk-" ~/.agentos/*.log
# Expected: No matches (or only redacted ***last4)
```

---

## 📂 File Changes

**New Files**:
- `agentos/webui/secrets/__init__.py`
- `agentos/webui/secrets/store.py`
- `agentos/webui/api/secrets.py`
- `tests/webui/test_secrets_store.py`
- `tests/webui/test_secrets_api.py`
- `tests/webui/validate_secrets_api.sh` (executable)

**Modified Files**:
- `agentos/webui/app.py` (registered secrets router)
- `agentos/providers/cloud_openai.py` (SecretStore integration)
- `agentos/providers/cloud_anthropic.py` (SecretStore integration)

---

## 🎯 Next Steps

### Sprint B Task #7 (TBD)

Potential next task: Authentication / Multi-user support

**Why needed**:
- Current: Secrets API is localhost-only
- Future: Remote WebUI access requires auth
- Security: Prevent unauthorized secret modification

**Out of scope for Task #6**:
- ❌ User authentication
- ❌ Multi-user secret isolation
- ❌ Remote access control

---

## ✅ Task Closure

**Status**: READY TO COMMIT

Sprint B Task #6 is complete and ready for user approval.

**Deliverables**:
- ✅ SecretStore with 0600 enforcement
- ✅ WebUI API endpoints (save/get/delete)
- ✅ Provider integration (OpenAI/Anthropic)
- ✅ Key redaction in logs/errors
- ✅ Unit tests (24/24 passed)
- ✅ Manual validation script
- ✅ Security guarantees enforced
- ✅ Comprehensive documentation

**Dependencies Met**:
- ✅ Sprint B Task #4 (EventBus - not directly used but available)
- ✅ W-P1-03 (Provider abstraction - extended)

**Security Verified**:
- ✅ No keys in logs (grep confirmed)
- ✅ No keys in API responses (SecretInfo only has last4)
- ✅ 0600 permissions (enforced + tested)
- ✅ Atomic writes (tmp file pattern)
- ✅ Validation (min 8 chars, non-empty provider)

**Ready for**: User verification and git commit
