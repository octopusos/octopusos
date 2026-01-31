# InfoNeedClassifier Integration - Quick Reference

**Version**: 1.0
**Date**: 2026-01-31

## What It Does

The InfoNeedClassifier automatically analyzes user questions and determines the best way to handle them:

- 🔍 **Detects external info needs** before wasting time on outdated answers
- ⚡ **Fast-tracks ambient queries** (time, phase, status) without LLM
- 🛡️ **Enforces phase gates** to prevent external communication in planning phase
- 💡 **Suggests verification** when answers might be outdated

## Classification Types

### 1. LOCAL_CAPABILITY (Ambient State)

**What it is**: Questions about system state that don't need LLM

**Examples**:
- "What time is it?"
- "What execution phase am I in?"
- "Show me the current session info"

**Behavior**:
- Direct system response
- No LLM invocation
- < 10ms response time

### 2. REQUIRE_COMM (External Facts)

**What it is**: Questions requiring up-to-date or authoritative information

**Examples**:
- "What is the latest AI policy?"
- "What happened today in tech news?"
- "What is the current Python version?"

**Behavior**:
- Blocks with suggestion to use `/comm`
- Phase gate enforced (planning → must switch to execution)
- No answer provided until user uses `/comm`

### 3. SUGGEST_COMM (Verification Recommended)

**What it is**: Questions that can be answered but verification is recommended

**Examples**:
- "What are Python 3.13 features?" (might have recent updates)
- "What is the best way to structure a REST API?" (opinions vary)

**Behavior**:
- Provides full LLM answer
- Adds disclaimer + suggested `/comm` command
- User decides: accept answer or verify

### 4. DIRECT_ANSWER (Normal Flow)

**What it is**: Questions that can be answered directly from LLM knowledge

**Examples**:
- "Explain the concept of closures"
- "How do I write a for loop in Python?"
- "What is dependency injection?"

**Behavior**:
- Normal ChatEngine flow
- Full LLM answer
- No classification overhead

## Usage Examples

### Example 1: Ambient State Query

**User Input**:
```
What time is it?
```

**Classification**: LOCAL_CAPABILITY

**Response**:
```
Current time: 2026-01-31 13:45:23
```

**No LLM invocation, instant response**

---

### Example 2: External Info Need (Execution Phase)

**User Input**:
```
What is the latest AI policy announced today?
```

**Classification**: REQUIRE_COMM

**Response**:
```
🔍 External information required

Question: What is the latest AI policy announced today?
Type: external_fact_uncertain
Reason: Time-sensitive query with authoritative keywords

Suggested action:
`/comm search What is the latest AI policy announced today?`

If you prefer, I can answer based on my existing knowledge,
but the information may not be current or authoritative.
```

---

### Example 3: External Info Need (Planning Phase)

**User Input**:
```
What is the latest AI news?
```

**Current Phase**: planning

**Classification**: REQUIRE_COMM

**Response**:
```
⚠️ This question requires external information, but the current
execution phase is 'planning'.

Question type: external_fact_uncertain
Reason: Time-sensitive keywords detected

To get external information, you need to:
1. Switch to execution phase: `/phase execution`
2. Use the communication command: `/comm search <query>`

Alternatively, I can provide an answer based on my existing knowledge,
but it may not be up-to-date.
```

---

### Example 4: Suggest Verification

**User Input**:
```
What are the latest Python 3.13 features?
```

**Classification**: SUGGEST_COMM

**Response**:
```
Python 3.13 introduces several new features:

1. **Per-Interpreter GIL**: Experimental support for per-interpreter
   GIL, allowing true parallelism in subinterpreters.

2. **Improved Error Messages**: Enhanced error messages with better
   context and suggestions.

3. **Performance Improvements**: Optimizations in the bytecode
   interpreter and memory management.

[... full answer ...]

---
💡 Note: This answer is based on my existing knowledge and may not
reflect the latest information.
To verify or get current information, use: `/comm search What are the latest Python 3.13 features?`
```

## How to Test Locally

### Quick Test

```bash
python3 test_chat_engine_integration.py
```

### Manual Test in Python

```python
from agentos.core.chat.engine import ChatEngine

# Create engine
engine = ChatEngine()

# Create session in execution phase
session_id = engine.create_session(
    title="Test Session",
    metadata={"execution_phase": "execution"}
)

# Test ambient state query
response1 = engine.send_message(session_id, "What time is it?")
print(response1['content'])

# Test external info need
response2 = engine.send_message(session_id, "What is the latest AI news?")
print(response2['content'])

# Check metadata
print(response2['metadata'])
# Expected: {'classification': 'require_comm', 'info_need_type': 'external_fact_uncertain', ...}
```

## Metadata Structure

Every classified message includes metadata:

