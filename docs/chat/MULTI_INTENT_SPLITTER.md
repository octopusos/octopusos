# Multi-Intent Question Splitter

## Overview

The Multi-Intent Question Splitter is a rule-based component that detects and splits composite questions containing multiple intents into individual sub-questions.

**Key Features:**
- Rule-based (no LLM) - Low latency (<5ms p95) and cost
- Conservative strategy - Preserves original question when uncertain
- Context preservation - Detects when sub-questions need context
- Bilingual support - Handles both Chinese and English

## Quick Start

```python
from agentos.core.chat.multi_intent_splitter import MultiIntentSplitter

splitter = MultiIntentSplitter()

# Check if question should be split
question = "现在几点？以及最新AI政策"
if splitter.should_split(question):
    # Split into sub-questions
    sub_questions = splitter.split(question)

    for sub_q in sub_questions:
        print(f"[{sub_q.index}] {sub_q.text}")
        if sub_q.needs_context:
            print(f"    → Needs context: {sub_q.context_hint}")
```

Output:
```
[0] 现在几点？
[1] 最新AI政策
```

## Splitting Rules

### 1. Connector-Based Splitting

Detects connector words that join independent questions.

**Chinese Connectors:**
- 以及, 还有, 另外, 同时, 顺便
- 而且, 并且, 再者, 此外

**English Connectors:**
- and also, also, additionally, as well as
- by the way, furthermore, moreover, besides

**Examples:**
```python
# Chinese
"现在几点？以及最新AI政策"
→ ["现在几点？", "最新AI政策"]

# English
"What's the time? And also the latest AI policy"
→ ["What's the time?", "the latest AI policy"]
```

### 2. Punctuation-Based Splitting

Detects punctuation patterns that mark question boundaries.

**Patterns:**
- `.？` or `.?` - Period followed by question mark
- `；` or `;` - Semicolon

**Examples:**
```python
"谁是当前总统；他的政策是什么？"
→ ["谁是当前总统", "他的政策是什么？"]

"What is Docker; How to install it?"
→ ["What is Docker", "How to install it?"]
```

### 3. Enumeration-Based Splitting

Detects numbered or ordered lists.

**Patterns:**
- Numeric: `1. 2. 3.` or `1) 2) 3)`
- Parenthesized: `(1) (2) (3)` or `（1）（2）`
- Ordinal: `First, Second,` or `第一, 第二,`

**Examples:**
```python
"1. 现在几点 2. 今天天气 3. 最新新闻"
→ ["现在几点", "今天天气", "最新新闻"]

"First, check the logs. Second, restart the service."
→ ["check the logs", "restart the service"]
```

## Conservative Splitting Policy

The splitter is **conservative by design** - when uncertain, it preserves the original question.

### Cases That Will NOT Split

1. **Parallel Components** (not independent questions)
   ```python
   "最新的AI政策以及实施细节是什么？"
   # NOT split - "以及" connects parallel aspects of a single question
   ```

2. **Short Sub-Questions** (< min_length)
   ```python
   "短；短"
   # NOT split - sub-questions too short
   ```

3. **Too Many Splits** (> max_splits)
   ```python
   "1. A 2. B 3. C 4. D 5. E"  # max_splits=3 by default
   # NOT split - exceeds maximum
   ```

4. **Compound Objects**
   ```python
   "Show me files with .py and .js extensions"
   # NOT split - "and" connects file extensions, not questions
   ```

5. **Single Questions with Multiple Aspects**
   ```python
   "比较Python和Java的性能以及语法差异"
   # NOT split - single comparison question with multiple aspects
   ```

## Context Preservation

The splitter detects when sub-questions need context from previous questions.

### Context Indicators

**Pronouns and References:**
- English: he, she, it, they, his, her, this, that
- Chinese: 他, 她, 它, 们, 这, 那

**Examples:**
```python
"谁是现任总统？以及他的主要政策"
→ SubQuestion 1: "谁是现任总统？"
   - needs_context: False

→ SubQuestion 2: "他的主要政策"
   - needs_context: True
   - context_hint: "pronoun_reference"
```

### Using Context Hints

```python
sub_questions = splitter.split("Who is the CEO? And what are his policies?")

for sub_q in sub_questions:
    if sub_q.needs_context:
        # Include previous sub-question(s) as context
        context = sub_questions[sub_q.index - 1].text
        process_with_context(sub_q.text, context)
    else:
        process_standalone(sub_q.text)
```

## Configuration

```python
config = {
    'min_length': 5,           # Minimum sub-question length (default: 5)
    'max_splits': 3,           # Maximum splits allowed (default: 3)
    'enable_context': True,    # Enable context detection (default: True)
}

splitter = MultiIntentSplitter(config=config)
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `min_length` | int | 5 | Minimum character length for valid sub-question |
| `max_splits` | int | 3 | Maximum number of splits (returns empty if exceeded) |
| `enable_context` | bool | True | Whether to detect and mark context needs |

## Performance

**Target:** < 5ms per split (p95)

**Measured Performance:**
- Simple split (2 questions): ~0.1-0.5ms
- Complex enumeration (3-5 items): ~0.5-1.0ms
- Long text (1000+ chars): ~2-5ms

The splitter is designed for real-time use in chat pipelines with minimal latency impact.

## API Reference

### `MultiIntentSplitter`

Main class for splitting multi-intent questions.

```python
class MultiIntentSplitter:
    def __init__(self, config: Optional[Dict[str, Any]] = None)
    def should_split(self, question: str) -> bool
    def split(self, question: str) -> List[SubQuestion]
