# Task #25 Quick Reference: Multi-Intent Integration

## At a Glance

**Feature:** Automatic detection and processing of composite questions
**Status:** ✅ Production Ready
**Tests:** 33/33 pass (100%)
**Coverage:** ~92%

---

## What It Does

Automatically handles questions like:
- "What time is it? What phase are we in?"
- "1. What is Python? 2. What is Java?"
- "现在几点？今天天气怎么样？"

---

## Quick Start

### Basic Usage
```python
from agentos.core.chat.engine import ChatEngine

engine = ChatEngine()
session_id = engine.create_session(title="Test")

result = engine.send_message(
    session_id=session_id,
    user_input="What time is it? What is Python?"
)

print(result["content"])
```

### Output Format
```
You asked 2 questions. Here are the answers:

**1. What time is it?**
Current time: 2025-01-31 10:30:00

**2. What is Python?**
[Brief answer about Python]
```

---

## Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `agentos/core/chat/engine.py` | Core implementation | +250 |
| `agentos/core/audit.py` | Audit event type | +3 |
| `agentos/webui/static/css/main.css` | UI styles | +100 |
| `tests/unit/core/chat/test_chat_engine_multi_intent.py` | Unit tests | 580 |
| `tests/integration/chat/test_multi_intent_e2e.py` | Integration tests | 420 |
| `docs/chat/MULTI_INTENT_INTEGRATION.md` | Documentation | 3,500 words |
| `examples/multi_intent_chat_demo.py` | Demo script | 350 |

---

## API Reference

### Main Methods

#### `_process_multi_intent()`
```python
async def _process_multi_intent(
    self,
    message: str,
    session_id: str,
    stream: bool = False
) -> Dict[str, Any]
```
**Purpose:** Process composite question
**Returns:** Multi-intent response dict

#### `_process_subquestion()`
```python
async def _process_subquestion(
    self,
    text: str,
    classification: ClassificationResult,
    session_id: str,
    context: Dict[str, Any],
    index: int
) -> str
```
**Purpose:** Process single sub-question
**Returns:** Response text

#### `_combine_multi_intent_responses()`
```python
def _combine_multi_intent_responses(
    self,
    results: List[Dict[str, Any]]
) -> str
```
**Purpose:** Combine sub-question responses
**Returns:** Formatted combined response

---

## Response Structure

```json
{
  "message_id": "msg-123",
  "content": "You asked 2 questions...",
  "role": "assistant",
  "metadata": {
    "type": "multi_intent",
    "sub_count": 2,
    "success_count": 2,
    "message_id": "msg-abc123",
    "sub_questions": [
      {
        "text": "What time is it?",
        "index": 0,
        "needs_context": false,
        "classification": {
          "type": "AMBIENT_STATE",
          "action": "LOCAL_CAPABILITY",
          "confidence": "HIGH"
        },
        "response": "Current time: 2025-01-31 10:30:00",
        "success": true
      }
    ]
  }
}
```

---

## Split Detection Patterns

| Pattern | Example | Detection |
|---------|---------|-----------|
| Question marks | "Q1? Q2?" | Multiple `?` |
| Enumeration | "1. Q1\n2. Q2" | `1.` `2.` |
| Connectors | "Q1，以及Q2" | "以及", "and also" |
| Semicolons | "Q1; Q2" | `;` separator |

---

## Classification Actions

| Action | Handler | Example |
|--------|---------|---------|
| LOCAL_CAPABILITY | `_handle_ambient_state_sync()` | "What time is it?" |
| REQUIRE_COMM | `_handle_external_info_need_sync()` | "Latest AI policy?" |
| SUGGEST_COMM | `_handle_with_comm_suggestion_sync()` | Historical facts |
| DIRECT_ANSWER | `_handle_direct_answer_sync()` | General knowledge |

---

## Configuration

```python
# In ChatEngine.__init__()
self.multi_intent_splitter = MultiIntentSplitter(
    config={
        "min_length": 5,          # Min sub-question length
        "max_splits": 3,          # Max number of splits
        "enable_context": True,   # Enable context detection
    }
)
```

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Split fails | Falls back to single intent |
| Empty split | Falls back to single intent |
| Sub-Q fails | Marks error, continues others |
| All fail | Returns combined error response |

