# CommunicationAdapter Quick Start Guide

## TL;DR

```python
from agentos.core.chat.communication_adapter import CommunicationAdapter

adapter = CommunicationAdapter()

# Search
result = await adapter.search(query="Python", session_id="s1", task_id="t1")

# Fetch
result = await adapter.fetch(url="https://example.com", session_id="s1", task_id="t1")
```

## Installation

No additional installation needed. The adapter uses existing CommunicationOS infrastructure.

## Basic Usage

### Initialize Once Per Session
```python
from agentos.core.chat.communication_adapter import CommunicationAdapter

adapter = CommunicationAdapter()
```

### Search the Web
```python
result = await adapter.search(
    query="Python best practices",
    session_id="session-123",
    task_id="task-456",
    max_results=10  # optional
)

if "results" in result:
    for item in result["results"]:
        print(f"{item['title']} - {item['url']}")
        print(f"Trust: {item['trust_tier']}")
else:
    print(f"Error: {result['message']}")
```

### Fetch URL Content
```python
result = await adapter.fetch(
    url="https://www.python.org",
    session_id="session-123",
    task_id="task-456"
)

if result["status"] == "success":
    content = result["content"]
    print(f"Title: {content['title']}")
    print(f"Text: {content['text'][:200]}...")
    print(f"Trust: {result['metadata']['trust_tier']}")
else:
    print(f"Error: {result['message']}")
```

## Response Format

### Search Response
```python
{
    "results": [
        {
            "title": "Result Title",
            "url": "https://example.com",
            "snippet": "Result snippet...",
            "trust_tier": "search_result"
        }
    ],
    "metadata": {
        "query": "Python",
        "total_results": 10,
        "trust_tier_warning": "搜索结果是候选来源,不是验证事实",
        "attribution": "CommunicationOS (search) in session session-123",
        "retrieved_at": "2026-01-30T12:31:01.081292+00:00",
        "audit_id": "ev-abc123"
    }
}
```

### Fetch Response
```python
{
    "status": "success",
    "url": "https://example.com",
    "content": {
        "title": "Page Title",
        "description": "Page description",
        "text": "Main content...",
        "links": [...],
        "images": [...]
    },
    "metadata": {
        "trust_tier": "external_source",
        "content_hash": "sha256...",
        "citations": {
            "url": "https://example.com",
            "title": "Page Title",
            "author": "example.com",
            "retrieved_at": "..."
        },
        "attribution": "CommunicationOS (fetch) in session session-123",
        "audit_id": "ev-abc123"
    }
}
```

### Error Response
```python
{
    "status": "blocked",  # or "error", "rate_limited"
    "reason": "SSRF_PROTECTION",
    "message": "该 URL 被安全策略阻止(内网地址或 localhost)",
    "hint": "请使用公开的 HTTPS URL",
    "metadata": {
        "attribution": "CommunicationOS in session session-123"
    }
}
```

## Error Handling

### Check Response Status
```python
result = await adapter.fetch(url=url, session_id=sid, task_id=tid)

if result.get("status") == "success":
    # Process content
    pass
elif result.get("status") == "blocked":
    print(f"Blocked: {result['message']}")
    print(f"Hint: {result['hint']}")
elif result.get("status") == "rate_limited":
    print(f"Rate limited. Retry after {result['retry_after']} seconds")
else:
    print(f"Error: {result.get('message', 'Unknown error')}")
```

## Trust Tiers

All results include trust tier information:

- **search_result**: Search results (candidates only, not verified facts)
- **external_source**: Fetched content (needs verification)
- **primary_source**: Official sites, original documents
- **authoritative**: Government, academia, certified organizations

```python
# Access trust tier
trust = result["metadata"]["trust_tier"]

if trust == "search_result":
    print("⚠️  This is a search result, not a verified fact")
elif trust == "authoritative":
    print("✅ Authoritative source")
```

## Attribution

Every response includes attribution:
```python
attribution = result["metadata"]["attribution"]
# "CommunicationOS (search) in session session-123"
```

