# Idempotency and Caching System

**Version**: 1.0.0 | **Status**: Implemented | **Date**: 2026-01-29

Comprehensive documentation for AgentOS idempotency and caching system.

---

## Overview

The idempotency and caching system provides three core components to reduce token consumption and avoid redundant operations:

1. **IdempotencyStore** - Request deduplication and result caching
2. **LLMOutputCache** - LLM output caching to save tokens
3. **ToolLedger** - Tool execution recording and replay

### Design Goals

- **Reduce token consumption** - Cache LLM outputs to avoid redundant API calls
- **Avoid redundant executions** - Replay tool results instead of re-executing
- **Enable safe retries** - Idempotency guarantees for crash recovery
- **Track effectiveness** - Monitor cache hit rates and token savings

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ LLMOutput    │    │ ToolLedger   │    │ Application  │  │
│  │ Cache        │    │              │    │ Code         │  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
│         │                   │                   │           │
│         └───────────────────┴───────────────────┘           │
│                             │                               │
├─────────────────────────────┼───────────────────────────────┤
│                    ┌────────▼────────┐                      │
│                    │ Idempotency     │                      │
│                    │ Store           │                      │
│                    └────────┬────────┘                      │
├─────────────────────────────┼───────────────────────────────┤
│                    ┌────────▼────────┐                      │
│                    │ SQLite Database │                      │
│                    │ (idempotency_   │                      │
│                    │  keys table)    │                      │
│                    └─────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

### Database Schema

Uses the `idempotency_keys` table from schema v0.30.0:

```sql
CREATE TABLE idempotency_keys (
    idempotency_key TEXT PRIMARY KEY,
    task_id TEXT,
    work_item_id TEXT,
    request_hash TEXT NOT NULL,
    response_data TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    expires_at TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE SET NULL,
    FOREIGN KEY (work_item_id) REFERENCES work_items(work_item_id) ON DELETE SET NULL
);
```

---

## Component 1: IdempotencyStore

### Purpose

Core store for managing idempotency keys, providing request deduplication and result caching.

### Key Features

- **Atomic check-or-create** - Race-safe idempotency key creation
- **Request hash validation** - Detect conflicts from different requests with same key
- **Result caching** - Store and retrieve operation results
- **Automatic expiration** - Clean up old keys
- **Status tracking** - pending, completed, failed

### API Reference

#### `check(key, request_hash=None) -> Optional[Dict]`

Check if operation already completed.

```python
from agentos.core.idempotency import IdempotencyStore

store = IdempotencyStore()
result = store.check(key="operation-123")

if result:
    print("Cache hit:", result)
else:
    print("Cache miss - need to execute")
```

#### `check_or_create(key, request_hash, ...) -> Tuple[bool, Optional[Dict]]`

Atomic check-then-create operation (recommended).

```python
is_cached, result = store.check_or_create(
    key="operation-123",
    request_hash="sha256:abc...",
    task_id="task-456",
    expires_in_seconds=3600
)

if is_cached:
    return result  # Use cached result
else:
    # Execute operation
    result = expensive_operation()
    store.mark_succeeded("operation-123", result)
    return result
```

#### `mark_succeeded(key, result) -> None`

Mark operation as completed with result.

```python
result = {"status": "success", "data": [...]}
store.mark_succeeded("operation-123", result)
```

#### `mark_failed(key, error) -> None`

Mark operation as failed.

```python
try:
    result = risky_operation()
except Exception as e:
    store.mark_failed("operation-123", str(e))
    raise
```

#### `compute_hash(data) -> str`

Compute deterministic hash for request validation.

```python
request_data = {"prompt": "...", "model": "gpt-4"}
hash_str = IdempotencyStore.compute_hash(request_data)
# Returns: "sha256:abc123..."
```

---

## Component 2: LLMOutputCache

### Purpose

Cache LLM outputs to reduce token consumption and API latency.

### Key Features

- **Automatic caching** - Transparently cache LLM responses
- **Cache key generation** - Hash-based keys from prompt + model + context
- **Hit/miss tracking** - Monitor cache effectiveness
- **Token savings estimation** - Track cost savings
- **Configurable expiration** - Default 7 days

### Cache Key Format