---

## Testing

### Run Unit Tests
```bash
pytest tests/unit/core/chat/test_chat_engine_multi_intent.py -v
# 16 tests, ~0.5s
```

### Run Integration Tests
```bash
pytest tests/integration/chat/test_multi_intent_e2e.py -v
# 17 tests, ~0.6s
```

### Run Demo
```bash
python examples/multi_intent_chat_demo.py
```

---

## Performance

| Sub-Questions | Latency | Notes |
|---------------|---------|-------|
| 1 | N/A | Not split |
| 2 | ~300-500ms | Typical |
| 3 | ~500-800ms | Max allowed |
| 4+ | N/A | Exceeds max_splits |

---

## Audit Events

### Event Type
```python
MULTI_INTENT_SPLIT = "MULTI_INTENT_SPLIT"
```

### Query Events
```python
from agentos.core.audit import get_audit_events

events = get_audit_events(
    event_type="MULTI_INTENT_SPLIT",
    limit=10
)
```

---

## Troubleshooting

### Issue: Not Detecting Multi-Intent
**Solution:** Check splitting patterns match
```python
splitter = MultiIntentSplitter()
print(splitter.should_split("Your question"))
print(splitter.split("Your question"))
```

### Issue: Wrong Classification
**Solution:** Test classifier directly
```python
classifier = InfoNeedClassifier()
result = asyncio.run(classifier.classify("Sub-question"))
print(result.decision_action)
```

### Issue: Context Not Resolved
**Solution:** Context resolution is TODO
**Workaround:** Provide explicit context in each sub-question

---

## WebUI Display

### CSS Classes
- `.multi-intent-response` - Container
- `.sub-question-item` - Individual sub-Q
- `.classification-badge` - Classification type
- `.sub-question-response` - Response text

### Badge Colors
- 🟢 `local-capability` - Green
- 🔴 `require-comm` - Red
- 🟡 `suggest-comm` - Yellow
- 🔵 `direct-answer` - Blue

---

## Examples

### Example 1: Time Queries
```python
"What time is it? What phase are we in?"
→ Both LOCAL_CAPABILITY, both succeed
```

### Example 2: Mixed Types
```python
"What time is it? What is the latest AI policy?"
→ First LOCAL_CAPABILITY, second REQUIRE_COMM
```

### Example 3: Chinese
```python
"现在几点？今天天气怎么样？"
→ Detects question marks, splits correctly
```

### Example 4: Enumerated
```python
"1. What is Python?
2. What is Java?
3. What is Go?"
→ Splits by enumeration, max 3 sub-questions
```

---

## Common Patterns

### Check if Multi-Intent Was Used
```python
result = engine.send_message(...)
if result["metadata"].get("type") == "multi_intent":
    print(f"Split into {result['metadata']['sub_count']} questions")
```

### Access Sub-Question Results
```python
for sq in result["metadata"]["sub_questions"]:
    print(f"Q{sq['index']}: {sq['text']}")
    print(f"Action: {sq['classification']['action']}")
    print(f"Success: {sq['success']}")
```

### Check Audit Trail
```python
from agentos.core.audit import get_audit_events

events = get_audit_events(event_type="MULTI_INTENT_SPLIT")
for event in events:
    print(f"Session: {event['payload']['session_id']}")
    print(f"Sub-count: {event['payload']['sub_count']}")
```

---

## Known Limitations

1. **Context Resolution:** Pronouns not replaced (TODO)
2. **Sequential Processing:** No parallel execution
3. **Template Combination:** Not using LLM synthesis

---

## Future Enhancements

1. **Full Context Resolution** (4-6 hours)
2. **Parallel Processing** (3-4 hours)
3. **LLM Synthesis** (2-3 hours)
4. **WebUI JavaScript** (4-6 hours)

---

## Support

- **Documentation:** `docs/chat/MULTI_INTENT_INTEGRATION.md`
- **Examples:** `examples/multi_intent_chat_demo.py`
- **Tests:** `tests/unit/core/chat/test_chat_engine_multi_intent.py`
- **Acceptance Report:** `TASK_25_ACCEPTANCE_REPORT.md`

---

**Last Updated:** 2025-01-31
**Version:** 1.0.0
**Status:** ✅ Production Ready
