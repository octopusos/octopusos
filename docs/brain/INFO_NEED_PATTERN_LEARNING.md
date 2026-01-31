# InfoNeed Pattern Learning System

## Overview

The InfoNeed Pattern Learning System implements a dual-memory architecture for improving question classification over time:

- **MemoryOS (Short-term)**: Stores individual classification judgments for 30 days
- **BrainOS (Long-term)**: Stores extracted patterns permanently for system evolution

## Core Principle

**"Remember HOW we judge, not WHAT we know"**

✅ Store:
- Decision patterns and rule effectiveness
- Question features → Classification type mappings
- Confidence evolution and decision stability
- Pattern success rates and evolution history

❌ Don't Store:
- External facts or content
- Semantic analysis or embeddings
- Specific answer content

## Architecture

```
┌─────────────────┐
│   User Query    │
└────────┬────────┘
         │
         v
┌─────────────────────────────┐
│   InfoNeedClassifier        │
│   - Rule-based filtering    │
│   - LLM self-assessment     │
│   - Decision matrix         │
└────────┬────────────────────┘
         │ (Classification Result)
         v
┌─────────────────────────────┐
│   MemoryOS Writer           │
│   - Store judgment          │
│   - Record outcome          │
│   - TTL: 30 days            │
└────────┬────────────────────┘
         │
         │ (Daily Job)
         v
┌─────────────────────────────┐
│   Pattern Extractor         │
│   - Query judgments (7d)    │
│   - Extract features        │
│   - Cluster by similarity   │
│   - Calculate statistics    │
└────────┬────────────────────┘
         │
         v
┌─────────────────────────────┐
│   BrainOS Writer            │
│   - Write/update patterns   │
│   - Track evolution         │
│   - No expiration           │
└─────────────────────────────┘
```

## Data Models

### InfoNeedPatternNode

Long-term pattern representing learned decision patterns:

```python
{
    "pattern_id": "uuid",
    "pattern_type": "question_keyword_pattern",
    "question_features": {
        "has_time_keywords": true,
        "has_policy_keywords": false,
        "length": 42,
        "signature": "TIME|MEDIUM"
    },
    "classification_type": "external_fact_uncertain",
    "confidence_level": "low",
    "occurrence_count": 150,
    "success_count": 120,
    "failure_count": 30,
    "success_rate": 0.8,
    "avg_confidence_score": 0.75,
    "avg_latency_ms": 45.0,
    "pattern_version": 3
}
```

### DecisionSignalNode

Atomic decision signals:

```python
{
    "signal_id": "uuid",
    "signal_type": "keyword",
    "signal_value": "latest",
    "effectiveness_score": 0.85,
    "true_positive_count": 100,
    "false_positive_count": 15
}
```

### PatternEvolutionEdge

Pattern evolution history:

```python
{
    "evolution_id": "uuid",
    "from_pattern_id": "old-pattern-id",
    "to_pattern_id": "new-pattern-id",
    "evolution_type": "refined",
    "reason": "Adjusted weights to improve accuracy",
    "timestamp": "2026-01-31T12:00:00Z"
}
```

## Feature Extraction

Features are extracted using **rule-based methods only** (no LLM or embeddings):

### Keyword Matching

- **Time keywords**: "latest", "current", "now", "2026"
- **Policy keywords**: "official", "regulation", "standard"
- **Tech keywords**: "API", "function", "class"
- **State keywords**: "status", "running", "config"
- **Opinion keywords**: "recommend", "suggest", "should"

### Structural Features

- Question length (short/medium/long)
- Word count
- Interrogative words ("what", "how", "why")
- Code patterns (regex for class/function/file patterns)

### Feature Signature

A string encoding the feature vector for clustering:

```
"TIME|POLICY|MEDIUM|Q:WHAT"
```

## Pattern Extraction Process

### 1. Query Recent Judgments

```python
judgments = await memory_writer.query_recent_judgments(
    time_range="7d",  # Last 7 days
    limit=10000
)
```

### 2. Extract Features

```python
features = feature_extractor.extract_features(
    question="What is the latest Python version?"
)
# Returns: {"has_time_keywords": True, "signature": "TIME|MEDIUM", ...}
```

### 3. Cluster by Signature

```python
clusters = clusterer.cluster_judgments(judgments, features_list)
# Groups judgments with identical signatures
```

### 4. Generate Patterns

```python
pattern = generate_pattern_from_cluster(signature, cluster_items)
# Calculates statistics: occurrence_count, success_rate, etc.
```

### 5. Write to BrainOS

```python
await writer.write_pattern(pattern)
```

## Pattern Evolution

Patterns evolve through four mechanisms:

### 1. Refined

Adjust feature weights or thresholds:

```python
await writer.evolve_pattern(
    old_pattern_id="pat-123",
    new_pattern=refined_pattern,
    evolution_type="refined",
    reason="Adjusted confidence threshold based on user feedback"
)
```