```
llm-cache:{operation_type}:{model}:{prompt_hash}[:task_id][:work_item_id]
```

Example: `llm-cache:plan:gpt-4:a3f2e1b9:task-123`

### API Reference

#### `get_or_generate(operation_type, prompt, model, generate_fn, ...) -> Dict`

Get cached output or generate new one.

```python
from agentos.core.idempotency import LLMOutputCache

cache = LLMOutputCache()

# Cache plan generation
plan = cache.get_or_generate(
    operation_type="plan",
    prompt="Write a plan to implement feature X",
    model="gpt-4",
    task_id="task-123",
    generate_fn=lambda: call_openai_api(prompt)
)

# Returns cached result on subsequent calls with same params
```

#### `invalidate(operation_type, prompt, model, ...) -> None`

Manually invalidate cached entry.

```python
cache.invalidate(
    operation_type="plan",
    prompt="Write a plan to implement feature X",
    model="gpt-4",
    task_id="task-123"
)
```

#### `get_stats() -> Dict`

Get cache statistics.

```python
stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate']:.1%}")
print(f"Cache hits: {stats['cache_hits']}")
print(f"Cache misses: {stats['cache_misses']}")
```

### Usage Examples

#### Example 1: Cache Plan Generation

```python
cache = LLMOutputCache()

def generate_plan(task_description):
    """Generate plan with caching."""
    prompt = f"Generate a plan for: {task_description}"

    return cache.get_or_generate(
        operation_type="plan",
        prompt=prompt,
        model="gpt-4",
        task_id=current_task_id,
        generate_fn=lambda: {
            "content": call_llm(prompt),
            "tokens": 150,
            "model": "gpt-4"
        }
    )

# First call - executes LLM
plan1 = generate_plan("Build user authentication")

# Second call - returns cached result (no LLM call)
plan2 = generate_plan("Build user authentication")

assert plan1 == plan2  # Same result
```

#### Example 2: Cache Work Item Outputs

```python
def execute_work_item(work_item):
    """Execute work item with caching."""
    cache = LLMOutputCache()

    prompt = work_item["prompt"]

    return cache.get_or_generate(
        operation_type="work_item",
        prompt=prompt,
        model="gpt-4",
        task_id=work_item["task_id"],
        work_item_id=work_item["work_item_id"],
        generate_fn=lambda: {
            "result": execute_llm_call(prompt),
            "tokens": 200
        }
    )
```

---

## Component 3: ToolLedger

### Purpose

Record tool executions and replay results on retry, avoiding redundant tool calls.

### Key Features

- **Execution recording** - Record exit code, stdout, stderr
- **Result replay** - Return cached results instead of re-executing
- **Hash-based validation** - Command hash for cache keys
- **Large output handling** - Hash stdout/stderr > 10KB
- **Execution history** - Query past executions

### Ledger Key Format

```
tool-ledger:{tool_name}:{command_hash}[:task_id][:work_item_id]
```

Example: `tool-ledger:bash:a3f2e1b9:task-123`

### API Reference

#### `execute_or_replay(tool_name, command, execute_fn, ...) -> Dict`

Execute tool or replay cached result.

```python
from agentos.core.idempotency import ToolLedger

ledger = ToolLedger()

# Execute or replay bash command
result = ledger.execute_or_replay(
    tool_name="bash",
    command="ls -la",
    task_id="task-123",
    execute_fn=lambda: run_bash_command("ls -la")
)

print(f"Exit code: {result['exit_code']}")
print(f"Stdout: {result['stdout']}")
print(f"Replayed: {result['replayed']}")
```

#### `get_execution_history(task_id, limit=100) -> List[Dict]`

Get tool execution history for a task.

```python
history = ledger.get_execution_history("task-123", limit=50)

for entry in history:
    print(f"{entry['key']}: exit_code={entry['exit_code']}")
```

#### `get_stats() -> Dict`

Get execution statistics.

```python
stats = ledger.get_stats()
print(f"Replay rate: {stats['replay_rate']:.1%}")
print(f"Executions: {stats['executions']}")
print(f"Replays: {stats['replays']}")
```

### Usage Examples

#### Example 1: Record Bash Execution

