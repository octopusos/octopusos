# CommunicationAdapter Documentation

## Overview

The `CommunicationAdapter` is the bridge between Chat commands and CommunicationOS, providing a Chat-friendly interface while maintaining all security, auditing, and evidence tracking features of CommunicationOS.

## Important: Conversation Mode vs Execution Phase

**Key Principle**: `conversation_mode` does NOT affect permission judgment. Only `execution_phase` controls access to `/comm` commands.

### Two Independent Concepts

1. **conversation_mode** (chat/discussion/plan/development/task)
   - Controls: How AgentOS interacts (UX, tone, output format)
   - Does NOT control: Security permissions, capability access
   - Can change: Freely, without approval

2. **execution_phase** (planning/execution)
   - Controls: What AgentOS can do (security boundary, capability access)
   - Does NOT control: Conversation style, output format
   - Can change: Only with explicit user approval

### Example: Development Mode + Planning Phase

```python
# User switches to development mode for code-style interaction
conversation_mode = "development"
execution_phase = "planning"

# Result: Code-focused UX, but read-only permissions
# - Can: Read files, analyze code, discuss architecture
# - Cannot: Execute /comm commands (blocked by Phase Gate)
```

Even though `development` mode might suggest the need for external communication, the Phase Gate will block `/comm` commands because `execution_phase` is still `"planning"`.

### /comm Commands and Phase Gate

All `/comm` commands check ONLY `execution_phase`, NOT `conversation_mode`:

```python
# In comm_commands.py
def _check_phase_gate(execution_phase: str) -> None:
    """Phase Gate: Block /comm commands in planning phase."""
    if execution_phase != "execution":
        raise BlockedError(
            "comm.* commands are forbidden in planning phase."
        )
    # Note: conversation_mode is NOT checked here
```

**Scenarios**:

| conversation_mode | execution_phase | /comm allowed? | Reason |
|------------------|----------------|---------------|---------|
| chat | planning | ❌ NO | Phase Gate blocks |
| development | planning | ❌ NO | Phase Gate blocks (mode irrelevant) |
| task | planning | ❌ NO | Phase Gate blocks |
| chat | execution | ✅ YES | Phase Gate allows |
| development | execution | ✅ YES | Phase Gate allows |
| task | execution | ✅ YES | Phase Gate allows |

**Golden Rule**: If you want to use `/comm` commands, you MUST be in `execution` phase, regardless of `conversation_mode`.

## Architecture

```
┌─────────────┐
│ Chat Layer  │
│  /comm      │
│  commands   │
└──────┬──────┘
       │
       │ Uses
       ▼
┌──────────────────────────┐
│  CommunicationAdapter    │  ← This module
│                          │
│  • Format conversion     │
│  • Evidence propagation  │
│  • Attribution enforcing │
│  • Error translation     │
└──────┬───────────────────┘
       │
       │ Calls
       ▼
┌──────────────────────────┐
│  CommunicationService    │
│                          │
│  • Policy enforcement    │
│  • Rate limiting         │
│  • Audit logging         │
│  • Trust tier tracking   │
└──────┬───────────────────┘
       │
       │ Routes to
       ▼
┌──────────────────────────┐
│  Connectors              │
│  • WebSearch             │
│  • WebFetch              │
│  • RSS, Email, etc.      │
└──────────────────────────┘
```

## Key Features

### 1. Evidence Tracking
Every operation includes audit trail information:
```python
"metadata": {
    "audit_id": "ev-11ba62200198",  # Links to CommunicationOS audit log
    "attribution": "CommunicationOS (search) in session {session_id}",
    "retrieved_at": "2026-01-30T12:31:01.081292+00:00"
}
```

### 2. Trust Tier Propagation
All results include trust tier information:
- **SEARCH_RESULT**: Search engine results (candidates only, not facts)
- **EXTERNAL_SOURCE**: Fetched content (needs verification)
- **PRIMARY_SOURCE**: Official sites, original documents
- **AUTHORITATIVE_SOURCE**: Government, academia, certified orgs

### 3. Chat-Friendly Error Handling
Errors are translated to user-friendly Chinese messages:
```python
{
    "status": "blocked",
    "reason": "SSRF_PROTECTION",
    "message": "该 URL 被安全策略阻止(内网地址或 localhost)",
    "hint": "请使用公开的 HTTPS URL"
}
```

### 4. Forced Attribution
Every response includes attribution that cannot be omitted:
```python
"attribution": "CommunicationOS (search/fetch) in session {session_id}"
```

## Usage

