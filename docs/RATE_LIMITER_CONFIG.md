# AutoComm Rate Limiting and Deduplication Configuration

## Overview

The AutoComm system now includes rate limiting and deduplication mechanisms to prevent abuse and optimize resource usage.

## Configuration Parameters

### Rate Limiting

Located in `agentos/core/chat/rate_limiter.py`:

```python
MAX_REQUESTS_PER_MINUTE = 5
```

- **Description**: Maximum number of AutoComm requests per minute per session
- **Default**: 5 requests/minute
- **Scope**: Per session (different sessions have independent rate limits)
- **Window**: Rolling 1-minute window

### Deduplication

Located in `agentos/core/chat/rate_limiter.py`:

```python
DEDUP_WINDOW_SECONDS = 300  # 5 minutes
```

- **Description**: Time window for deduplication cache
- **Default**: 300 seconds (5 minutes)
- **Scope**: Per session (same query in different sessions is not considered duplicate)
- **Hash**: SHA-256 hash of query text (case-sensitive)

## How It Works

### Rate Limiting

1. **Per-Session Tracking**: Each session has an independent request log
2. **Rolling Window**: Only requests in the last 1 minute are counted
3. **Quota Management**: When limit is reached, subsequent requests are blocked with a clear error message
4. **Automatic Reset**: Old requests expire automatically after 1 minute

### Deduplication

1. **Query Hashing**: Each query is hashed using SHA-256 (first 16 chars)
2. **Cache Storage**: Results are cached with timestamp
3. **Cache Hit**: If same query is submitted within window, cached result is returned
4. **Cache Expiration**: Cache entries expire after `DEDUP_WINDOW_SECONDS`
5. **Session Isolation**: Same query in different sessions is not deduplicated

## Integration Points

### ChatEngine Integration

The rate limiter and dedup checker are integrated into `ChatEngine._handle_external_info_need()`:

```python
# 1. Check rate limit
allowed, remaining = rate_limiter.check_rate_limit(session_id)
if not allowed:
    # Return rate limit error message
    ...

# 2. Check deduplication
is_duplicate, cached_result = dedup_checker.check_duplicate(session_id, message)
if is_duplicate:
    # Return cached result
    return cached_result

# 3. Execute AutoComm
result = self._execute_auto_comm_search(...)

# 4. Store result for deduplication
dedup_checker.store_result(session_id, message, result)
```

## Observability

### Rate Limit Events

When rate limit is hit, the following metadata is included in the response:

```python
{
    "auto_comm_rate_limited": True,
    "remaining_quota": 0
}
```

And logged with:

```python
logger.warning(
    "AutoComm rate limited",
    extra={
        "event": "AUTOCOMM_RATE_LIMITED",
        "session_id": session_id,
        "quota_limit": rate_limiter.max_requests
    }
)
```

### Deduplication Events

When a duplicate query is detected:

```python
logger.info(
    "AutoComm duplicate query",
    extra={
        "event": "AUTOCOMM_DUPLICATE",
        "session_id": session_id,
        "query": message[:100]
    }
)
```

## Testing

### Unit Tests

Located in `tests/core/chat/test_rate_limiter.py`:

- **RateLimiter Tests**: 4 tests covering limit enforcement, session isolation, and window reset
- **DedupChecker Tests**: 7 tests covering deduplication logic, cache expiration, and session isolation
- **Integration Tests**: 2 tests covering combined behavior

Run tests:

```bash
pytest tests/core/chat/test_rate_limiter.py -v
```

Expected output: **13 passed**

### Manual Testing

1. **Rate Limit Test**:
   - Send 6 identical queries in quick succession
   - 6th request should return rate limit error

2. **Deduplication Test**:
   - Send same query twice within 5 minutes
   - 2nd request should return cached result

## Customization

To adjust the limits, edit `agentos/core/chat/rate_limiter.py`:

```python
# Increase rate limit to 10 requests/minute
MAX_REQUESTS_PER_MINUTE = 10

# Extend dedup window to 10 minutes
DEDUP_WINDOW_SECONDS = 600
```

**Note**: No restart required - changes take effect on next import.

## Known Limitations

1. **In-Memory Storage**: Rate limits and cache are stored in memory and reset on process restart
2. **No Cross-Process Sync**: Different processes have independent limits (acceptable for staging)
3. **Case-Sensitive Dedup**: "Weather" and "weather" are treated as different queries
4. **No User-Level Limits**: Only session-level limits (no global per-user limits across sessions)

## Future Enhancements

For production deployment, consider:

1. **Redis Backend**: Replace in-memory storage with Redis for persistence and cross-process sync
2. **User-Level Limits**: Add per-user rate limiting across sessions
3. **Case-Insensitive Dedup**: Normalize query text before hashing
4. **Semantic Dedup**: Use embeddings to detect semantically similar queries
5. **Configurable Limits**: Allow per-user or per-tenant custom limits