```python
ledger = ToolLedger()

def run_bash(command, task_id):
    """Run bash command with ledger recording."""
    return ledger.execute_or_replay(
        tool_name="bash",
        command=command,
        task_id=task_id,
        execute_fn=lambda: subprocess.run(
            ["bash", "-c", command],
            capture_output=True,
            text=True,
            timeout=30
        )
    )

# First run - executes command
result1 = run_bash("echo hello", "task-123")
assert result1["replayed"] == False

# Second run - replays cached result
result2 = run_bash("echo hello", "task-123")
assert result2["replayed"] == True
assert result2["stdout"] == result1["stdout"]
```

#### Example 2: Force Re-execution

```python
# Force execution even if cached
result = ledger.execute_or_replay(
    tool_name="bash",
    command="date",
    task_id="task-123",
    force_execute=True,  # Bypass cache
    execute_fn=lambda: get_current_date()
)
```

---

## Integration Patterns

### Pattern 1: Task Execution with Full Caching

```python
from agentos.core.idempotency import LLMOutputCache, ToolLedger

def execute_task_with_caching(task):
    """Execute task with full LLM and tool caching."""
    llm_cache = LLMOutputCache()
    tool_ledger = ToolLedger()

    # 1. Generate plan (cached)
    plan = llm_cache.get_or_generate(
        operation_type="plan",
        prompt=f"Create plan for: {task['description']}",
        model="gpt-4",
        task_id=task["id"],
        generate_fn=lambda: generate_plan_via_llm(task)
    )

    # 2. Execute steps (cached)
    for step in plan["steps"]:
        # Execute tool with replay
        result = tool_ledger.execute_or_replay(
            tool_name=step["tool"],
            command=step["command"],
            task_id=task["id"],
            execute_fn=lambda: run_tool(step["tool"], step["command"])
        )

        # Analyze result with LLM (cached)
        analysis = llm_cache.get_or_generate(
            operation_type="analysis",
            prompt=f"Analyze: {result['stdout']}",
            model="gpt-4",
            task_id=task["id"],
            generate_fn=lambda: analyze_via_llm(result)
        )

    return {"status": "completed", "plan": plan}
```

### Pattern 2: Recovery with Cache

```python
def recover_task(task_id):
    """Recover task execution using cached results."""
    llm_cache = LLMOutputCache()
    tool_ledger = ToolLedger()

    # Get execution history
    history = tool_ledger.get_execution_history(task_id)

    # Resume from last checkpoint
    for entry in history:
        if entry["status"] == "completed":
            print(f"Replaying: {entry['key']}")
            # Tool results will be replayed automatically

    # Continue execution with caching
    # ...
```

### Pattern 3: Cache Statistics Monitoring

```python
def monitor_cache_effectiveness():
    """Monitor cache hit rates and savings."""
    llm_cache = LLMOutputCache()
    tool_ledger = ToolLedger()

    # Get statistics
    llm_stats = llm_cache.get_stats()
    tool_stats = tool_ledger.get_stats()

    print(f"LLM Cache Hit Rate: {llm_stats['hit_rate']:.1%}")
    print(f"Tool Replay Rate: {tool_stats['replay_rate']:.1%}")

    # Estimate token savings (500 tokens/request average)
    tokens_saved = llm_stats['cache_hits'] * 500
    cost_saved = (tokens_saved / 1000) * 0.03  # $0.03 per 1K tokens

    print(f"Estimated tokens saved: {tokens_saved:,}")
    print(f"Estimated cost saved: ${cost_saved:.2f}")
```

---

## Monitoring and Statistics

### Command-line Statistics

Use the `print_token_savings.py` script:

```bash
# Print human-readable stats
python scripts/tools/print_token_savings.py

# Print JSON format
python scripts/tools/print_token_savings.py --format json

# Filter by task
python scripts/tools/print_token_savings.py --task-id task-123
```

### Example Output

```
======================================================================
IDEMPOTENCY & CACHING STATISTICS
======================================================================

Overall:
  Total Keys: 1,234
  Completed:  1,100
  Pending:    10
  Failed:     24
  First:      2026-01-29 10:00:00
  Last:       2026-01-29 15:30:00

LLM Output Cache:
  Total Requests:  450
  Cache Hits:      320 (71.1%)
  Cache Misses:    120
  In Progress:     5
  Failures:        5

  Estimated Savings:
    Tokens:      ~160,000
    Cost:        ~$4.80
    (assuming 500 tokens/request)

Tool Execution Ledger:
  Total Operations: 780
  Replays:          580 (74.4%)
  Executions:       190
  In Progress:      5
  Failures:         5

======================================================================
```

