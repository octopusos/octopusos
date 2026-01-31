# InfoNeedClassifier Quick Reference

**One-page quick reference for developers**

---

## Five Types (One-Sentence Summary)

| Type | Summary | Action |
|------|---------|--------|
| **LOCAL_DETERMINISTIC** | Code structure, file existence - use local tools | LOCAL_CAPABILITY |
| **LOCAL_KNOWLEDGE** | Stable concepts, best practices - answer from training | DIRECT_ANSWER (high conf) |
| **AMBIENT_STATE** | System state, time, config - read local state | LOCAL_CAPABILITY |
| **EXTERNAL_FACT_UNCERTAIN** | Time-sensitive facts, regulations - need internet | REQUIRE_COMM |
| **OPINION** | Subjective recommendations - answer with disclaimer | SUGGEST_COMM |

---

## Keyword Quick Lookup

### Time-Sensitive Keywords
```
latest, today, current, now, recently, 2025, 2026, recent, this year
新, 最新, 现在, 当前, 今天, 最近
```

### Authoritative Keywords
```
policy, regulation, law, official, standard, government, announcement, compliance
政策, 法规, 官方, 公告, 规定, 标准
```

### Ambient State Keywords
```
time, phase, session, mode, config, status, running, active
什么时候, 几点, 当前, 状态, 运行, 配置
```

### Code Structure Patterns
```
class\s+\w+, function\s+\w+, method\s+\w+, \.py, \.js, API, exists, where is, find.*file
```

### Opinion Indicators
```
recommend, suggest, should, better, prefer, opinion, think, believe
推荐, 建议, 应该, 最好, 认为, 觉得
```

---

## Decision Matrix (Simple)

```
Type + Confidence            → Action
─────────────────────────────────────────────────────
LOCAL_DETERMINISTIC + ANY    → LOCAL_CAPABILITY
LOCAL_KNOWLEDGE + HIGH        → DIRECT_ANSWER
LOCAL_KNOWLEDGE + MED/LOW     → SUGGEST_COMM
AMBIENT_STATE + ANY           → LOCAL_CAPABILITY
EXTERNAL_FACT_UNCERTAIN + ANY → REQUIRE_COMM
OPINION + HIGH                → DIRECT_ANSWER
OPINION + MED/LOW             → SUGGEST_COMM / REQUIRE_COMM
```

---

## Quick Start

### Basic Usage

```python
import asyncio
from agentos.core.chat.info_need_classifier import InfoNeedClassifier

async def classify():
    classifier = InfoNeedClassifier()
    result = await classifier.classify("What is the latest AI policy?")

    print(f"Type: {result.info_need_type.value}")
    print(f"Action: {result.decision_action.value}")
    print(f"Reasoning: {result.reasoning}")

asyncio.run(classify())
```

### Disable LLM (Fast Mode)

```python
classifier = InfoNeedClassifier(config={
    "enable_llm_evaluation": False  # Rule-based only, < 10ms
})
```

### Route Based on Action

```python
from agentos.core.chat.models.info_need import DecisionAction

result = await classifier.classify(message)

if result.decision_action == DecisionAction.LOCAL_CAPABILITY:
    # Use file system, grep, status checks
    pass
elif result.decision_action == DecisionAction.DIRECT_ANSWER:
    # Generate LLM response
    pass
elif result.decision_action == DecisionAction.REQUIRE_COMM:
    # Suggest /comm command
    pass
elif result.decision_action == DecisionAction.SUGGEST_COMM:
    # Answer + disclaimer
    pass
```

---

## Common Commands

### Run Demo

```bash
# Full demo with all examples
python3 examples/info_need_classifier_demo.py

# Interactive mode
python3 examples/info_need_classifier_demo.py interactive

# Single classification
python3 examples/info_need_classifier_demo.py classify "Your question here"

# Batch classification
python3 examples/info_need_classifier_demo.py batch questions.txt
```

### Debug Classification

```python
import logging
logging.basicConfig(level=logging.DEBUG)

classifier = InfoNeedClassifier()
result = await classifier.classify(message)

# Inspect
print(f"Signal strength: {result.rule_signals.signal_strength}")
print(f"Matched keywords: {result.rule_signals.matched_keywords}")
if result.llm_confidence:
    print(f"LLM reason: {result.llm_confidence.reason}")
```

### Export to JSON

```python
result = await classifier.classify(message)
json_data = result.to_dict()

import json
print(json.dumps(json_data, indent=2, default=str))
```

---

## Signal Strength Thresholds

| Strength | Meaning | LLM Called? |
|----------|---------|-------------|
| 0.8 - 1.0 | Very strong signal | No (skip LLM) |
| 0.5 - 0.7 | Medium signal | Maybe (if type = LOCAL_KNOWLEDGE/OPINION) |
| 0.0 - 0.4 | Weak signal | Yes (needs LLM) |

**Signal Calculation**:
- Ambient state keywords: +0.4
- Code structure patterns: +0.3
- Time-sensitive keywords: +0.2
- Authoritative keywords: +0.2
- Opinion indicators: +0.1
- Multiple matches (3+): +0.1
- Multiple matches (5+): +0.2

---

## Troubleshooting Checklist

### Classification seems wrong?

