# InfoNeedClassifier Complete Usage Guide

## Table of Contents
- [Design Philosophy](#design-philosophy)
- [Five Information Need Types](#five-information-need-types)
- [Usage Examples](#usage-examples)
- [Integration Flow](#integration-flow)
- [FAQ](#faq)
- [Extension Guide](#extension-guide)
- [Best Practices](#best-practices)

---

## Design Philosophy

### Why Not Ask "Do You Know?"

Traditional AI chat systems ask the LLM "Do you know this?" or "Are you confident in answering this?" This approach has critical flaws:

1. **LLMs cannot self-assess knowledge accuracy** - They can only assess pattern familiarity, not factual correctness
2. **Hallucination risk** - LLMs confidently provide outdated or incorrect information
3. **No external verification** - Without internet access, LLMs cannot verify time-sensitive facts
4. **Binary thinking** - "Yes/No" doesn't capture the nuance of information needs

### Why Classify Question Types

Instead of asking the LLM about its knowledge, we classify the **type of information need**:

- **Local Deterministic**: Questions about code structure, file existence - answerable via local tools
- **Local Knowledge**: Questions about stable concepts - answerable from training data
- **Ambient State**: Questions about system state (time, phase, config) - requires runtime info
- **External Fact (Uncertain)**: Time-sensitive or authoritative facts - requires internet
- **Opinion**: Subjective questions - benefit from multiple perspectives

This approach:
- Separates **what we can know** from **what we claim to know**
- Routes questions to appropriate handlers (local tools, LLM, communication)
- Makes uncertainty explicit and actionable

### How to Judge Internet Need

The classifier evaluates:

1. **Time sensitivity**: Does this information change frequently? (keywords: "latest", "today", "2025")
2. **Authoritative requirement**: Does this need official sources? (keywords: "policy", "regulation", "official")
3. **Local determinism**: Can local tools answer this? (code structure, file paths, grep)
4. **Ambient state**: Is this about runtime state? (time, phase, session ID)

Decision Matrix:
```
Question Type         + Confidence → Action
LOCAL_DETERMINISTIC   + ANY        → Use local tools (grep, file system)
LOCAL_KNOWLEDGE       + HIGH       → Answer directly from LLM
LOCAL_KNOWLEDGE       + LOW/MED    → Suggest verification via /comm
AMBIENT_STATE         + ANY        → Use local capabilities (time, config)
EXTERNAL_FACT         + ANY        → Require /comm search
OPINION               + HIGH       → Answer with disclaimer
OPINION               + LOW        → Suggest external perspectives
```

### From Tool System to Judgment System

**Before InfoNeedClassifier**:
- LLM decides whether to use tools
- Risk: LLM may claim to know when it doesn't
- No structured decision making

**After InfoNeedClassifier**:
- **Judgment-only module** - does NOT execute actions
- Rule-based fast path (< 10ms) for clear cases
- LLM self-assessment ONLY for stability evaluation ("Will my answer be wrong in 24h?")
- Explicit decision matrix for routing
- User-controlled external information access

**Key constraint**: InfoNeedClassifier is **judgment-only**. It:
- Does NOT perform searches
- Does NOT fetch external data
- Does NOT generate answers
- ONLY classifies and recommends actions

---

## Five Information Need Types

### 1. LOCAL_DETERMINISTIC

**Definition**: Questions about code structure, file existence, or deterministic operations that can be answered by examining local files or project state.

**Characteristics**:
- Answer is deterministic (not probabilistic)
- Does not require LLM reasoning
- Answerable via file system operations, grep, code analysis
- Answer does not change over time (for a given codebase state)

**Judgment Criteria**:
- Contains code structure keywords: `class`, `function`, `method`, `API`
- Contains file path patterns: `.py`, `.js`, `.json`
- Contains existence queries: `exists`, `where is`, `find file`
- Contains deterministic operations: `count`, `list`, `show`

**Processing**:
- Action: `LOCAL_CAPABILITY`
- Route to: File system tools, grep, code analysis tools
- Skip LLM entirely (fast path)

**Examples**:

1. ✅ "Does the `InfoNeedClassifier` class exist in this project?"
   - Detection: `class` + `exists` keywords
   - Action: Use grep/file search to locate class

2. ✅ "Show me all Python files in the `agentos/core/chat` directory"
   - Detection: `.py` + `show` + file path
   - Action: Use `ls` or `find` command

3. ✅ "What methods does the `ChatEngine` class have?"
   - Detection: `methods` + `class` keywords
   - Action: Parse class definition from file

4. ✅ "Count how many test files exist"
   - Detection: `count` + `test files` + `exists`
   - Action: File system count operation

5. ✅ "Where is the configuration file located?"
   - Detection: `where is` + `file` keywords
   - Action: File search operation

**Common Misclassifications**:
- ❌ "What is a class?" (LOCAL_KNOWLEDGE, not deterministic query)
- ❌ "Should I create a new class?" (OPINION, not deterministic)
- ❌ "Is this class well-designed?" (OPINION, requires subjective judgment)

---

### 2. LOCAL_KNOWLEDGE

**Definition**: Questions about established concepts, best practices, documentation, or stable domain knowledge that LLMs are trained on.

**Characteristics**:
- Based on training data cutoff
- Stable over time (not rapidly changing)
- General domain knowledge
- Does not require authoritative sources
- Confidence level matters

**Judgment Criteria**:
- Asks about concepts: `what is`, `explain`, `how to`
- Asks about best practices: `best practice`, `recommended approach`
- Asks about comparison: `difference between`, `vs`
- No time-sensitive keywords
- No authoritative source requirements

**Processing**:
- Action: `DIRECT_ANSWER` (if high confidence) or `SUGGEST_COMM` (if low/medium)
- LLM self-assessment: Check if answer would be stable over 24 hours
- Route to: LLM generation with context

**Examples**:

1. ✅ "What is REST API?"
   - Detection: `what is` + general concept
   - LLM assessment: High confidence (stable concept)
   - Action: Direct answer

2. ✅ "Explain the SOLID principles"
   - Detection: `explain` + established concept
   - LLM assessment: High confidence (stable principles)
   - Action: Direct answer

3. ✅ "What's the difference between AI and ML?"
   - Detection: `difference between` + general concepts
   - LLM assessment: High confidence
   - Action: Direct answer

4. ✅ "How do I use async/await in Python?"
   - Detection: `how do I` + programming concept
   - LLM assessment: Medium confidence (syntax may vary by version)
   - Action: Direct answer with version caveat

5. ✅ "What are microservices?"
   - Detection: `what are` + architecture concept
   - LLM assessment: High confidence (stable concept)
   - Action: Direct answer

**Common Misclassifications**:
- ❌ "What is the latest Python version?" (EXTERNAL_FACT, time-sensitive)
- ❌ "What is the current AI regulation?" (EXTERNAL_FACT, time-sensitive + authoritative)
- ❌ "What time is it?" (AMBIENT_STATE, not knowledge-based)

**Confidence Variations**:
- High → Answer directly
- Medium → Answer with "Note: This may have changed since my training"
- Low → Suggest using /comm for verification

---

### 3. AMBIENT_STATE

**Definition**: Questions about the current runtime state, system configuration, or environment that require reading local system state (not external resources).

**Characteristics**:
- Requires real-time information
- Answerable from local system state
- Changes frequently
- Does not require LLM reasoning
- Fast lookup operations

**Judgment Criteria**:
- Time queries: `time`, `when`, `几点`
- State queries: `phase`, `mode`, `status`, `running`, `active`
- Session queries: `session`, `session ID`, `current session`
- Config queries: `config`, `settings`, `configuration`

**Processing**:
- Action: `LOCAL_CAPABILITY`
- Route to: Local state readers (datetime, session manager, config reader)
- Skip LLM (fast path)

**Examples**:

1. ✅ "What time is it?"
   - Detection: `time` keyword
   - Action: Read system time
   - Response: "Current time: 2026-01-31 14:23:45"

2. ✅ "What phase am I in?"
   - Detection: `phase` keyword
   - Action: Read session metadata
   - Response: "Current execution phase: planning"

3. ✅ "What is my session ID?"
   - Detection: `session ID` keywords
   - Action: Read from context
   - Response: "Current session ID: abc123..."

4. ✅ "What mode are we in?"
   - Detection: `mode` keyword
   - Action: Read conversation_mode from session
   - Response: "Current conversation mode: chat"

5. ✅ "Show me the system status"
   - Detection: `status` keyword
   - Action: Aggregate state information
   - Response: Multi-line status report

**Common Misclassifications**:
- ❌ "What is a phase?" (LOCAL_KNOWLEDGE, not state query)
- ❌ "What will the time be in 2 hours?" (Calculation, not direct state)
- ❌ "What is the weather?" (EXTERNAL_FACT, not local state)

**Fast Path Optimization**:
- Ambient state queries bypass LLM completely
- Direct lookup from state managers
- Response time < 50ms

---

### 4. EXTERNAL_FACT_UNCERTAIN

**Definition**: Questions about facts that are time-sensitive, require authoritative sources, or may have changed since the LLM's training cutoff.

**Characteristics**:
- Time-sensitive information
- Requires verification from authoritative sources
- May have changed recently
- Risk of outdated information from LLM
- Requires internet access for accuracy

**Judgment Criteria**:
- Time-sensitive keywords: `latest`, `today`, `current`, `2025`, `2026`, `recent`, `最新`
- Authoritative keywords: `policy`, `regulation`, `official`, `law`, `compliance`, `政策`, `法规`
- Combination of both (highest signal strength)
- LLM self-assessment: "low" confidence due to time-sensitivity

**Processing**:
- Action: `REQUIRE_COMM`
- Route to: User notification + /comm command suggestion
- Block if execution_phase = "planning"
- Never answer directly without disclaimer

**Examples**:

1. ✅ "What is the latest Python version?"
   - Detection: `latest` + version query
   - Signal strength: 0.8 (time-sensitive)
   - Action: Require /comm search
   - Suggested: `/comm search latest Python version`

2. ✅ "What are Australia's current AI regulations?"
   - Detection: `current` + `regulations` (time + authoritative)
   - Signal strength: 0.9 (both keywords)
   - Action: Require /comm search
   - Suggested: `/comm search Australia AI regulations 2026`

3. ✅ "What happened in AI news today?"
   - Detection: `today` + `news` (time-sensitive)
   - Signal strength: 0.85
   - Action: Require /comm search
   - Suggested: `/comm search AI news today`

4. ✅ "What is the official stance of the US government on AI safety?"
   - Detection: `official` + `government` (authoritative)
   - Signal strength: 0.7
   - Action: Require /comm search
   - Suggested: `/comm search US government AI safety official policy`

5. ✅ "What are the 2026 updates to GDPR?"
   - Detection: `2026` + `updates` (time-sensitive)
   - Signal strength: 0.8
   - Action: Require /comm search
   - Suggested: `/comm search GDPR 2026 updates`

**Common Misclassifications**:
- ❌ "What is GDPR?" (LOCAL_KNOWLEDGE if asking about general concept)
- ✅ "What is the latest GDPR update?" (EXTERNAL_FACT, time-sensitive)
- ❌ "What is a regulation?" (LOCAL_KNOWLEDGE, concept definition)

**Phase-Based Blocking**:
```python
if execution_phase == "planning":
    # Block external info in planning phase
    response = "⚠️ External info required but currently in planning phase"
else:
    # Suggest /comm command
    response = "🔍 External information required\n\n" \
               "Suggested action: /comm search <query>"
```

---

### 5. OPINION

**Definition**: Questions requesting subjective judgments, recommendations, or value assessments that depend on context, preferences, or multiple perspectives.

**Characteristics**:
- Subjective, not objective facts
- Multiple valid answers exist
- Context-dependent
- May benefit from external perspectives
- LLM can provide initial answer but should acknowledge uncertainty

**Judgment Criteria**:
- Opinion indicators: `recommend`, `suggest`, `should`, `better`, `prefer`, `推荐`, `建议`
- Evaluation requests: `good`, `bad`, `pros and cons`
- Open-ended: `how would you`, `what do you think`
- Comparison: `which is better`, `best approach`

**Processing**:
- Action: `DIRECT_ANSWER` (high confidence) or `SUGGEST_COMM` (medium) or `REQUIRE_COMM` (low)
- LLM provides answer with disclaimer
- Suggest external perspectives for validation

**Examples**:

1. ✅ "What's the best way to learn Python?"
   - Detection: `best way` (opinion indicator)
   - LLM assessment: Medium confidence (context-dependent)
   - Action: Direct answer + suggest external perspectives
   - Disclaimer: "This is a subjective recommendation..."

2. ✅ "Should I use REST or GraphQL?"
   - Detection: `should I` + comparison
   - LLM assessment: Medium confidence
   - Action: Direct answer with trade-offs + suggest research
   - Disclaimer: "The choice depends on your use case..."

3. ✅ "Is this architecture design good?"
   - Detection: `good` + evaluation request
   - LLM assessment: Low confidence (needs context)
   - Action: Suggest providing more context or using /comm for expert opinions

4. ✅ "What do you recommend for database choice?"
   - Detection: `recommend` + open-ended
   - LLM assessment: Medium confidence
   - Action: Direct answer with options + suggest research
   - Disclaimer: "Recommendations vary by requirements..."

5. ✅ "What's your opinion on microservices?"
   - Detection: `opinion` + subjective topic
   - LLM assessment: Medium confidence
   - Action: Direct answer with balanced perspective
   - Disclaimer: "Opinions vary in the industry..."

**Common Misclassifications**:
- ❌ "What is the recommended port for HTTP?" (LOCAL_KNOWLEDGE, standard = 80, objective fact)
- ✅ "Should I use HTTP or HTTPS?" (OPINION, depends on security requirements)
- ❌ "What is the best sorting algorithm?" (Depends - if asking about time complexity it's LOCAL_KNOWLEDGE, if asking for project recommendation it's OPINION)

**Confidence-Based Routing**:
- High confidence → Answer directly with disclaimer
- Medium confidence → Answer + suggest verification
- Low confidence → Suggest gathering external input first

---

## Usage Examples

### Example 1: Basic Usage

```python
import asyncio
from agentos.core.chat.info_need_classifier import InfoNeedClassifier

async def basic_classification():
    # Create classifier instance
    classifier = InfoNeedClassifier()

    # Classify a message
    result = await classifier.classify("What is the latest AI policy?")

    # Inspect result
    print(f"Type: {result.info_need_type.value}")
    print(f"Action: {result.decision_action.value}")
    print(f"Confidence: {result.confidence_level.value}")
    print(f"Reasoning: {result.reasoning}")

    # Example output:
    # Type: external_fact_uncertain
    # Action: require_comm
    # Confidence: low
    # Reasoning: Classified as external_fact_uncertain. Rule-based signals...

# Run
asyncio.run(basic_classification())
```

### Example 2: ChatEngine Integration

```python
from agentos.core.chat.engine import ChatEngine

async def chat_with_classification():
    # ChatEngine automatically uses InfoNeedClassifier
    engine = ChatEngine()

    # Create session
    session_id = engine.create_session(
        title="Test Session",
        metadata={"execution_phase": "planning"}
    )

    # Send message - classifier runs automatically
    response = engine.send_message(
        session_id=session_id,
        user_input="What time is it?"
    )

    # Classification happened behind the scenes
    # Response routed based on DecisionAction
    print(response["content"])

asyncio.run(chat_with_classification())
```

### Example 3: Custom Configuration

```python
from agentos.core.chat.info_need_classifier import InfoNeedClassifier

async def custom_config():
    # Disable LLM self-assessment (rule-based only)
    classifier = InfoNeedClassifier(config={
        "enable_llm_evaluation": False,  # Faster, rule-based only
        "llm_threshold": 0.5  # When to invoke LLM (if enabled)
    })

    result = await classifier.classify("What is Python?")

    # LLM evaluation was skipped
    assert result.llm_confidence is None
    print(f"Classified without LLM: {result.info_need_type.value}")

asyncio.run(custom_config())
```

### Example 4: Batch Classification

```python
from agentos.core.chat.info_need_classifier import InfoNeedClassifier
import asyncio

async def batch_classify():
    classifier = InfoNeedClassifier()

    messages = [
        "Help me summarize this document",      # LOCAL_DETERMINISTIC
        "What is REST API?",                    # LOCAL_KNOWLEDGE
        "What time is it?",                     # AMBIENT_STATE
        "What's the latest Python version?",    # EXTERNAL_FACT_UNCERTAIN
        "Should I use Flask or Django?",        # OPINION
    ]

    # Classify all messages
    for msg in messages:
        result = await classifier.classify(msg)
        print(f"{msg[:40]:40} -> {result.info_need_type.value:25} ({result.decision_action.value})")

    # Output:
    # Help me summarize this document        -> local_deterministic         (local_capability)
    # What is REST API?                      -> local_knowledge             (direct_answer)
    # What time is it?                       -> ambient_state               (local_capability)
    # What's the latest Python version?      -> external_fact_uncertain     (require_comm)
    # Should I use Flask or Django?          -> opinion                     (suggest_comm)

asyncio.run(batch_classify())
```

### Example 5: Testing with Mock LLM

```python
from agentos.core.chat.info_need_classifier import InfoNeedClassifier
import json
import asyncio

async def mock_llm_callable(prompt: str) -> str:
    """Mock LLM for testing"""
    if "latest" in prompt.lower():
        return json.dumps({
            "confidence": "low",
            "reason": "time-sensitive"
        })
    else:
        return json.dumps({
            "confidence": "high",
            "reason": "stable"
        })

async def test_with_mock():
    classifier = InfoNeedClassifier(
        llm_callable=mock_llm_callable
    )

    result = await classifier.classify("What is the latest AI news?")

    # Mock LLM returned low confidence
    assert result.confidence_level.value == "low"
    assert result.decision_action.value == "require_comm"
    print("Test passed!")

asyncio.run(test_with_mock())
```

### Example 6: Handling Classification Results

```python
from agentos.core.chat.info_need_classifier import InfoNeedClassifier
from agentos.core.chat.models.info_need import DecisionAction
import asyncio

async def handle_classification():
    classifier = InfoNeedClassifier()
    message = "What's the latest Python version?"

    result = await classifier.classify(message)

    # Route based on decision action
    if result.decision_action == DecisionAction.LOCAL_CAPABILITY:
        print("Using local tools...")
        # Execute local file operations, status checks, etc.

    elif result.decision_action == DecisionAction.DIRECT_ANSWER:
        print("Answering from LLM knowledge...")
        # Generate response from LLM

    elif result.decision_action == DecisionAction.REQUIRE_COMM:
        print("External information required!")
        # Notify user and suggest /comm command
        suggested_cmd = f"/comm search {message}"
        print(f"Suggested: {suggested_cmd}")

    elif result.decision_action == DecisionAction.SUGGEST_COMM:
        print("Answering but suggesting verification...")
        # Provide answer + disclaimer

    # Log classification for audit
    print(f"\nClassification audit:")
    print(f"  Type: {result.info_need_type.value}")
    print(f"  Confidence: {result.confidence_level.value}")
    print(f"  Reasoning: {result.reasoning}")

asyncio.run(handle_classification())
```

### Example 7: Serialization and Export

```python
from agentos.core.chat.info_need_classifier import InfoNeedClassifier
import json
import asyncio

async def serialize_result():
    classifier = InfoNeedClassifier()

    result = await classifier.classify("What is the latest AI regulation?")

    # Serialize to dict
    result_dict = result.to_dict()

    # Export to JSON
    json_str = json.dumps(result_dict, indent=2, default=str)
    print(json_str)

    # Save to file
    with open("classification_log.json", "a") as f:
        f.write(json_str + "\n")

    print("\nClassification logged to file")

asyncio.run(serialize_result())
```

---

## Integration Flow

### Classification Pipeline in ChatEngine

```
┌─────────────────────────────────────────────────────────────┐
│                       User Message                          │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            v
┌─────────────────────────────────────────────────────────────┐
│            Is it a slash command? (/help, /comm)            │
│                 YES → Execute command handler               │
└───────────────────────────┬─────────────────────────────────┘
                            │ NO
                            v
┌─────────────────────────────────────────────────────────────┐
│               InfoNeedClassifier.classify()                 │
│                                                             │
│  Step 1: Rule-based filtering (< 10ms)                     │
│  ├─ Check keywords (time-sensitive, authoritative, etc.)   │
│  ├─ Check patterns (code structure, opinion indicators)    │
│  └─ Calculate signal strength (0.0 - 1.0)                  │
│                                                             │
│  Step 2: Preliminary type determination                    │
│  └─ AMBIENT_STATE | LOCAL_DETERMINISTIC | LOCAL_KNOWLEDGE  │
│     | EXTERNAL_FACT_UNCERTAIN | OPINION                    │
│                                                             │
│  Step 3: LLM self-assessment (if needed)                   │
│  ├─ Skip if: LOCAL_DETERMINISTIC, AMBIENT_STATE            │
│  ├─ Skip if: Strong rule signals (>= 0.7)                  │
│  └─ Ask: "Will answer be wrong in 24h?"                    │
│     └─ Response: {confidence: "high|medium|low"}           │
│                                                             │
│  Step 4: Finalize type + confidence                        │
│  └─ Combine rule signals + LLM assessment                  │
│                                                             │
│  Step 5: Decision matrix lookup                            │
│  └─ (type, confidence) → DecisionAction                    │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            v
            ┌───────────────┴───────────────┐
            │      DecisionAction           │
            └───────────┬───────────────────┘
                        │
        ┌───────────────┼───────────────┬────────────────┐
        │               │               │                │
        v               v               v                v
┌───────────────┐ ┌──────────────┐ ┌─────────────┐ ┌─────────────┐
│LOCAL_         │ │DIRECT_       │ │REQUIRE_     │ │SUGGEST_     │
│CAPABILITY     │ │ANSWER        │ │COMM         │ │COMM         │
└───────┬───────┘ └──────┬───────┘ └──────┬──────┘ └──────┬──────┘
        │                │                │               │
        v                v                v               v
┌───────────────┐ ┌──────────────┐ ┌─────────────┐ ┌─────────────┐
│ Handle Ambient│ │ Build Context│ │ Notify User │ │Build Context│
│ State         │ │ + Invoke LLM │ │ + Suggest   │ │+ Invoke LLM │
│               │ │              │ │ /comm       │ │+ Add        │
│- Read time    │ │- RAG enabled │ │             │ │  Disclaimer │
│- Read phase   │ │- Memory      │ │ Check phase:│ │             │
│- Read config  │ │  enabled     │ │ - Planning→ │ │"Note: May be│
│- Read status  │ │              │ │   Block     │ │ outdated"   │
│               │ │- Temperature │ │ - Execution→│ │             │
│Return direct  │ │  0.7         │ │   Suggest   │ │Return answer│
│answer         │ │              │ │             │ │+ disclaimer │
└───────────────┘ └──────────────┘ └─────────────┘ └─────────────┘
        │                │                │               │
        └────────────────┴────────────────┴───────────────┘
                         │
                         v
              ┌──────────────────┐
              │ Save Message to  │
              │ ChatService with │
              │ Classification   │
              │ Metadata         │
              └──────────────────┘
                         │
                         v
              ┌──────────────────┐
              │ Return Response  │
              │ to User          │
              └──────────────────┘
```

### Decision Matrix

```
┌─────────────────────────┬──────────┬──────────┬──────────┐
│   InfoNeedType          │   HIGH   │  MEDIUM  │   LOW    │
├─────────────────────────┼──────────┼──────────┼──────────┤
│ LOCAL_DETERMINISTIC     │ LOCAL_   │ LOCAL_   │ LOCAL_   │
│                         │ CAPABIL  │ CAPABIL  │ CAPABIL  │
├─────────────────────────┼──────────┼──────────┼──────────┤
│ LOCAL_KNOWLEDGE         │ DIRECT_  │ DIRECT_  │ SUGGEST_ │
│                         │ ANSWER   │ ANSWER   │ COMM     │
├─────────────────────────┼──────────┼──────────┼──────────┤
│ AMBIENT_STATE           │ LOCAL_   │ LOCAL_   │ LOCAL_   │
│                         │ CAPABIL  │ CAPABIL  │ CAPABIL  │
├─────────────────────────┼──────────┼──────────┼──────────┤
│ EXTERNAL_FACT_UNCERTAIN │ REQUIRE_ │ REQUIRE_ │ REQUIRE_ │
│                         │ COMM     │ COMM     │ COMM     │
├─────────────────────────┼──────────┼──────────┼──────────┤
│ OPINION                 │ DIRECT_  │ SUGGEST_ │ REQUIRE_ │
│                         │ ANSWER   │ COMM     │ COMM     │
└─────────────────────────┴──────────┴──────────┴──────────┘
```

---

## FAQ

### Q1: When does the classifier call the LLM?

**A**: The LLM is called ONLY when:
1. Question type is `LOCAL_KNOWLEDGE` or `OPINION` (confidence matters)
2. Rule signals are weak (signal_strength < 0.5)
3. NOT called for `LOCAL_DETERMINISTIC` or `AMBIENT_STATE` (fast path)
4. NOT called for `EXTERNAL_FACT_UNCERTAIN` with strong signals (>= 0.7)
5. `enable_llm_evaluation` config is True (default)

The LLM is used for **stability assessment**, not answer generation.

---

### Q2: How can I disable LLM self-assessment?

**A**: Pass configuration when creating the classifier:

```python
classifier = InfoNeedClassifier(config={
    "enable_llm_evaluation": False  # Pure rule-based classification
})
```

This makes classification faster but may be less accurate for edge cases.

---

### Q3: How do I add new keywords?

**A**: Edit the keyword lists in `RuleBasedFilter` class:

```python
# In agentos/core/chat/info_need_classifier.py

class RuleBasedFilter:
    TIME_SENSITIVE_KEYWORDS = [
        "today", "latest", "current", "now", "recently",
        # Add your keywords here:
        "newest", "up-to-date", "breaking"
    ]
```

Alternatively, extend the class:

```python
from agentos.core.chat.info_need_classifier import RuleBasedFilter

class CustomFilter(RuleBasedFilter):
    TIME_SENSITIVE_KEYWORDS = RuleBasedFilter.TIME_SENSITIVE_KEYWORDS + [
        "newest", "up-to-date", "breaking"
    ]
```

---

### Q4: What happens if classification is wrong?

**A**: Classification errors are handled gracefully:

1. **Over-conservative** (false positive for REQUIRE_COMM):
   - User gets notification + /comm suggestion
   - Can still answer: "Ignore and answer based on your knowledge"

2. **Under-conservative** (false negative, should have required comm):
   - System still adds disclaimer for LOW/MEDIUM confidence
   - Audit log captures the classification decision

3. **Debugging**:
   - Check `result.reasoning` for explanation
   - Check `result.rule_signals.matched_keywords` for triggered keywords
   - Check `result.llm_confidence` for LLM assessment

---

### Q5: How can I optimize performance?

**A**:

1. **Disable LLM for fast classification**:
   ```python
   config = {"enable_llm_evaluation": False}
   ```

2. **Adjust LLM threshold** (only call LLM for very weak signals):
   ```python
   config = {"llm_threshold": 0.3}  # Default: 0.5
   ```

3. **Use singleton classifier** (reuse instance):
   ```python
   # Create once
   classifier = InfoNeedClassifier()

   # Reuse for all classifications
   for msg in messages:
       result = await classifier.classify(msg)
   ```

4. **Cache results** for repeated messages:
   ```python
   classification_cache = {}

   async def classify_with_cache(message: str):
       if message not in classification_cache:
           result = await classifier.classify(message)
           classification_cache[message] = result
       return classification_cache[message]
   ```

---

### Q6: How do I debug classification results?

**A**:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

classifier = InfoNeedClassifier()
result = await classifier.classify("What is the latest AI news?")

# Inspect classification details
print("=" * 60)
print(f"Message: {message}")
print(f"Type: {result.info_need_type.value}")
print(f"Action: {result.decision_action.value}")
print(f"Confidence: {result.confidence_level.value}")
print()
print("Rule Signals:")
print(f"  Signal strength: {result.rule_signals.signal_strength}")
print(f"  Matched keywords: {result.rule_signals.matched_keywords}")
print(f"  Time-sensitive: {result.rule_signals.has_time_sensitive_keywords}")
print(f"  Authoritative: {result.rule_signals.has_authoritative_keywords}")
print()
if result.llm_confidence:
    print("LLM Assessment:")
    print(f"  Confidence: {result.llm_confidence.confidence.value}")
    print(f"  Reason: {result.llm_confidence.reason}")
    print(f"  Reasoning: {result.llm_confidence.reasoning}")
print()
print("Reasoning:")
print(f"  {result.reasoning}")
print("=" * 60)
```

---

### Q7: How do I customize the decision matrix?

**A**: Override the `DecisionMatrix` class:

```python
from agentos.core.chat.info_need_classifier import DecisionMatrix
from agentos.core.chat.models.info_need import InfoNeedType, ConfidenceLevel, DecisionAction

class CustomDecisionMatrix(DecisionMatrix):
    MATRIX = {
        # Custom mappings
        (InfoNeedType.LOCAL_KNOWLEDGE, ConfidenceLevel.LOW): DecisionAction.REQUIRE_COMM,
        # ... other mappings
    }

# Use custom matrix
from agentos.core.chat.info_need_classifier import InfoNeedClassifier

classifier = InfoNeedClassifier()
classifier.decision_matrix = CustomDecisionMatrix()
```

---

### Q8: Does the classifier support languages other than English?

**A**: Yes! The classifier includes Chinese keywords and can be extended:

**Built-in Chinese support**:
```python
TIME_SENSITIVE_KEYWORDS = [
    "today", "latest", "current",
    "新", "最新", "现在", "当前", "今天"  # Chinese
]
```

**Add more languages**:
```python
class MultilingualFilter(RuleBasedFilter):
    TIME_SENSITIVE_KEYWORDS = RuleBasedFilter.TIME_SENSITIVE_KEYWORDS + [
        # Spanish
        "último", "reciente", "actual",
        # French
        "dernier", "récent", "actuel",
        # Japanese
        "最新", "最近", "現在"
    ]
```

---

### Q9: How do I handle mixed-type questions?

**A**: The classifier prioritizes based on signal strength:

**Example**: "What is the latest Python best practice?"
- Contains `latest` (EXTERNAL_FACT_UNCERTAIN)
- Contains `best practice` (OPINION)
- Signal strength: 0.8 for time-sensitive keywords
- **Result**: Classified as `EXTERNAL_FACT_UNCERTAIN` (stronger signal)

If signals are equal, the classifier uses LLM assessment to break ties.

---

### Q10: How do I export classification logs?

**A**:

```python
import json
from datetime import datetime

classification_log = []

async def classify_and_log(message: str):
    result = await classifier.classify(message)

    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "message": message,
        "classification": result.to_dict()
    }

    classification_log.append(log_entry)

    return result

# Export to JSON file
def export_log(filename: str):
    with open(filename, "w") as f:
        json.dump(classification_log, f, indent=2, default=str)
```

---

## Extension Guide

### Adding a New InfoNeedType

To add a new information need type (e.g., `COLLABORATIVE_QUERY`):

**Step 1: Define the enum value**

```python
# In agentos/core/chat/models/info_need.py

class InfoNeedType(str, Enum):
    LOCAL_DETERMINISTIC = "local_deterministic"
    LOCAL_KNOWLEDGE = "local_knowledge"
    AMBIENT_STATE = "ambient_state"
    EXTERNAL_FACT_UNCERTAIN = "external_fact_uncertain"
    OPINION = "opinion"
    COLLABORATIVE_QUERY = "collaborative_query"  # NEW
```

**Step 2: Add keywords for detection**

```python
# In agentos/core/chat/info_need_classifier.py

class RuleBasedFilter:
    # ... existing keywords ...

    COLLABORATIVE_KEYWORDS = [
        "collaborate", "work together", "team", "pair",
        "协作", "一起工作"
    ]

    def filter(self, message: str) -> ClassificationSignal:
        # ... existing checks ...

        # Check collaborative keywords
        has_collaborative = False
        for keyword in self.COLLABORATIVE_KEYWORDS:
            if keyword.lower() in message_lower:
                has_collaborative = True
                matched_keywords.append(f"collab:{keyword}")

        # Update signal strength calculation
        # ...
```

**Step 3: Update type determination logic**

```python
def _determine_type(self, signals: ClassificationSignal) -> InfoNeedType:
    # ... existing checks ...

    # Check for collaborative query
    collab_matches = [k for k in signals.matched_keywords if k.startswith("collab:")]
    if collab_matches:
        return InfoNeedType.COLLABORATIVE_QUERY

    # ... rest of logic ...
```

**Step 4: Add decision matrix entries**

```python
class DecisionMatrix:
    MATRIX = {
        # ... existing entries ...

        (InfoNeedType.COLLABORATIVE_QUERY, ConfidenceLevel.HIGH): DecisionAction.SUGGEST_COMM,
        (InfoNeedType.COLLABORATIVE_QUERY, ConfidenceLevel.MEDIUM): DecisionAction.REQUIRE_COMM,
        (InfoNeedType.COLLABORATIVE_QUERY, ConfidenceLevel.LOW): DecisionAction.REQUIRE_COMM,
    }
```

**Step 5: Add handler in ChatEngine**

```python
# In agentos/core/chat/engine.py

def send_message(self, session_id: str, user_input: str, stream: bool = False):
    # ... classification ...

    if classification_result.decision_action == DecisionAction.REQUIRE_COMM:
        if classification_result.info_need_type == InfoNeedType.COLLABORATIVE_QUERY:
            return self._handle_collaborative_query(session_id, user_input, ...)
        else:
            return self._handle_external_info_need(session_id, user_input, ...)
```

---

### Modifying LLM Prompt

To customize the LLM self-assessment prompt:

```python
from agentos.core.chat.info_need_classifier import LLMConfidenceEvaluator

class CustomLLMEvaluator(LLMConfidenceEvaluator):
    PROMPT_TEMPLATE = '''Evaluate answer stability for this question.

Question: {question}

Will your answer WITHOUT internet access be outdated within 24 hours?

Respond with JSON:
{{
  "confidence": "high | medium | low",
  "reason": "time-sensitive | authoritative | stable | uncertain | outdated"
}}

Custom instructions:
- "high": Information is timeless
- "medium": May change but slowly
- "low": Rapidly changing information

JSON response:'''

# Use custom evaluator
classifier = InfoNeedClassifier()
classifier.llm_evaluator = CustomLLMEvaluator(llm_callable=custom_llm_callable)
```

---

### Integrating with Other Systems

To integrate the classifier with your own chat system:

```python
from agentos.core.chat.info_need_classifier import InfoNeedClassifier
from agentos.core.chat.models.info_need import DecisionAction

class MyChatSystem:
    def __init__(self):
        self.classifier = InfoNeedClassifier()

    async def handle_message(self, user_message: str):
        # Classify the message
        result = await self.classifier.classify(user_message)

        # Route based on decision action
        if result.decision_action == DecisionAction.LOCAL_CAPABILITY:
            return self.handle_with_local_tools(user_message)

        elif result.decision_action == DecisionAction.DIRECT_ANSWER:
            return self.generate_llm_response(user_message)

        elif result.decision_action == DecisionAction.REQUIRE_COMM:
            return self.request_external_info(user_message, result)

        elif result.decision_action == DecisionAction.SUGGEST_COMM:
            response = self.generate_llm_response(user_message)
            response += "\n\nNote: For current info, consider searching online."
            return response

    def handle_with_local_tools(self, message: str):
        # Your local tool routing logic
        pass

    def generate_llm_response(self, message: str):
        # Your LLM invocation logic
        pass

    def request_external_info(self, message: str, classification):
        # Your external info handling logic
        pass
```

---

## Best Practices

### 1. Logging and Monitoring

**Log all classifications for audit**:

```python
import logging

logger = logging.getLogger(__name__)

async def classify_with_logging(classifier, message: str):
    result = await classifier.classify(message)

    logger.info(
        f"Classification: message='{message[:50]}...', "
        f"type={result.info_need_type.value}, "
        f"action={result.decision_action.value}, "
        f"confidence={result.confidence_level.value}, "
        f"signal_strength={result.rule_signals.signal_strength:.2f}"
    )

    return result
```

**Monitor classification distribution**:

```python
from collections import Counter

classification_counts = Counter()

async def classify_with_metrics(classifier, message: str):
    result = await classifier.classify(message)

    # Track classification distribution
    classification_counts[result.info_need_type.value] += 1

    # Log periodically
    if sum(classification_counts.values()) % 100 == 0:
        logger.info(f"Classification distribution: {dict(classification_counts)}")

    return result
```

---

### 2. Performance Optimization

**Use async efficiently**:

```python
# Batch classification
async def classify_batch(classifier, messages: list[str]):
    tasks = [classifier.classify(msg) for msg in messages]
    results = await asyncio.gather(*tasks)
    return results
```

**Profile classification time**:

```python
import time

async def classify_with_timing(classifier, message: str):
    start_time = time.time()
    result = await classifier.classify(message)
    elapsed_ms = (time.time() - start_time) * 1000

    logger.debug(f"Classification took {elapsed_ms:.2f}ms")

    # Alert if slow
    if elapsed_ms > 1000:  # 1 second
        logger.warning(f"Slow classification: {elapsed_ms:.2f}ms for '{message[:50]}'")

    return result
```

---

### 3. Testing Strategy

**Unit tests for rule-based filter**:

```python
import pytest
from agentos.core.chat.info_need_classifier import RuleBasedFilter

def test_time_sensitive_detection():
    filter = RuleBasedFilter()

    # Should detect time-sensitive keywords
    signal = filter.filter("What is the latest Python version?")
    assert signal.has_time_sensitive_keywords is True

    # Should not detect in stable query
    signal = filter.filter("What is Python?")
    assert signal.has_time_sensitive_keywords is False
```

**Integration tests for full pipeline**:

```python
@pytest.mark.asyncio
async def test_external_fact_classification():
    classifier = InfoNeedClassifier()

    result = await classifier.classify("What is the latest AI policy?")

    assert result.info_need_type.value == "external_fact_uncertain"
    assert result.decision_action.value == "require_comm"
```

**Mock LLM for deterministic tests**:

```python
async def mock_high_confidence(prompt: str) -> str:
    return '{"confidence": "high", "reason": "stable"}'

@pytest.mark.asyncio
async def test_with_mock_llm():
    classifier = InfoNeedClassifier(llm_callable=mock_high_confidence)

    result = await classifier.classify("What is REST API?")

    assert result.confidence_level.value == "high"
    assert result.decision_action.value == "direct_answer"
```

---

### 4. Monitoring Metrics

**Key metrics to track**:

1. **Classification distribution**:
   - % of LOCAL_DETERMINISTIC
   - % of LOCAL_KNOWLEDGE
   - % of AMBIENT_STATE
   - % of EXTERNAL_FACT_UNCERTAIN
   - % of OPINION

2. **Performance metrics**:
   - Average classification time
   - % of classifications that use LLM
   - LLM call latency

3. **Accuracy metrics** (requires manual review):
   - False positive rate for REQUIRE_COMM
   - False negative rate (missed external info needs)
   - User override rate (user ignores classification)

**Example monitoring setup**:

```python
import time
from dataclasses import dataclass, field
from typing import Dict

@dataclass
class ClassificationMetrics:
    type_counts: Dict[str, int] = field(default_factory=lambda: {})
    action_counts: Dict[str, int] = field(default_factory=lambda: {})
    llm_call_count: int = 0
    total_time_ms: float = 0.0
    count: int = 0

    def record(self, result, elapsed_ms: float, used_llm: bool):
        self.type_counts[result.info_need_type.value] = \
            self.type_counts.get(result.info_need_type.value, 0) + 1

        self.action_counts[result.decision_action.value] = \
            self.action_counts.get(result.decision_action.value, 0) + 1

        if used_llm:
            self.llm_call_count += 1

        self.total_time_ms += elapsed_ms
        self.count += 1

    def report(self):
        avg_time = self.total_time_ms / self.count if self.count > 0 else 0
        llm_rate = self.llm_call_count / self.count * 100 if self.count > 0 else 0

        print(f"Classification Metrics (n={self.count}):")
        print(f"  Average time: {avg_time:.2f}ms")
        print(f"  LLM usage rate: {llm_rate:.1f}%")
        print(f"  Type distribution: {self.type_counts}")
        print(f"  Action distribution: {self.action_counts}")

# Use
metrics = ClassificationMetrics()

async def classify_with_metrics(classifier, message: str):
    start = time.time()
    result = await classifier.classify(message)
    elapsed_ms = (time.time() - start) * 1000

    used_llm = result.llm_confidence is not None
    metrics.record(result, elapsed_ms, used_llm)

    return result
```

---

## Summary

The InfoNeedClassifier is a **judgment-only** system that:

1. **Classifies** user questions into 5 types based on information requirements
2. **Evaluates** confidence using rules + optional LLM self-assessment
3. **Recommends** actions (local tools, direct answer, communication required)
4. **Does NOT** execute searches, fetch data, or generate answers

Key design principles:
- Separate what we CAN know from what we CLAIM to know
- Use fast rule-based path for clear cases (< 10ms)
- Use LLM only for stability assessment, not knowledge claims
- Make uncertainty explicit and actionable
- Route questions to appropriate handlers

For more details, see:
- [INFO_NEED_CLASSIFIER_QUICK_REF.md](./INFO_NEED_CLASSIFIER_QUICK_REF.md) - One-page quick reference
- [info_need_classifier_demo.py](../../examples/info_need_classifier_demo.py) - Interactive demo
- [info_need_classifier.py](../../agentos/core/chat/info_need_classifier.py) - Implementation
