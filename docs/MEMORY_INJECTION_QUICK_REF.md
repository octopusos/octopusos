# Memory Injection Quick Reference (Task #8)

## Overview

Task #8 enhanced Memory injection in system prompts to ensure LLMs actually use Memory facts, especially `preferred_name`.

---

## Key Features

### 1. High Priority Placement
Memory facts appear at the **top** of the system prompt, immediately after the base prompt.

### 2. Visual Emphasis
- **Separators**: `============================================================`
- **Symbols**: ⚠️ (warning), 👤 (identity), 🎯 (preferences), 📋 (information)
- **Header**: "CRITICAL USER CONTEXT (MUST FOLLOW)"

### 3. Strong Enforcement
- Uses imperative "MUST" language
- Explicit "Do NOT use..." warnings
- Clear directives for LLM behavior

### 4. Categorization
Memory facts are organized into three sections:
- **👤 USER IDENTITY**: `preferred_name` and identity-related facts
- **🎯 USER PREFERENCES**: Other user preferences
- **📋 USER INFORMATION**: General facts (contact, company, etc.)

---

## Example Output

```
============================================================
⚠️  CRITICAL USER CONTEXT (MUST FOLLOW)
============================================================

👤 USER IDENTITY:
   The user prefers to be called: "胖哥"
   ⚠️  You MUST address the user as "胖哥" in all responses.
   ⚠️  Do NOT use generic terms like "user" or "you" - use "胖哥".

🎯 USER PREFERENCES:
  • language: zh-CN
  • response_style: concise

📋 USER INFORMATION:
  • Works at OpenAI
  • Located in San Francisco

============================================================
```

---

## Usage

### Creating Memory Facts

**Preferred Name** (most important):
```python
{
    "scope": "global",
    "type": "preference",
    "content": {
        "key": "preferred_name",
        "value": "胖哥"
    },
    "confidence": 0.9
}
```

**Other Preferences**:
```python
{
    "scope": "global",
    "type": "preference",
    "content": {
        "key": "language",
        "value": "zh-CN"
    },
    "confidence": 0.85
}
```

**Facts**:
```python
{
    "scope": "project",
    "type": "project_fact",
    "content": {
        "summary": "This project uses Python 3.11"
    },
    "confidence": 0.8
}
```

### Checking Memory Injection

**Logs**:
```bash
# Check if Memory was loaded
grep "Memory context loaded" logs/agentos.log

# Example output:
INFO: Memory context loaded: 3 facts (preferred_name=present)
```

**Audit Events**:
```sql
-- Query audit table
SELECT *
FROM task_audits
WHERE event_type = 'MEMORY_CONTEXT_INJECTED'
ORDER BY created_at DESC
LIMIT 10;
```

---

## Debugging

### Memory Not Appearing in Prompt

1. **Check Memory exists**:
   ```sql
   SELECT * FROM memory_items WHERE type = 'preference';
   ```

2. **Check scope is correct**:
   - `preferred_name` should have `scope = "global"`
   - Verify `project_id` is NULL for global scope

3. **Check session metadata**:
   ```sql
   SELECT metadata FROM chat_sessions WHERE session_id = 'your-session-id';
   ```

4. **Enable debug logging**:
   ```python
   import logging
   logging.getLogger("agentos.core.chat.context_builder").setLevel(logging.DEBUG)
   ```

### LLM Not Using preferred_name

1. **Verify injection**: Check system prompt contains the enforcement instructions
2. **Check token budget**: Ensure Memory isn't being trimmed
3. **Review LLM response**: Look for other issues (model temperature, etc.)

---

## Integration Points

### Memory Loading (Task #6)
Memory facts are loaded based on scope:
- **Global scope**: Always included
- **Project scope**: Only for current project
- **Agent scope**: Only for current agent type

### Memory Extraction (Task #4)
Auto-extracted Memory facts are automatically injected:
```python
# Task #4 extracts: "User wants to be called 胖哥"
# Task #8 injects it prominently in the prompt
```

### Memory UI (Task #9)
UI badge shows Memory injection status using audit events:
```javascript
// Fetch audit events
fetch('/api/audit?event_type=MEMORY_CONTEXT_INJECTED')
  .then(events => showBadge(events))
```

---

## Configuration

### Context Budget
Memory token allocation:
```python
ContextBudget(
    max_tokens=8000,
    memory_tokens=1000,  # Memory budget
    # ...
)
```

If Memory exceeds budget, facts are trimmed by confidence (highest first).

### Disabling Memory Injection
```python
context_pack = context_builder.build(
    session_id="sess-123",
    user_input="Hello",
    memory_enabled=False  # Disable Memory
)
```

---

## Testing

