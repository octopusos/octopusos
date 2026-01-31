# Evolvable System Quick Reference Card

**Version**: 1.0 | **Date**: 2026-01-31 | **1-Page Reference**

---

## 🎯 Core Principle

> **"Don't evaluate whether answers are correct, only evaluate whether judgments are validated or refuted by reality"**

---

## 📊 Three Subsystems

| Subsystem | Purpose | Key Components |
|-----------|---------|----------------|
| **Quality Monitoring** 📊 | Track classification performance | Audit logs, 6 metrics, WebUI dashboard |
| **Memory System** 🧠 | Learn from experience | MemoryOS (30d), BrainOS (permanent), patterns |
| **Multi-Intent Processing** 🧩 | Handle composite questions | Splitter, context detection, parallel classification |

---

## 🔢 Six Core Metrics

| Metric | Formula | Target | Interpretation |
|--------|---------|--------|----------------|
| **Comm Trigger Rate** | `REQUIRE_COMM / total` | Monitor | External dependency level |
| **False Positive Rate** | `unnecessary / REQUIRE_COMM` | < 10% | Over-classification |
| **False Negative Rate** | `corrected / NOT_REQUIRE_COMM` | < 5% | Under-classification |
| **Ambient Hit Rate** | `validated / AMBIENT_STATE` | > 95% | System state accuracy |
| **Decision Latency** | `percentiles(latencies)` | p95 < 200ms | Performance |
| **Decision Stability** | `consistent / similar` | > 90% | Consistency |

---

## 🧠 Information Need Types (5)

| Type | Description | Example | Decision Action |
|------|-------------|---------|-----------------|
| **LOCAL_DETERMINISTIC** | Code/data analysis | "Where is ChatEngine class?" | DIRECT_ANSWER |
| **LOCAL_KNOWLEDGE** | General knowledge | "What is Python?" | DIRECT_ANSWER |
| **AMBIENT_STATE** | System state | "What time is it?" | LOCAL_CAPABILITY |
| **EXTERNAL_FACT_UNCERTAIN** | Needs verification | "Latest AI policy?" | REQUIRE_COMM |
| **OPINION_DISCUSSION** | Subjective | "Is microservices better?" | SUGGEST_COMM |

---

## 🛠️ Quick Commands

### View Metrics (CLI)
```bash
# Show recent metrics
agentos metrics show --last 7d

# Generate report
agentos metrics generate --output report.json --last 30d

# Export to CSV
agentos metrics export --format csv --last 90d
```

### Pattern Extraction (Scheduled Job)
```bash
# Run extraction (cron at 2 AM daily)
python -m agentos.jobs.info_need_pattern_extraction --days 7 --min-occurrences 5

# Dry-run (no writes)
python -m agentos.jobs.info_need_pattern_extraction --days 7 --dry-run
```

### Database Queries
```sql
-- Check recent classifications
SELECT COUNT(*) FROM task_audits
WHERE event_type = 'INFO_NEED_CLASSIFICATION'
AND timestamp > datetime('now', '-24 hours');

-- Check MemoryOS judgments
SELECT COUNT(*), outcome FROM info_need_judgments
GROUP BY outcome;

-- Check BrainOS patterns
SELECT COUNT(*) FROM info_need_patterns
WHERE success_rate > 0.8;
```

---

## 🔍 Quick Debugging

### Classification Issues
```python
# Inspect classification
result = await classifier.classify("Your question")
print(f"Type: {result.classified_type}")
print(f"Reasoning: {result.reasoning}")
print(f"Rule signals: {result.rule_signals}")

# Check MemoryOS history
judgments = await writer.query_recent_judgments(session_id="...")
for j in judgments:
    print(f"{j.question_text} → {j.outcome}")
```

### Multi-Intent Issues
```python
# Test splitting
splitter = MultiIntentSplitter()
print(f"Should split: {splitter.should_split(question)}")

# Inspect sub-questions
result = splitter.split(question)
for sq in result:
    print(f"[{sq.index}] {sq.text} (context: {sq.needs_context})")
```

### Pattern Issues
```bash
# Run extraction in dry-run mode
python -m agentos.jobs.info_need_pattern_extraction --dry-run

# Query low-performing patterns
SELECT pattern_signature, success_rate, occurrence_count
FROM info_need_patterns
WHERE success_rate < 0.5
ORDER BY occurrence_count DESC;
```

---

## 📁 Key File Locations

```
agentos/
├── core/
│   ├── audit.py                         # Audit logging
│   ├── chat/
│   │   ├── engine.py                    # Main orchestrator
│   │   ├── info_need_classifier.py      # Classification logic
│   │   └── multi_intent_splitter.py     # Intent splitting
│   ├── memory/
│   │   ├── schema.py                    # MemoryOS models
│   │   └── info_need_writer.py          # MemoryOS writer
│   └── brain/
│       ├── info_need_pattern_models.py  # Pattern models
│       ├── info_need_pattern_extractor.py # Feature extraction
│       └── info_need_pattern_writer.py  # BrainOS writer
├── metrics/
│   └── info_need_metrics.py             # Metrics calculator
├── jobs/
│   └── info_need_pattern_extraction.py  # Daily job
└── webui/
    ├── api/info_need_metrics.py         # Metrics API
    └── static/
        ├── js/views/InfoNeedMetricsView.js
        └── css/info-need-metrics.css
```