### Basic Search
```python
from agentos.core.chat.communication_adapter import CommunicationAdapter

adapter = CommunicationAdapter()

result = await adapter.search(
    query="Python tutorial",
    session_id="session-123",
    task_id="task-456",
    max_results=10
)

# Returns:
{
    "results": [
        {
            "title": "Python Tutorial - W3Schools",
            "url": "https://www.w3schools.com/python/",
            "snippet": "Learn Python programming...",
            "trust_tier": "search_result"
        }
    ],
    "metadata": {
        "query": "Python tutorial",
        "total_results": 10,
        "trust_tier_warning": "搜索结果是候选来源,不是验证事实",
        "attribution": "CommunicationOS (search) in session session-123",
        "retrieved_at": "2026-01-30T12:31:01.081292+00:00",
        "audit_id": "ev-11ba62200198"
    }
}
```

### Fetch URL Content
```python
result = await adapter.fetch(
    url="https://www.python.org",
    session_id="session-123",
    task_id="task-456"
)

# Returns:
{
    "status": "success",
    "url": "https://www.python.org",
    "content": {
        "title": "Welcome to Python.org",
        "description": "Official Python website",
        "text": "Python is a programming language...",
        "links": [...],
        "images": [...]
    },
    "metadata": {
        "trust_tier": "primary_source",
        "content_hash": "29611f4343656455...",
        "retrieved_at": "2026-01-30T12:31:01.081292+00:00",
        "citations": {
            "url": "https://www.python.org",
            "title": "Welcome to Python.org",
            "author": "www.python.org",
            "publish_date": "",
            "retrieved_at": "2026-01-30T12:31:01.081292+00:00"
        },
        "attribution": "CommunicationOS (fetch) in session session-123",
        "audit_id": "ev-11ba62200198"
    }
}
```

## Error Handling

The adapter translates all CommunicationOS errors to Chat-friendly formats:

### SSRF Protection
```python
{
    "status": "blocked",
    "reason": "SSRF_PROTECTION",
    "message": "该 URL 被安全策略阻止(内网地址或 localhost)",
    "hint": "请使用公开的 HTTPS URL"
}
```

### Rate Limiting
```python
{
    "status": "rate_limited",
    "message": "超过速率限制,请等待 60 秒",
    "retry_after": 60
}
```

### Approval Required
```python
{
    "status": "requires_approval",
    "message": "该操作需要管理员批准",
    "hint": "Outbound operation requires explicit human approval"
}
```

## Integration with Chat Commands

The adapter is designed to be used by Chat slash commands:

```python
# In /comm search command
from agentos.core.chat.communication_adapter import CommunicationAdapter

async def handle_comm_search(args, context):
    adapter = CommunicationAdapter()
    result = await adapter.search(
        query=args["query"],
        session_id=context["session_id"],
        task_id=context["task_id"]
    )

    # Display results to user
    if "results" in result:
        for item in result["results"]:
            print(f"📄 {item['title']}")
            print(f"   🔗 {item['url']}")
            print(f"   🔍 {item['snippet']}")
    else:
        print(f"❌ Error: {result['message']}")
```

## Security Guarantees

1. **All requests go through PolicyEngine**: SSRF, domain blocking, rate limiting
2. **All operations are audited**: Every call generates an evidence record
3. **Trust tier is always tracked**: No unmarked external data
4. **Attribution cannot be bypassed**: Every response includes source attribution
5. **Execution phase is enforced**: Chat commands always run in "execution" phase

## Testing

Run the integration test:
```bash
python3 test_communication_adapter.py
```

Expected validations:
- ✅ Adapter can call CommunicationService
- ✅ search() returns Chat-friendly format
- ✅ fetch() returns Chat-friendly format
- ✅ All responses include Evidence metadata
- ✅ Error handling is friendly and actionable
- ✅ Attribution is enforced
- ✅ Audit trail linkage works (audit_id present)
- ✅ SSRF protection is active

## Statistics and Monitoring

```python
# Get communication statistics
stats = await adapter.get_statistics()
# Returns: {
#     "total_requests": 134,
#     "success_rate": 79.85,
#     "by_connector": {...}
# }

# List available connectors
connectors = await adapter.list_connectors()
# Returns: {
#     "web_search": {"enabled": true, "operations": ["search"], ...},
#     "web_fetch": {"enabled": true, "operations": ["fetch", "download"], ...}
# }
```

## Future Enhancements

1. **Enhanced citation extraction**: Better author and date extraction from HTML
2. **Content summarization**: AI-powered content summarization
3. **Multi-source verification**: Cross-reference search results with fetched content
4. **Trust tier upgrade paths**: Explicit paths to upgrade trust tiers
5. **Batch operations**: Bulk search and fetch for efficiency

## Related Documentation

- [CommunicationOS Architecture](../communication/ARCHITECTURE.md)
- [Trust Tier System](../communication/TRUST_TIERS.md)
- [Policy Engine](../communication/POLICY_ENGINE.md)
- [Evidence Logging](../communication/EVIDENCE_LOGGING.md)