### 2. Split

One pattern splits into multiple sub-patterns:

```python
# Old: "TIME|MEDIUM" → New: "TIME|SHORT" + "TIME|LONG"
```

### 3. Merged

Multiple patterns merge into one:

```python
# Old: "TECH|SHORT" + "TECH|MEDIUM" → New: "TECH|ANY"
```

### 4. Deprecated

Pattern becomes ineffective:

```python
# success_rate < 0.3 → deprecated
```

## Daily Pattern Extraction Job

### Configuration

```python
job = PatternExtractionJob(
    brain_db_path="/path/to/brain.db",
    time_window_days=7,         # Look back 7 days
    min_occurrences=5,          # Min 5 occurrences for pattern
    min_success_rate=0.3,       # Min 30% success rate
    dry_run=False               # Actually make changes
)
```

### Execution

```python
stats = await job.run()

# Returns:
{
    "status": "completed",
    "patterns_extracted": 15,
    "patterns_written": 10,
    "patterns_updated": 5,
    "patterns_cleaned": 2
}
```

### Scheduling

Recommended: Daily at 2 AM (low traffic)

```bash
# Cron job
0 2 * * * python -m agentos.jobs.info_need_pattern_extraction
```

## API Usage

### Extract Patterns

```python
from agentos.core.brain.info_need_pattern_extractor import InfoNeedPatternExtractor

extractor = InfoNeedPatternExtractor()

patterns = await extractor.extract_patterns(
    time_window=timedelta(days=7),
    min_occurrences=5
)

for pattern in patterns:
    print(f"Pattern: {pattern.classification_type}")
    print(f"Success rate: {pattern.success_rate:.2%}")
    print(f"Occurrences: {pattern.occurrence_count}")
```

### Write Patterns

```python
from agentos.core.brain.info_need_pattern_writer import InfoNeedPatternWriter

writer = InfoNeedPatternWriter()

# Write new pattern
pattern_id = await writer.write_pattern(pattern)

# Update statistics
await writer.update_pattern_statistics(
    pattern_id=pattern_id,
    success=True,
    confidence_score=0.9,
    latency_ms=50.0
)
```

### Query Patterns

```python
# Query by criteria
patterns = await writer.query_patterns(
    classification_type="external_fact_uncertain",
    min_confidence=0.7,
    min_occurrences=10,
    min_success_rate=0.8
)

# Get specific pattern
pattern = await writer.get_pattern_by_id(pattern_id)
```

### Track Evolution

```python
# Record evolution
new_id = await writer.evolve_pattern(
    old_pattern_id="old-123",
    new_pattern=refined_pattern,
    evolution_type="refined",
    reason="Improved accuracy based on recent data"
)
```

## Database Schema

See `schema_v39_info_need_patterns.sql` for complete schema.

Key tables:
- `info_need_patterns`: Pattern nodes
- `decision_signals`: Decision signals
- `pattern_signal_links`: Pattern-signal relationships
- `pattern_evolution`: Evolution history

## Performance Considerations

### Feature Extraction

- **Target**: < 10ms per question
- **Method**: Rule-based (no LLM/embeddings)
- **Cached**: Keyword sets in memory

### Pattern Extraction

- **Frequency**: Daily (not real-time)
- **Batch size**: 10,000 judgments max
- **Time window**: 7 days recommended

### BrainOS Queries

- **Indexed**: All query fields
- **Limit**: 100-1000 patterns typical
- **Cache**: Consider query result caching

## Monitoring

Track these metrics:

1. **Pattern Quality**
   - Success rate distribution
   - Coverage (% queries matched by patterns)
   - Evolution frequency

2. **Extraction Performance**
   - Job duration
   - Patterns extracted per run
   - Error rate

3. **Storage**
   - Total patterns
   - Pattern growth rate
   - Low-quality pattern cleanup rate

## Future Enhancements

1. **Adaptive Thresholds**: Auto-adjust min_occurrences based on traffic
2. **Pattern Merging**: Automatically merge similar patterns
3. **Multi-Signal Patterns**: Combine multiple signal types
4. **Feedback Loop**: Use patterns to pre-filter in classifier
5. **Cross-Session Learning**: Learn from global patterns

## References

- InfoNeedClassifier: `/agentos/core/chat/info_need_classifier.py`
- MemoryOS Writer: `/agentos/core/memory/info_need_writer.py`
- Pattern Models: `/agentos/core/brain/info_need_pattern_models.py`
- Pattern Extractor: `/agentos/core/brain/info_need_pattern_extractor.py`
- Pattern Writer: `/agentos/core/brain/info_need_pattern_writer.py`
- Migration SQL: `/agentos/store/migrations/schema_v39_info_need_patterns.sql`