This attribution:
- Cannot be removed or modified
- Links the operation to CommunicationOS
- Includes session context

## Audit Trail

Every operation is logged with an audit ID:
```python
audit_id = result["metadata"]["audit_id"]
# "ev-abc123"

# Query audit logs later
evidence = await adapter.service.evidence_logger.get_evidence(audit_id)
```

## Statistics

```python
# Get communication statistics
stats = await adapter.get_statistics()
print(f"Total requests: {stats['total_requests']}")
print(f"Success rate: {stats['success_rate']}%")

# List available connectors
connectors = await adapter.list_connectors()
for name, info in connectors.items():
    print(f"{name}: {info['enabled']}")
```

## Common Patterns

### Search and Fetch Pattern
```python
# 1. Search for relevant URLs
search_result = await adapter.search(
    query="Python tutorials",
    session_id=session_id,
    task_id=task_id
)

# 2. Fetch content from top results
if "results" in search_result:
    for item in search_result["results"][:3]:
        fetch_result = await adapter.fetch(
            url=item["url"],
            session_id=session_id,
            task_id=task_id
        )
        if fetch_result["status"] == "success":
            # Process content
            pass
```

### Error-Safe Pattern
```python
try:
    result = await adapter.fetch(url=url, session_id=sid, task_id=tid)

    if result.get("status") != "success":
        # Handle error gracefully
        logger.warning(f"Fetch failed: {result.get('message')}")
        return None

    return result["content"]

except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return None
```

### Retry Pattern for Rate Limiting
```python
import asyncio

async def fetch_with_retry(adapter, url, session_id, task_id, max_retries=3):
    for attempt in range(max_retries):
        result = await adapter.fetch(url, session_id, task_id)

        if result.get("status") == "rate_limited":
            wait_time = result.get("retry_after", 60)
            print(f"Rate limited. Waiting {wait_time}s...")
            await asyncio.sleep(wait_time)
            continue

        return result

    return {"status": "error", "message": "Max retries exceeded"}
```

## Testing

Run the test suite:
```bash
# Integration test
python3 test_communication_adapter.py

# Examples
python3 examples/chat_communication_adapter_example.py
```

## Security Notes

1. **SSRF Protection**: Internal IPs and localhost are blocked
2. **Rate Limiting**: 30/min for search, 20/min for fetch
3. **All operations are audited**: Check logs with audit_id
4. **Trust tier always tracked**: No unmarked external data

## Getting Help

- Full documentation: `docs/chat/COMMUNICATION_ADAPTER.md`
- Examples: `examples/chat_communication_adapter_example.py`
- Test suite: `test_communication_adapter.py`
- Architecture: `docs/communication/ARCHITECTURE.md`

## Common Issues

### Search Returns Error
**Issue**: "DuckDuckGo search library not installed"
**Solution**: Install DuckDuckGo library:
```bash
pip install ddgs
# or
pip install duckduckgo-search
```

### Fetch Blocked
**Issue**: "该 URL 被安全策略阻止"
**Cause**: URL is internal (localhost, private IP)
**Solution**: Use public HTTPS URLs only

### Rate Limited
**Issue**: "超过速率限制,请等待 X 秒"
**Solution**: Wait for retry_after seconds before retrying

## Quick Reference Card

| Operation | Method | Key Parameters |
|-----------|--------|----------------|
| Search web | `search()` | query, session_id, task_id |
| Fetch URL | `fetch()` | url, session_id, task_id |
| Get stats | `get_statistics()` | - |
| List connectors | `list_connectors()` | - |

| Response Field | Location | Description |
|----------------|----------|-------------|
| Results | `results[]` | Search results array |
| Content | `content{}` | Fetched content object |
| Trust tier | `metadata.trust_tier` | Source trust level |
| Attribution | `metadata.attribution` | Operation attribution |
| Audit ID | `metadata.audit_id` | Evidence record ID |
| Status | `status` | Operation status |

| Trust Tier | Meaning |
|------------|---------|
| search_result | Search results (unverified) |
| external_source | Fetched content |
| primary_source | Official/original source |
| authoritative | Government/academia |