### Unit Tests
```bash
# Run Memory injection tests
pytest tests/unit/core/chat/test_context_builder_memory_injection.py -v

# Run all context builder tests
pytest tests/unit/core/chat/test_context_builder*.py -v
```

### Demo Script
```bash
# Run demonstration
python examples/memory_prompt_injection_demo.py
```

---

## Best Practices

### 1. Use `preferred_name` Consistently
Always store user's preferred name with:
- `type = "preference"`
- `content.key = "preferred_name"`
- `scope = "global"`

### 2. Set High Confidence
For critical facts like `preferred_name`:
```python
"confidence": 0.9  # High confidence ensures priority
```

### 3. Keep Summaries Concise
For facts without key/value structure:
```python
"content": {
    "summary": "Short, clear description"  # Not a paragraph
}
```

### 4. Monitor Audit Logs
Regularly check `MEMORY_CONTEXT_INJECTED` events to ensure Memory is being used.

### 5. Test with Real LLM
The enhanced prompt significantly improves LLM compliance, but always test with actual model calls.

---

## API Reference

### `ContextBuilder._build_system_prompt()`

**Signature**:
```python
def _build_system_prompt(
    self,
    context_parts: Dict[str, Any],
    session_id: str
) -> str
```

**Parameters**:
- `context_parts`: Dictionary with keys:
  - `memory`: List of memory fact dicts
  - `rag`: List of RAG chunk dicts
  - `summaries`: List of summary artifact dicts
  - `window`: List of recent messages
- `session_id`: Chat session ID

**Returns**: Complete system prompt string

**Memory Fact Structure**:
```python
{
    "id": "mem-123",
    "scope": "global",
    "type": "preference",  # or "user_preference", "project_fact", etc.
    "content": {
        "key": "preferred_name",  # Optional
        "value": "胖哥",          # Optional
        "summary": "..."           # Fallback if key/value not present
    },
    "confidence": 0.9,
    "tags": ["user", "identity"]
}
```

### `ContextBuilder._log_memory_injection_audit()`

**Signature**:
```python
def _log_memory_injection_audit(
    self,
    session_id: str,
    memory_facts: List[Dict[str, Any]],
    usage: ContextUsage
) -> None
```

**Purpose**: Logs `MEMORY_CONTEXT_INJECTED` audit event

**Metadata Captured**:
- `session_id`: Chat session ID
- `memory_count`: Number of memory facts
- `memory_types`: List of memory types
- `has_preferred_name`: Boolean
- `preferred_name`: The actual preferred name value (if present)
- `tokens_memory`: Token count for memory section
- `memory_ids`: List of memory IDs

---

## Troubleshooting

### Issue: Memory not injected

**Symptoms**: System prompt doesn't contain "CRITICAL USER CONTEXT"

**Causes**:
1. No memory facts loaded
2. Memory disabled (`memory_enabled=False`)
3. Memory trimmed due to budget

**Solution**:
```python
# Check memory facts
memory_facts = context_builder._load_memory_facts(session_id)
print(f"Loaded {len(memory_facts)} memory facts")

# Check budget
print(f"Memory budget: {context_builder.budget.memory_tokens} tokens")
```

### Issue: preferred_name not highlighted

**Symptoms**: preferred_name appears in preferences section, not identity section

**Causes**:
1. Memory type is not "preference" or "user_preference"
2. Content doesn't have `key = "preferred_name"`

**Solution**:
```python
# Correct format
{
    "type": "preference",  # or "user_preference"
    "content": {
        "key": "preferred_name",  # Must be exact key
        "value": "胖哥"
    }
}

# Wrong format
{
    "type": "preference",
    "content": {
        "preferred_name": "胖哥"  # Wrong: key is in content, not as a field
    }
}
```

### Issue: LLM still not using preferred_name

**Symptoms**: LLM response uses "you" instead of "胖哥"

**Possible Causes**:
1. Model temperature too high (hallucination)
2. Context window overflow
3. Model doesn't support instruction following well
4. Prompt is being overridden somewhere

**Solution**:
1. Check system prompt is actually being sent to model
2. Reduce temperature to 0.3-0.5
3. Use a better instruction-following model
4. Check for prompt overrides in engine

---

## Related Documentation

- **Task #6 Report**: Memory scope resolution
- **Task #4 Report**: Memory auto-extraction
- **ADR-MEMORY-001**: Memory architecture decisions
- **API Documentation**: `/api/memory` endpoints

---

## Support

For issues or questions:
1. Check logs: `logs/agentos.log`
2. Query audit table: `task_audits`
3. Run demo script: `python examples/memory_prompt_injection_demo.py`
4. Contact: Memory Phase team

---

**Last Updated**: 2026-01-31
**Version**: 1.0 (Task #8 completion)