```python
metadata = {
    "classification": str,        # "local_capability" | "require_comm" | "suggest_comm"
    "info_need_type": str,        # "ambient_state" | "external_fact_uncertain" | ...
    "confidence": str,            # "high" | "medium" | "low"
    "execution_phase": str,       # "planning" | "execution"
    "context_tokens": int,        # (if LLM invoked)
    "model_route": str,           # (if LLM invoked)
}
```

## Decision Matrix

| Info Need Type | Confidence | Decision |
|----------------|------------|----------|
| LOCAL_DETERMINISTIC | Any | LOCAL_CAPABILITY |
| AMBIENT_STATE | Any | LOCAL_CAPABILITY |
| LOCAL_KNOWLEDGE | High | DIRECT_ANSWER |
| LOCAL_KNOWLEDGE | Medium | DIRECT_ANSWER |
| LOCAL_KNOWLEDGE | Low | SUGGEST_COMM |
| EXTERNAL_FACT_UNCERTAIN | Any | REQUIRE_COMM |
| OPINION | High | DIRECT_ANSWER |
| OPINION | Medium | SUGGEST_COMM |
| OPINION | Low | REQUIRE_COMM |

## Performance

### Classification Speed

- **Rule-based only**: < 10ms (most cases)
- **With LLM evaluation**: 500ms - 2000ms (selective)

### When LLM Evaluation is Used

LLM evaluation is **only** triggered when:
- Type is LOCAL_KNOWLEDGE or OPINION
- Rule signals are weak (< 0.5 strength)

**Never** for:
- LOCAL_DETERMINISTIC (always local tools)
- AMBIENT_STATE (always local tools)
- EXTERNAL_FACT_UNCERTAIN with strong signals (clearly needs comm)

## Configuration

### Current Defaults

```python
config = {
    "enable_llm_evaluation": True,
    "llm_threshold": 0.5
}
```

### Disable LLM Evaluation (for testing)

```python
classifier = InfoNeedClassifier(
    config={"enable_llm_evaluation": False}
)
```

## Troubleshooting

### Issue: Classification always returns DIRECT_ANSWER

**Cause**: Classification is failing silently

**Solution**:
1. Check logs for classification errors
2. Verify LLM service is running (Ollama at http://127.0.0.1:11434)
3. Test classifier directly:

```python
import asyncio
from agentos.core.chat.info_need_classifier import InfoNeedClassifier

classifier = InfoNeedClassifier()
result = asyncio.run(classifier.classify("What time is it?"))
print(result.decision_action)  # Should be LOCAL_CAPABILITY
```

### Issue: LLM evaluation is slow

**Cause**: LLM service is slow or overloaded

**Solution**:
1. Use a faster local model
2. Disable LLM evaluation temporarily:
   ```python
   config={"enable_llm_evaluation": False}
   ```
3. Increase `llm_threshold` to reduce LLM calls:
   ```python
   config={"llm_threshold": 0.7}
   ```

### Issue: Phase gate not working

**Cause**: Session metadata doesn't have execution_phase

**Solution**:
```python
# Always set execution_phase when creating session
session_id = engine.create_session(
    title="Test",
    metadata={"execution_phase": "planning"}  # or "execution"
)
```

## Integration Points

### ChatEngine Flow

```
send_message()
    ↓
1. Check slash command
    ↓
2. Classify message → [Route to handler OR continue]
    ↓
3. Build context
    ↓
4. Invoke model
    ↓
5. Save response
```

### Handler Methods

```python
# Ambient state (no LLM)
_handle_ambient_state(session_id, message, classification, context, stream)

# External info need (no LLM, suggest /comm)
_handle_external_info_need(session_id, message, classification, context, stream)

# With suggestion (LLM + disclaimer)
_handle_with_comm_suggestion(session_id, message, classification, context, stream)
```

## Key Design Principles

1. **Non-breaking**: All existing functionality unchanged
2. **Fast path**: Ambient queries bypass LLM entirely
3. **Selective LLM**: Only use LLM evaluation when needed
4. **Graceful degradation**: Classification failure → normal flow
5. **Phase enforcement**: Respect planning/execution boundaries
6. **User control**: Suggest, don't force (except phase gates)

## Related Documentation

- **Architecture**: `docs/adr/ADR-INFO-NEED-CLASSIFIER-001.md`
- **Models**: `agentos/core/chat/models/info_need.py`
- **Classifier**: `agentos/core/chat/info_need_classifier.py`
- **Integration**: `docs/INFO_NEED_CLASSIFIER_INTEGRATION_SUMMARY.md`
- **Test Matrix**: `docs/testing/INFO_NEED_TEST_MATRIX.md`

---

**Quick Start**: Run `python3 test_chat_engine_integration.py` to verify integration