---

## Best Practices

### ✅ DO

1. **Use check_or_create()** - Atomic operation prevents race conditions
2. **Include task/work_item IDs** - Better tracking and debugging
3. **Set reasonable expiration** - Default 7 days for LLM, 30 days for tools
4. **Monitor cache hit rates** - Track effectiveness with get_stats()
5. **Handle failures gracefully** - Use mark_failed() to track errors
6. **Use deterministic prompts** - Same input = same cache key
7. **Invalidate when needed** - Manually invalidate stale cache entries

### ❌ DON'T

1. **Don't use random prompts** - Random elements prevent cache hits
2. **Don't skip request hashing** - Hashing detects conflicts
3. **Don't cache time-sensitive data** - Use force_execute for current data
4. **Don't store huge results** - Large outputs are automatically hashed
5. **Don't reuse keys incorrectly** - Different operations need different keys
6. **Don't ignore expiration** - Set appropriate expires_at values
7. **Don't assume cache hits** - Always handle cache misses

---

## Troubleshooting

### Problem: Low cache hit rate

**Diagnosis**:
```python
stats = cache.get_stats()
if stats['hit_rate'] < 0.3:
    print("Cache hit rate is low!")
```

**Solutions**:
- Ensure prompts are deterministic (no random elements)
- Check if task_id/work_item_id are consistent
- Verify model names match exactly
- Check cache expiration settings

---

### Problem: Cache conflicts

**Error**: `IdempotencyConflictError: Same key used with different request`

**Cause**: Same idempotency key used with different request parameters.

**Solution**:
```python
# Include all relevant parameters in cache key
cache_key = f"operation:{task_id}:{step_id}:{timestamp}"
```

---

### Problem: Memory growth from large outputs

**Symptom**: Database size growing rapidly

**Solution**: Large outputs are automatically hashed. If needed, adjust threshold:

```python
# In tool_ledger.py
result = ledger._hash_large_outputs(result, size_threshold=5000)
```

---

## Performance Considerations

### Cache Hit Rate Impact

| Hit Rate | Token Savings | Latency Reduction |
|----------|---------------|-------------------|
| 50% | 50% fewer API calls | 50% faster |
| 70% | 70% fewer API calls | 70% faster |
| 90% | 90% fewer API calls | 90% faster |

### Storage Growth

- **LLM cache**: ~1KB per entry
- **Tool ledger**: ~500 bytes per entry (small outputs), ~2KB (hashed large outputs)
- **Cleanup**: Automatic expiration handles cleanup

### Database Indexes

Optimized indexes on `idempotency_keys` table ensure fast lookups:
- Primary key on `idempotency_key`
- Index on `(task_id, created_at DESC)`
- Index on `(work_item_id, created_at DESC)`

---

## Testing

### Unit Tests

```bash
# Run LLM cache tests
python tests/integration/test_llm_cache.py

# Run tool ledger tests
python tests/integration/test_tool_ledger.py
```

### Integration Tests

Both test files include comprehensive integration tests:
- Cache hit/miss behavior
- Statistics tracking
- Error handling
- Replay functionality
- Large output handling

---

## Future Enhancements

1. **Distributed caching** - Redis/Memcached support
2. **Cache warming** - Pre-populate common queries
3. **Smart invalidation** - Automatic invalidation on dependency changes
4. **Compression** - Compress large cached results
5. **Analytics** - Advanced cache effectiveness analytics
6. **TTL policies** - Per-operation-type expiration policies

---

## References

- Database Schema: `docs/specs/RECOVERY_DATABASE_SCHEMA.md`
- Quick Reference: `docs/specs/RECOVERY_QUICK_REFERENCE.md`
- Migration: `agentos/store/migrations/schema_v30.sql`
- Source Code: `agentos/core/idempotency/`

---

**Document Version**: 1.0.0
**Last Updated**: 2026-01-29
**Maintained By**: AgentOS Team