1. **Check matched keywords**:
   ```python
   print(result.rule_signals.matched_keywords)
   ```

2. **Check signal strength**:
   ```python
   print(result.rule_signals.signal_strength)
   ```

3. **Check LLM assessment** (if available):
   ```python
   if result.llm_confidence:
       print(result.llm_confidence.reason)
   ```

4. **Check reasoning**:
   ```python
   print(result.reasoning)
   ```

### LLM not being called?

LLM is skipped for:
- LOCAL_DETERMINISTIC (always)
- AMBIENT_STATE (always)
- EXTERNAL_FACT_UNCERTAIN with strong signals (>= 0.7)
- When `enable_llm_evaluation = False`

### Performance too slow?

1. **Disable LLM evaluation**:
   ```python
   config = {"enable_llm_evaluation": False}
   ```

2. **Increase LLM threshold** (call LLM less often):
   ```python
   config = {"llm_threshold": 0.3}  # Default: 0.5
   ```

3. **Reuse classifier instance** (don't recreate):
   ```python
   classifier = InfoNeedClassifier()  # Create once
   # Reuse for all classifications
   ```

4. **Cache results**:
   ```python
   cache = {}

   async def classify_cached(msg):
       if msg not in cache:
           cache[msg] = await classifier.classify(msg)
       return cache[msg]
   ```

### Classification always returns same type?

Check for:
- Hardcoded test/mock LLM callable
- Configuration overrides
- Custom decision matrix

Reset to default:
```python
classifier = InfoNeedClassifier()  # No config, no custom callable
```

---

## Example Classifications

### LOCAL_DETERMINISTIC

```
✅ "Does the ChatEngine class exist?"
✅ "Show me all Python files"
✅ "Count test files"
❌ "What is a class?" (LOCAL_KNOWLEDGE)
```

### LOCAL_KNOWLEDGE

```
✅ "What is REST API?"
✅ "Explain SOLID principles"
❌ "What is the latest Python version?" (EXTERNAL_FACT)
```

### AMBIENT_STATE

```
✅ "What time is it?"
✅ "What phase am I in?"
✅ "Show system status"
❌ "What is a phase?" (LOCAL_KNOWLEDGE)
```

### EXTERNAL_FACT_UNCERTAIN

```
✅ "What is the latest AI policy?"
✅ "Today's AI news?"
✅ "Current GDPR updates?"
❌ "What is GDPR?" (LOCAL_KNOWLEDGE)
```

### OPINION

```
✅ "Best way to learn Python?"
✅ "Should I use REST or GraphQL?"
✅ "Recommend a database?"
❌ "What is the recommended HTTP port?" (LOCAL_KNOWLEDGE, standard = 80)
```

---

## Integration Patterns

### Pattern 1: ChatEngine (Automatic)

```python
from agentos.core.chat.engine import ChatEngine

engine = ChatEngine()  # InfoNeedClassifier is auto-integrated
response = engine.send_message(session_id, user_input)
# Classification happens automatically
```

### Pattern 2: Custom Chat System

```python
classifier = InfoNeedClassifier()

async def handle_message(msg: str):
    result = await classifier.classify(msg)

    if result.decision_action == DecisionAction.LOCAL_CAPABILITY:
        return handle_with_tools(msg)
    elif result.decision_action == DecisionAction.REQUIRE_COMM:
        return suggest_comm_command(msg)
    else:
        return generate_llm_response(msg)
```

### Pattern 3: Pre-filter for Expensive Operations

```python
# Only use expensive operations (LLM, search) when needed
result = await classifier.classify(msg)

if result.decision_action == DecisionAction.LOCAL_CAPABILITY:
    # Fast path: use grep, file system
    return local_tool_response(msg)
else:
    # Expensive path: LLM generation
    return llm_response(msg)
```

---

## Key Constraints

1. **Judgment-only**: Does NOT execute searches, fetch data, or generate answers
2. **Fast path**: Rule-based classification < 10ms for clear cases
3. **Conservative**: When in doubt, suggests/requires communication
4. **LLM for stability**: LLM evaluates "Will answer be wrong in 24h?", not "Do I know this?"
5. **Explicit uncertainty**: Makes unknown unknowns visible and actionable

---

## Quick Links

- Full Guide: [INFO_NEED_CLASSIFICATION_GUIDE.md](./INFO_NEED_CLASSIFICATION_GUIDE.md)
- Interactive Demo: [info_need_classifier_demo.py](../../examples/info_need_classifier_demo.py)
- Implementation: [info_need_classifier.py](../../agentos/core/chat/info_need_classifier.py)
- Data Models: [models/info_need.py](../../agentos/core/chat/models/info_need.py)

---

## Cheat Sheet: Decision Flow

```
Message → RuleFilter → PreliminaryType → NeedLLM?
                                         ├─ NO  → FinalType
                                         └─ YES → LLMEval → FinalType
                                                              ↓
                                                        DecisionMatrix
                                                              ↓
                                                        DecisionAction
                                                         ├─ LOCAL_CAPABILITY
                                                         ├─ DIRECT_ANSWER
                                                         ├─ REQUIRE_COMM
                                                         └─ SUGGEST_COMM
```

---

**Last Updated**: 2026-01-31
**Version**: 1.0.0