```

#### Methods

**`should_split(question: str) -> bool`**

Fast pre-check to determine if splitting is needed.

- **Args:** `question` - Question text to evaluate
- **Returns:** `True` if question likely contains multiple intents

**`split(question: str) -> List[SubQuestion]`**

Split question into sub-questions.

- **Args:** `question` - Composite question to split
- **Returns:** List of `SubQuestion` objects (empty if no split needed)

### `SubQuestion`

Data class representing a split sub-question.

```python
@dataclass
class SubQuestion:
    text: str                    # Sub-question text
    index: int                   # Zero-based index in sequence
    original_start: int          # Start position in original text
    original_end: int            # End position in original text
    needs_context: bool = False  # Whether context is needed
    context_hint: Optional[str] = None  # Type of context needed

    def to_dict(self) -> Dict[str, Any]
```

### Convenience Function

```python
def split_question(
    question: str,
    config: Optional[Dict[str, Any]] = None
) -> List[SubQuestion]
```

One-off splitting without creating a splitter instance.

## Usage Examples

### Basic Splitting

```python
from agentos.core.chat.multi_intent_splitter import split_question

# Simple case
result = split_question("现在几点？以及最新AI政策")
print(f"Split into {len(result)} questions:")
for sub_q in result:
    print(f"  - {sub_q.text}")
```

### With Configuration

```python
splitter = MultiIntentSplitter(config={
    'min_length': 3,
    'max_splits': 5,
})

result = splitter.split("1. A 2. B 3. C 4. D")
# Will split (doesn't exceed max_splits=5)
```

### Context-Aware Processing

```python
splitter = MultiIntentSplitter(config={'enable_context': True})
result = splitter.split("Who is the CEO? And what are his policies?")

for i, sub_q in enumerate(result):
    if sub_q.needs_context and i > 0:
        # Include previous question as context
        context = result[i-1].text
        answer = process_with_context(sub_q.text, context)
    else:
        answer = process_standalone(sub_q.text)
    print(answer)
```

### Integration with Chat Engine

```python
def process_user_message(message: str):
    splitter = MultiIntentSplitter()

    if splitter.should_split(message):
        sub_questions = splitter.split(message)
        answers = []

        for sub_q in sub_questions:
            answer = chat_engine.process(sub_q.text)
            answers.append(answer)

        # Combine answers
        return combine_answers(answers)
    else:
        # Process as single question
        return chat_engine.process(message)
```

## Known Limitations

1. **No Semantic Understanding**
   - Rule-based approach cannot understand semantic relationships
   - May occasionally split parallel components or miss complex patterns

2. **Limited to Supported Patterns**
   - Only detects predefined connector words and punctuation patterns
   - May miss unconventional question structures

3. **Context Detection is Heuristic**
   - Pronoun detection doesn't guarantee actual reference
   - May miss subtle context dependencies

4. **No Cross-Sentence Analysis**
   - Doesn't analyze broader context or conversation history
   - Each question is evaluated independently

5. **Language Support**
   - Optimized for Chinese and English
   - Other languages may require additional patterns

## Best Practices

1. **Use should_split() First**
   ```python
   # More efficient - avoids unnecessary work
   if splitter.should_split(question):
       result = splitter.split(question)
   ```

2. **Reuse Splitter Instances**
   ```python
   # Good - reuse instance
   splitter = MultiIntentSplitter()
   for question in questions:
       result = splitter.split(question)

   # Less optimal - creates new instance each time
   for question in questions:
       result = split_question(question)
   ```

3. **Handle Empty Results**
   ```python
   result = splitter.split(question)
   if not result:
       # No split - process original question
       process(question)
   else:
       # Process sub-questions
       for sub_q in result:
           process(sub_q.text)
   ```

4. **Preserve Original Question**
   ```python
   result = splitter.split(question)
   if result:
       # Store original for reference
       metadata = {'original_question': question}
       for sub_q in result:
           process(sub_q.text, metadata)
   ```

## Testing

Comprehensive test suite with 35+ test cases covering:
- Connector-based splitting (Chinese and English)
- Punctuation-based splitting
- Enumeration-based splitting
- Conservative non-split cases
- Context preservation
- Performance benchmarks

Run tests:
```bash
pytest tests/unit/core/chat/test_multi_intent_splitter.py -v
```

## Version History

- **v1.0.0** (2026-01-31)
  - Initial implementation
  - Rule-based splitting with 3 strategies
  - Context preservation support
  - Bilingual support (Chinese/English)
  - Performance target: <5ms p95

## References

- Test case matrix: `tests/fixtures/multi_intent_test_cases.yaml`
- Unit tests: `tests/unit/core/chat/test_multi_intent_splitter.py`
- Implementation: `agentos/core/chat/multi_intent_splitter.py`
