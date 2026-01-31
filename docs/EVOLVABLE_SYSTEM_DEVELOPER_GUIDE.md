# Evolvable System Developer Guide

**Document Version**: 1.0
**Last Updated**: 2026-01-31
**Audience**: Software Engineers, System Integrators

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Extending Quality Metrics](#extending-quality-metrics)
3. [Adding Pattern Types](#adding-pattern-types)
4. [Integrating New Splitting Rules](#integrating-new-splitting-rules)
5. [Debugging Techniques](#debugging-techniques)
6. [Testing Strategies](#testing-strategies)
7. [Performance Optimization](#performance-optimization)
8. [Common Pitfalls](#common-pitfalls)

---

## 1. Getting Started

### 1.1 Development Environment Setup

```bash
# Clone repository
git clone https://github.com/yourorg/agentos.git
cd agentos

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Run database migrations
sqlite3 store/registry.sqlite < agentos/store/migrations/schema_v38_info_need_judgments.sql
sqlite3 store/registry.sqlite < agentos/store/migrations/schema_v39_info_need_patterns.sql

# Verify installation
python -m pytest tests/ -v --maxfail=5
```

### 1.2 Project Structure

```
agentos/
├── core/
│   ├── audit.py                    # Audit logging system
│   ├── chat/
│   │   ├── engine.py               # Main chat orchestrator
│   │   ├── info_need_classifier.py # Classification logic
│   │   └── multi_intent_splitter.py # Intent splitting
│   ├── memory/
│   │   ├── schema.py               # MemoryOS data models
│   │   └── info_need_writer.py     # MemoryOS writer
│   └── brain/
│       ├── info_need_pattern_models.py   # Pattern data models
│       ├── info_need_pattern_extractor.py # Feature extraction
│       └── info_need_pattern_writer.py   # BrainOS writer
├── metrics/
│   └── info_need_metrics.py        # Quality metrics calculator
├── jobs/
│   └── info_need_pattern_extraction.py # Daily pattern extraction
└── webui/
    ├── api/
    │   └── info_need_metrics.py    # Metrics API endpoints
    └── static/
        ├── js/views/InfoNeedMetricsView.js
        └── css/info-need-metrics.css
```

### 1.3 Key Concepts

**Information Need Types** (5 types):
- `LOCAL_DETERMINISTIC`: Answers from code/data analysis
- `LOCAL_KNOWLEDGE`: Answers from LLM knowledge
- `AMBIENT_STATE`: System state queries
- `EXTERNAL_FACT_UNCERTAIN`: Requires external verification
- `OPINION_DISCUSSION`: Subjective questions

**Decision Actions** (4 actions):
- `LOCAL_CAPABILITY`: Handle locally (ambient state)
- `DIRECT_ANSWER`: Generate LLM response
- `REQUIRE_COMM`: Require external communication
- `SUGGEST_COMM`: Suggest external search

**Three-Step Classification**:
1. Rule-based filter (fast path)
2. LLM self-assessment (when needed)
3. Decision matrix (final decision)

---

## 2. Extending Quality Metrics

### 2.1 Adding a New Metric

**Example**: Add "Average Confidence Score" metric

**Step 1**: Define metric calculation in `info_need_metrics.py`

```python
# File: agentos/metrics/info_need_metrics.py

def _calculate_avg_confidence(self, enriched_data: List[Dict]) -> float:
    """
    Calculate average LLM confidence score.

    Args:
        enriched_data: List of classification events with outcomes

    Returns:
        Average confidence score (0.0-1.0)
    """
    confidence_scores = []

    for event in enriched_data:
        payload = event.get('payload', {})
        llm_conf = payload.get('llm_confidence_score')

        if llm_conf is not None:
            confidence_scores.append(llm_conf)

    if not confidence_scores:
        return 0.0

    return statistics.mean(confidence_scores)
```

**Step 2**: Add to `calculate_metrics()` method

```python
def calculate_metrics(
    self,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> Dict[str, Any]:
    """Calculate all metrics."""

    # ... existing code ...

    # Add new metric
    avg_confidence = self._calculate_avg_confidence(enriched_data)

    return {
        # ... existing metrics ...
        'avg_confidence_score': avg_confidence,
    }
```

**Step 3**: Update WebUI API to expose new metric

```python
# File: agentos/webui/api/info_need_metrics.py

@metrics_bp.route('/', methods=['GET'])
async def get_metrics():
    """Get InfoNeed metrics."""

    # ... existing code ...

    return jsonify({
        # ... existing metrics ...
        'avg_confidence_score': metrics['avg_confidence_score'],
    })
```

**Step 4**: Update WebUI view to display new metric

```javascript
// File: agentos/webui/static/js/views/InfoNeedMetricsView.js

renderMetricCards(metrics) {
    // ... existing cards ...

    // Add new card
    const avgConfidenceCard = this.createMetricCard(
        'Average Confidence',
        (metrics.avg_confidence_score * 100).toFixed(1) + '%',
        'gauge',
        this.getConfidenceTrend(metrics.avg_confidence_score)
    );

    container.appendChild(avgConfidenceCard);
}
```

**Step 5**: Add tests

```python
# File: tests/unit/metrics/test_info_need_metrics.py

def test_avg_confidence_calculation():
    """Test average confidence score calculation."""

    # Create test data
    events = [
        create_event(llm_confidence_score=0.8),
        create_event(llm_confidence_score=0.9),
        create_event(llm_confidence_score=0.7),
    ]

    # Calculate
    metrics = InfoNeedMetrics()
    result = metrics.calculate_metrics()

    # Verify
    assert result['avg_confidence_score'] == 0.8  # (0.8 + 0.9 + 0.7) / 3
```

**Step 6**: Update documentation

Add metric description to:
- `agentos/metrics/README.md`
- `EVOLVABLE_SYSTEM_FINAL_ACCEPTANCE_REPORT.md`
- API documentation

### 2.2 Metric Calculation Best Practices

1. **Use Non-Semantic Methods**
   - Only use metadata and statistics
   - No LLM calls in metrics calculation
   - No semantic analysis

2. **Handle Missing Data Gracefully**
   ```python
   # Good
   if not data:
       return 0.0

   # Bad
   return sum(data) / len(data)  # Crashes if empty
   ```

3. **Provide Breakdown by Type**
   ```python
   def _calculate_metric_by_type(self, data: List[Dict]) -> Dict[str, float]:
       """Calculate metric broken down by classification type."""
       by_type = {}

       for info_type in InfoNeedType:
           type_data = [d for d in data if d['type'] == info_type.value]
           by_type[info_type.value] = self._calculate_metric(type_data)

       return by_type
   ```

4. **Document Calculation Formula**
   ```python
   def _calculate_metric(self, data: List[Dict]) -> float:
       """
       Calculate metric X.

       Formula: (positive_count / total_count)

       Where:
       - positive_count: Events with outcome='validated'
       - total_count: All events in time range

       Returns:
           Metric value between 0.0 and 1.0
       """
   ```

---

## 3. Adding Pattern Types

### 3.1 Define New Pattern Category

**Example**: Add "API Call Pattern" for API-related questions

**Step 1**: Extend feature extraction

```python
# File: agentos/core/brain/info_need_pattern_extractor.py

class QuestionFeatureExtractor:

    # Add new keyword category
    API_KEYWORDS = {
        'api', 'endpoint', 'rest', 'graphql', 'webhook',
        'http', 'https', 'post', 'get', 'put', 'delete',
        'request', 'response', 'status code', 'header'
    }

    def extract_features(self, question: str) -> Dict[str, Any]:
        """Extract all features from question."""

        features = {
            # ... existing features ...

            # Add new feature
            'has_api_pattern': self._detect_api_pattern(question),
        }

        return features

    def _detect_api_pattern(self, text: str) -> bool:
        """Detect API-related keywords."""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.API_KEYWORDS)
```

**Step 2**: Include in feature signature

```python
def _generate_feature_signature(self, features: Dict[str, Any]) -> str:
    """Generate signature for clustering."""

    sig_parts = [
        # ... existing parts ...
        'api' if features['has_api_pattern'] else '',
    ]

    return '|'.join(filter(None, sig_parts))
```

**Step 3**: Add to pattern metadata

```python
# When creating pattern node
pattern = InfoNeedPatternNode(
    # ... existing fields ...
    metadata={
        'is_api_related': features['has_api_pattern'],
        # ... other metadata ...
    }
)
```

**Step 4**: Query patterns by new category

```python
# File: agentos/core/brain/info_need_pattern_writer.py

async def query_api_patterns(
    self,
    min_success_rate: float = 0.8
) -> List[InfoNeedPatternNode]:
    """Query API-related patterns."""

    query = """
        SELECT * FROM info_need_patterns
        WHERE json_extract(metadata, '$.is_api_related') = 1
        AND success_rate >= ?
        ORDER BY occurrence_count DESC
    """

    # ... execute query ...

    return patterns
```

**Step 5**: Add tests

```python
# File: tests/unit/core/brain/test_info_need_pattern_extractor.py

def test_api_pattern_detection():
    """Test API pattern detection."""

    extractor = QuestionFeatureExtractor()

    # Test positive cases
    assert extractor.extract_features("How to call REST API?")['has_api_pattern']
    assert extractor.extract_features("What is the endpoint for user data?")['has_api_pattern']

    # Test negative cases
    assert not extractor.extract_features("What is Python?")['has_api_pattern']
```

### 3.2 Pattern Evolution Strategies

**Refining Patterns**:
```python
async def refine_pattern(
    self,
    pattern_id: str,
    new_data: List[InfoNeedJudgment]
) -> str:
    """
    Refine existing pattern with new data.

    Updates statistics, examples, and feature vector.
    """

    # Load existing pattern
    old_pattern = await self.get_pattern(pattern_id)

    # Merge with new data
    new_pattern = self._merge_pattern_data(old_pattern, new_data)

    # Track evolution
    new_id = await self.evolve_pattern(
        old_pattern_id=pattern_id,
        new_pattern=new_pattern,
        evolution_type='refined',
        reason=f'Updated with {len(new_data)} new judgments'
    )

    return new_id
```

**Splitting Patterns**:
```python
async def split_pattern(
    self,
    pattern_id: str,
    split_criteria: Dict[str, Any]
) -> List[str]:
    """
    Split pattern into multiple sub-patterns.

    Useful when pattern becomes too broad.
    """

    # Load pattern
    pattern = await self.get_pattern(pattern_id)

    # Get all judgments for this pattern
    judgments = await self._get_pattern_judgments(pattern_id)

    # Split by criteria (e.g., by feature value)
    sub_groups = self._group_by_criteria(judgments, split_criteria)

    # Create new patterns for each group
    new_ids = []
    for group in sub_groups:
        new_pattern = self._create_pattern_from_judgments(group)
        new_id = await self.write_pattern(new_pattern)
        new_ids.append(new_id)

    # Track evolution
    for new_id in new_ids:
        await self.evolve_pattern(
            old_pattern_id=pattern_id,
            new_pattern_id=new_id,
            evolution_type='split',
            reason='Pattern split due to high variance'
        )

    # Deprecate old pattern
    await self.deprecate_pattern(pattern_id)

    return new_ids
```

---

## 4. Integrating New Splitting Rules

### 4.1 Add Custom Connector Pattern

**Example**: Add support for "以及" (Chinese connector) variations

**Step 1**: Extend connector list

```python
# File: agentos/core/chat/multi_intent_splitter.py

class MultiIntentSplitter:

    # Extend Chinese connectors
    CHINESE_CONNECTORS = [
        "以及",
        "还有",
        "另外",
        "同时",
        "顺便",
        # Add new variations
        "并且",
        "而且",
        "此外",
    ]
```

**Step 2**: Add to test cases

```yaml
# File: tests/fixtures/multi_intent_test_cases.yaml

- id: connector_chinese_bingqie
  category: connector_splitting
  input: "现在几点？并且最新AI政策是什么？"
  expected_split: true
  expected_count: 2
  expected_texts:
    - "现在几点？"
    - "最新AI政策是什么？"
```

**Step 3**: Test thoroughly

```python
# File: tests/unit/core/chat/test_multi_intent_splitter.py

def test_chinese_connector_bingqie():
    """Test new Chinese connector '并且'."""

    splitter = MultiIntentSplitter()

    result = splitter.split("现在几点？并且最新AI政策是什么？")

    assert len(result) == 2
    assert result[0].text == "现在几点？"
    assert result[1].text == "最新AI政策是什么？"
```

### 4.2 Add Custom Splitting Strategy

**Example**: Add "Because/So" pattern (causal relationship detection)

**Step 1**: Implement detection method

```python
def _detect_causal_pattern(self, text: str) -> bool:
    """
    Detect causal relationship patterns.

    Patterns:
    - "... because ... so ..."
    - "... 因为 ... 所以 ..."
    """

    # English pattern
    if ' because ' in text.lower() and ' so ' in text.lower():
        because_pos = text.lower().index(' because ')
        so_pos = text.lower().index(' so ')
        if so_pos > because_pos:
            return True

    # Chinese pattern
    if '因为' in text and '所以' in text:
        yinwei_pos = text.index('因为')
        suoyi_pos = text.index('所以')
        if suoyi_pos > yinwei_pos:
            return True

    return False
```

**Step 2**: Implement splitting logic

```python
def _split_causal_pattern(self, text: str) -> List[SubQuestion]:
    """Split on causal relationship."""

    # English
    if ' because ' in text.lower() and ' so ' in text.lower():
        parts = []

        # Split on "because"
        before, after = text.split(' because ', 1)
        reason, conclusion = after.split(' so ', 1)

        parts.append(SubQuestion(
            text=f"{before} because {reason}?",
            index=0,
            original_context=text,
            needs_context=False,
            context_hint=""
        ))

        parts.append(SubQuestion(
            text=f"So {conclusion}?",
            index=1,
            original_context=text,
            needs_context=True,
            context_hint="causal_dependency"
        ))

        return parts

    # Similar for Chinese...

    return []
```

**Step 3**: Integrate into main split logic

```python
def split(self, question: str) -> List[SubQuestion]:
    """Split question into sub-questions."""

    # ... existing strategies ...

    # Try causal pattern
    if self._detect_causal_pattern(question):
        result = self._split_causal_pattern(question)
        if result and self._validate_split(result):
            return result

    # ... fallback logic ...
```

**Step 4**: Add comprehensive tests

```python
def test_causal_pattern_english():
    """Test causal pattern splitting (English)."""

    splitter = MultiIntentSplitter()

    result = splitter.split("What is AGI because I want to understand so I can prepare?")

    assert len(result) == 2
    assert "because" in result[0].text.lower()
    assert result[1].needs_context  # Second part depends on first
```

### 4.3 Splitting Rule Best Practices

1. **Conservative by Default**
   - Only split when confidence is high
   - Validate minimum length requirements
   - Check question substance

2. **Detect Context Dependencies**
   ```python
   # Always check for pronouns or incomplete sentences
   if self._has_pronouns(sub_question):
       sub_question.needs_context = True
       sub_question.context_hint = "pronoun_reference"
   ```

3. **Provide Clear Context Hints**
   ```python
   # Context hint types:
   # - "pronoun_reference": Contains "his", "her", "it", etc.
   # - "incomplete_sentence": Starts with connector, no subject
   # - "causal_dependency": Depends on previous result
   # - "temporal_reference": Contains "then", "after", etc.
   ```

4. **Test Edge Cases**
   - Single word questions
   - Very long questions
   - Unicode characters
   - Mixed languages
   - Special characters

---

## 5. Debugging Techniques

### 5.1 Debug Classification Decisions

**Method 1: Verbose Logging**

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Classification will log:
# - Rule signals detected
# - LLM confidence assessment
# - Decision matrix reasoning

classifier = InfoNeedClassifier()
result = await classifier.classify("What is the latest Python version?")
```

**Method 2: Inspect Classification Result**

```python
result = await classifier.classify("Your question")

print(f"Type: {result.classified_type}")
print(f"Action: {result.decision_action}")
print(f"Confidence: {result.confidence_level}")
print(f"Reasoning: {result.reasoning}")
print(f"Rule Signals: {json.dumps(result.rule_signals, indent=2)}")
print(f"LLM Confidence: {result.llm_confidence}")
```

**Method 3: Query MemoryOS for History**

```python
from agentos.core.memory.info_need_writer import InfoNeedMemoryWriter

writer = InfoNeedMemoryWriter()

# Get recent judgments for analysis
judgments = await writer.query_recent_judgments(
    session_id="session-123",
    time_range="1h"
)

for j in judgments:
    print(f"\nQuestion: {j.question_text}")
    print(f"Type: {j.classified_type}")
    print(f"Outcome: {j.outcome}")
    print(f"Rule Signals: {j.rule_signals}")
```

### 5.2 Debug Multi-Intent Splitting

**Method 1: Test Individual Rules**

```python
splitter = MultiIntentSplitter()

# Test detection
question = "What time? What weather?"
print(f"Should split: {splitter.should_split(question)}")

# Test individual strategies
print(f"Connector detected: {splitter._detect_connector_split(question)}")
print(f"Punctuation detected: {splitter._detect_punctuation_split(question)}")
print(f"Question marks detected: {splitter._detect_multiple_question_marks(question)}")
```

**Method 2: Inspect Sub-Questions**

```python
result = splitter.split("Your composite question")

for sub_q in result:
    print(f"\n[{sub_q.index}] {sub_q.text}")
    print(f"  Needs context: {sub_q.needs_context}")
    print(f"  Context hint: {sub_q.context_hint}")
    print(f"  Original: {sub_q.original_context}")
```

### 5.3 Debug Pattern Extraction

**Method 1: Dry-Run Extraction**

```bash
# Run in dry-run mode (no writes)
python -m agentos.jobs.info_need_pattern_extraction --days 7 --dry-run
```

**Method 2: Inspect Features**

```python
from agentos.core.brain.info_need_pattern_extractor import QuestionFeatureExtractor

extractor = QuestionFeatureExtractor()

features = extractor.extract_features("What is the latest Python version?")

print(json.dumps(features, indent=2))
# {
#   "has_time_sensitive": true,
#   "has_code_pattern": true,
#   "question_length": 39,
#   ...
# }
```

**Method 3: Query Patterns with Filters**

```python
from agentos.core.brain.info_need_pattern_writer import InfoNeedPatternWriter

writer = InfoNeedPatternWriter()

# Query low-performing patterns
patterns = await writer.query_patterns(
    min_occurrences=10,
    max_success_rate=0.5  # Custom filter
)

for p in patterns:
    print(f"\nPattern: {p.pattern_signature}")
    print(f"Success rate: {p.success_rate:.1%}")
    print(f"Occurrences: {p.occurrence_count}")
    print(f"Examples: {p.example_questions[:3]}")
```

### 5.4 Debug Metrics Calculation

**Method 1: Check Audit Log Data**

```bash
# Query audit log
sqlite3 store/registry.sqlite "
  SELECT event_type, COUNT(*) as count
  FROM task_audits
  WHERE timestamp > datetime('now', '-7 days')
  GROUP BY event_type
"
```

**Method 2: Inspect Metric Calculation Steps**

```python
from agentos.metrics.info_need_metrics import InfoNeedMetrics

metrics = InfoNeedMetrics()

# Load data (inspect intermediate results)
classifications = metrics._load_classification_events(
    start_time="2026-01-01",
    end_time="2026-01-31"
)

print(f"Total classifications: {len(classifications)}")

outcomes = metrics._load_outcome_events(
    start_time="2026-01-01",
    end_time="2026-01-31"
)

print(f"Total outcomes: {len(outcomes)}")

# Enrich and inspect
enriched = metrics._enrich_with_outcomes(classifications, outcomes)

print(f"Matched: {sum(1 for e in enriched if e.get('outcome'))}")
print(f"Unmatched: {sum(1 for e in enriched if not e.get('outcome'))}")
```

---

## 6. Testing Strategies

### 6.1 Unit Testing

**Test Structure**:
```python
# tests/unit/core/chat/test_info_need_classifier.py

import pytest
from agentos.core.chat.info_need_classifier import InfoNeedClassifier

class TestRuleBasedFilter:
    """Test rule-based classification filter."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return InfoNeedClassifier()

    def test_time_sensitive_keywords(self, classifier):
        """Test detection of time-sensitive keywords."""

        # Test positive cases
        assert classifier._detect_time_sensitive("What is the latest Python version?")
        assert classifier._detect_time_sensitive("最新AI政策")

        # Test negative cases
        assert not classifier._detect_time_sensitive("What is Python?")

    def test_ambient_state_detection(self, classifier):
        """Test ambient state query detection."""

        # Should detect
        assert classifier._detect_ambient_state("What time is it?")
        assert classifier._detect_ambient_state("What phase are we in?")

        # Should not detect
        assert not classifier._detect_ambient_state("What is the weather?")
```

**Parametrized Testing**:
```python
@pytest.mark.parametrize("question,expected_type", [
    ("What time is it?", "AMBIENT_STATE"),
    ("What is Python?", "LOCAL_KNOWLEDGE"),
    ("Latest AI news?", "EXTERNAL_FACT_UNCERTAIN"),
])
def test_classification_types(classifier, question, expected_type):
    """Test classification for various question types."""
    result = asyncio.run(classifier.classify(question))
    assert result.classified_type.value == expected_type
```

### 6.2 Integration Testing

**Test End-to-End Flows**:
```python
# tests/integration/chat/test_multi_intent_e2e.py

@pytest.mark.asyncio
async def test_multi_intent_end_to_end():
    """Test complete multi-intent flow."""

    # Setup
    engine = ChatEngine()

    # Execute
    response = await engine.send_message(
        user_input="What time? What phase?",
        session_id="test-session",
        mode="normal",
        phase="planning"
    )

    # Verify
    assert response['type'] == 'multi_intent'
    assert response['sub_count'] == 2
    assert response['success_count'] == 2

    # Verify audit logging
    audit_events = get_audit_events(session_id="test-session")
    assert any(e['event_type'] == 'MULTI_INTENT_SPLIT' for e in audit_events)

    # Verify MemoryOS writes
    judgments = await get_recent_judgments(session_id="test-session")
    assert len(judgments) == 2
```

### 6.3 Performance Testing

**Benchmark Critical Paths**:
```python
# tests/performance/test_classification_performance.py

import time

def test_classification_latency():
    """Measure classification latency."""

    classifier = InfoNeedClassifier()
    questions = [
        "What time is it?",
        "What is Python?",
        "Latest AI news?",
    ]

    latencies = []

    for q in questions:
        start = time.time()
        result = asyncio.run(classifier.classify(q))
        latency = (time.time() - start) * 1000  # ms
        latencies.append(latency)

    # Assert p95 < 200ms
    p95 = sorted(latencies)[int(len(latencies) * 0.95)]
    assert p95 < 200, f"p95 latency {p95}ms exceeds target 200ms"
```

### 6.4 Regression Testing

**Maintain Golden Test Suite**:
```python
# tests/regression/test_classification_golden.py

GOLDEN_CASES = [
    {
        'question': "What time is it?",
        'expected_type': "AMBIENT_STATE",
        'expected_action': "LOCAL_CAPABILITY",
    },
    {
        'question': "Latest Python 3.13 features?",
        'expected_type': "EXTERNAL_FACT_UNCERTAIN",
        'expected_action': "REQUIRE_COMM",
    },
    # ... more cases ...
]

@pytest.mark.parametrize("case", GOLDEN_CASES)
def test_golden_case(case):
    """Test against golden test case."""
    classifier = InfoNeedClassifier()
    result = asyncio.run(classifier.classify(case['question']))

    assert result.classified_type.value == case['expected_type'], \
        f"Type mismatch for: {case['question']}"
    assert result.decision_action.value == case['expected_action'], \
        f"Action mismatch for: {case['question']}"
```

---

## 7. Performance Optimization

### 7.1 Optimize Classification Speed

**Technique 1: Rule-Based Fast Path**

Already implemented! Rule-based filter provides < 2ms classification for high-confidence cases, bypassing expensive LLM calls.

**Technique 2: LLM Response Caching**

```python
from functools import lru_cache
import hashlib

class InfoNeedClassifier:

    @lru_cache(maxsize=1000)
    def _get_cached_llm_assessment(self, question_hash: str) -> str:
        """Cache LLM assessments by question hash."""
        # Cached for identical questions within session
        return self._call_llm(question_hash)

    async def _assess_with_llm(self, message: str) -> str:
        """Assess with LLM (with caching)."""

        # Create hash
        question_hash = hashlib.sha256(message.encode()).hexdigest()

        # Try cache
        return self._get_cached_llm_assessment(question_hash)
```

**Technique 3: Batch Processing**

```python
async def classify_batch(
    self,
    messages: List[str]
) -> List[ClassificationResult]:
    """
    Classify multiple messages in batch.

    Benefits:
    - Shared LLM warmup cost
    - Potential parallel LLM calls
    - Batch database writes
    """

    results = []

    # Process in parallel where possible
    tasks = [self.classify(msg) for msg in messages]
    results = await asyncio.gather(*tasks)

    return results
```

### 7.2 Optimize Database Queries

**Technique 1: Use Prepared Statements**

```python
# Instead of string formatting
cursor.execute(f"SELECT * FROM judgments WHERE session_id = '{session_id}'")

# Use parameterized queries
cursor.execute("SELECT * FROM judgments WHERE session_id = ?", (session_id,))
```

**Technique 2: Optimize Indices**

```sql
-- Create composite index for common query pattern
CREATE INDEX IF NOT EXISTS idx_judgments_session_timestamp
ON info_need_judgments(session_id, timestamp DESC);

-- Use ANALYZE to update query planner statistics
ANALYZE info_need_judgments;
```

**Technique 3: Paginate Large Result Sets**

```python
async def query_recent_judgments_paginated(
    self,
    session_id: str,
    page_size: int = 100,
    offset: int = 0
) -> List[InfoNeedJudgment]:
    """Query with pagination."""

    query = """
        SELECT * FROM info_need_judgments
        WHERE session_id = ?
        ORDER BY timestamp DESC
        LIMIT ? OFFSET ?
    """

    cursor.execute(query, (session_id, page_size, offset))
    return [self._row_to_judgment(row) for row in cursor.fetchall()]
```

### 7.3 Optimize Pattern Extraction

**Technique 1: Incremental Extraction**

```python
async def extract_patterns_incremental(
    self,
    since: datetime
) -> List[InfoNeedPatternNode]:
    """
    Extract patterns only from new judgments since last run.

    Much faster than full extraction.
    """

    # Only load new judgments
    new_judgments = await self.memory_writer.query_recent_judgments(
        start_time=since
    )

    # Extract features
    for judgment in new_judgments:
        features = self.feature_extractor.extract_features(judgment.question_text)
        # ... update existing patterns or create new ones ...
```

**Technique 2: Parallel Feature Extraction**

```python
from concurrent.futures import ThreadPoolExecutor

def extract_patterns_parallel(
    self,
    judgments: List[InfoNeedJudgment],
    num_workers: int = 4
) -> List[InfoNeedPatternNode]:
    """Extract features in parallel."""

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        # Map: extract features for each judgment
        feature_futures = [
            executor.submit(self.feature_extractor.extract_features, j.question_text)
            for j in judgments
        ]

        # Gather results
        all_features = [f.result() for f in feature_futures]

    # Reduce: cluster and create patterns
    patterns = self.clusterer.cluster_by_signature(all_features)

    return patterns
```

---

## 8. Common Pitfalls

### 8.1 Classification Pitfalls

❌ **Pitfall**: Over-relying on LLM

```python
# Bad: Always call LLM
result = await self.llm.assess(question)
return result
```

✅ **Solution**: Use rule-based fast path

```python
# Good: Rule-based first, LLM only when needed
rule_signal = self.rule_filter.analyze(question)
if rule_signal.strength >= HIGH_CONFIDENCE_THRESHOLD:
    return self.make_decision_from_rules(rule_signal)
else:
    llm_conf = await self.llm.assess(question)
    return self.decision_matrix.decide(rule_signal, llm_conf)
```

---

❌ **Pitfall**: Not handling missing LLM

```python
# Bad: Assumes LLM is always available
llm_confidence = await self.llm.assess(question)
```

✅ **Solution**: Graceful degradation

```python
# Good: Fallback to rule-based decision
try:
    llm_confidence = await self.llm.assess(question)
except Exception as e:
    logger.warning(f"LLM unavailable: {e}, using rule-based fallback")
    llm_confidence = None

# Decision matrix handles None llm_confidence
```

---

### 8.2 Multi-Intent Pitfalls

❌ **Pitfall**: Splitting too aggressively

```python
# Bad: Split on every "and"
if "and" in question:
    return self.split(question)
```

✅ **Solution**: Validate split quality

```python
# Good: Check multiple criteria
if self._should_split(question):
    result = self.split(question)
    if self._validate_split(result):  # Check min length, substance, etc.
        return result
return []  # Don't split if uncertain
```

---

❌ **Pitfall**: Losing context

```python
# Bad: Split without tracking context
sub_questions = ["What time?", "What about him?"]  # "him" has no context
```

✅ **Solution**: Detect and mark context needs

```python
# Good: Mark context dependency
sub_questions = [
    SubQuestion(text="What time?", needs_context=False),
    SubQuestion(text="What about him?", needs_context=True, context_hint="pronoun_reference")
]
```

---

### 8.3 Pattern Learning Pitfalls

❌ **Pitfall**: Using LLM in feature extraction

```python
# Bad: Expensive and non-deterministic
features = await self.llm.extract_features(question)
```

✅ **Solution**: Rule-based feature extraction

```python
# Good: Fast and deterministic
features = {
    'has_time_sensitive': self._detect_time_keywords(question),
    'has_code_pattern': self._detect_code_patterns(question),
    'length': len(question),
}
```

---

❌ **Pitfall**: Not cleaning up low-quality patterns

```python
# Bad: Keep all patterns forever
await self.write_pattern(pattern)
```

✅ **Solution**: Cleanup based on quality

```python
# Good: Remove low-quality patterns
if pattern.occurrence_count < MIN_OCCURRENCES:
    await self.delete_pattern(pattern.pattern_id)
elif pattern.success_rate < MIN_SUCCESS_RATE:
    await self.deprecate_pattern(pattern.pattern_id)
else:
    await self.write_pattern(pattern)
```

---

### 8.4 Metrics Pitfalls

❌ **Pitfall**: Using LLM to evaluate quality

```python
# Bad: Asking LLM "was this answer good?"
quality = await self.llm.evaluate(answer)
```

✅ **Solution**: Use outcome-based metrics

```python
# Good: Based on user action
if user_used_communication:
    outcome = "validated"
elif user_corrected_system:
    outcome = "refuted"
else:
    outcome = "unnecessary"
```

---

❌ **Pitfall**: Not handling missing outcomes

```python
# Bad: Crashes if no outcomes
false_positive_rate = unnecessary / total_require_comm
```

✅ **Solution**: Handle edge cases

```python
# Good: Graceful handling
if total_require_comm == 0:
    false_positive_rate = 0.0
else:
    false_positive_rate = unnecessary / total_require_comm
```

---

## Conclusion

This developer guide covers the essentials for extending and maintaining the Evolvable System. Key takeaways:

1. **Follow Established Patterns**: Use existing code as templates
2. **Test Thoroughly**: Unit + integration + regression tests
3. **Optimize Carefully**: Measure before optimizing
4. **Learn from Reality**: Let outcomes drive improvements

For more information:
- Architecture: `docs/EVOLVABLE_SYSTEM_ARCHITECTURE.md`
- User Guide: `docs/EVOLVABLE_SYSTEM_USER_GUIDE.md`
- API Reference: Individual component documentation in `docs/`

---

**Document Version**: 1.0
**Last Updated**: 2026-01-31
**Feedback**: opensource@agentos.ai