---

## 🧪 Quick Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific subsystem
pytest tests/unit/core/chat/test_info_need_classifier.py -v
pytest tests/unit/core/chat/test_multi_intent_splitter.py -v
pytest tests/unit/core/memory/test_info_need_writer.py -v
pytest tests/unit/core/brain/test_info_need_pattern_extractor.py -v
pytest tests/unit/metrics/test_info_need_metrics.py -v

# Run integration tests
pytest tests/integration/ -v

# Run with coverage
pytest tests/ --cov=agentos --cov-report=term-missing
```

---

## 🚀 Performance Targets

| Component | Target | Actual | Status |
|-----------|--------|--------|--------|
| Classification (p95) | < 200ms | ~150ms | ✅ |
| Splitting (avg) | < 5ms | 0.035ms | ✅ |
| Audit write | < 10ms | ~8ms | ✅ |
| MemoryOS query | < 50ms | ~40ms | ✅ |
| Pattern extraction (1000) | < 5s | ~4.2s | ✅ |
| Metrics calc (1000) | < 1s | ~0.8s | ✅ |

---

## 📖 API Quick Reference

### Classification
```python
from agentos.core.chat.info_need_classifier import InfoNeedClassifier

classifier = InfoNeedClassifier()
result = await classifier.classify(
    message="What is Python?",
    session_id="session-123",
    message_id="msg-456",
    phase="planning"
)
# Returns: ClassificationResult
```

### Multi-Intent Splitting
```python
from agentos.core.chat.multi_intent_splitter import MultiIntentSplitter

splitter = MultiIntentSplitter()
if splitter.should_split(question):
    sub_questions = splitter.split(question)
    # Returns: List[SubQuestion]
```

### MemoryOS
```python
from agentos.core.memory.info_need_writer import InfoNeedMemoryWriter

writer = InfoNeedMemoryWriter()

# Write judgment
await writer.write_judgment(classification_result, session_id, ...)

# Update outcome
await writer.update_judgment_outcome(judgment_id, outcome="validated")

# Query
judgments = await writer.query_recent_judgments(
    session_id="...",
    time_range="7d"
)
```

### BrainOS
```python
from agentos.core.brain.info_need_pattern_writer import InfoNeedPatternWriter

writer = InfoNeedPatternWriter()

# Query patterns
patterns = await writer.query_patterns(
    classification_type="external_fact_uncertain",
    min_success_rate=0.8
)

# Track evolution
await writer.evolve_pattern(
    old_pattern_id="...",
    new_pattern=...,
    evolution_type="refined"
)
```

### Metrics
```python
from agentos.metrics.info_need_metrics import InfoNeedMetrics

metrics = InfoNeedMetrics()
report = metrics.calculate_metrics(
    start_time="2026-01-01",
    end_time="2026-01-31"
)
# Returns: Dict with 6 core metrics
```

---

## 🔧 Configuration

### Environment Variables
```bash
# Database path
export AGENTOS_DB_PATH="store/registry.sqlite"

# LLM endpoint (for classification)
export OLLAMA_URL="http://localhost:11434"

# WebUI port
export WEBUI_PORT=5000
```

### Config Files
```python
# agentos/config/info_need.yaml
classification:
  high_confidence_threshold: 0.8
  low_confidence_threshold: 0.4

multi_intent:
  min_length: 3
  max_splits: 3
  enable_context: true

pattern_extraction:
  min_occurrences: 5
  min_success_rate: 0.6
  time_window_days: 7

memory:
  ttl_days: 30
  cleanup_frequency: "daily"
```

---

## 🚨 Troubleshooting

| Issue | Solution |
|-------|----------|
| Classification slow | Check LLM availability, verify rule-based fast path working |
| MemoryOS not writing | Check logs for exceptions, verify database permissions |
| Pattern extraction fails | Run with `--dry-run`, check MemoryOS has data |
| Dashboard not loading | Verify API endpoint, check browser console for errors |
| Multi-intent not splitting | Verify question meets min_length, check splitting rules |

---

## 📚 Documentation

- **Final Acceptance Report**: `EVOLVABLE_SYSTEM_FINAL_ACCEPTANCE_REPORT.md`
- **Architecture Guide**: `docs/EVOLVABLE_SYSTEM_ARCHITECTURE.md`
- **Developer Guide**: `docs/EVOLVABLE_SYSTEM_DEVELOPER_GUIDE.md`
- **Operations Guide**: `docs/EVOLVABLE_SYSTEM_OPERATIONS_GUIDE.md`
- **User Guide**: `docs/EVOLVABLE_SYSTEM_USER_GUIDE.md`

---

## ✅ Deployment Checklist

- [ ] Run all tests (`pytest tests/ -v`)
- [ ] Run database migrations (v38, v39)
- [ ] Configure scheduled job (cron at 2 AM)
- [ ] Verify WebUI dashboard accessible
- [ ] Check logs for errors (first 24 hours)
- [ ] Monitor MemoryOS write success rate
- [ ] Verify pattern extraction runs successfully
- [ ] Review metrics (7-day trend)

---

**For full documentation, see**: `docs/EVOLVABLE_SYSTEM_FINAL_ACCEPTANCE_REPORT.md`

**Support**: opensource@agentos.ai | **License**: See LICENSE file
