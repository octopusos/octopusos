# InfoNeed Metrics Quick Reference

## 🎯 Core Metrics (6)

| Metric | Formula | Interpretation | Target |
|--------|---------|----------------|--------|
| **Comm Trigger Rate** | `REQUIRE_COMM / total` | How often comm is triggered | 20-30% |
| **False Positive Rate** | `unnecessary_comm / REQUIRE_COMM` | Unnecessary comm requests | <5% |
| **False Negative Rate** | `user_corrected / NOT REQUIRE_COMM` | Missed comm opportunities | <5% |
| **Ambient Hit Rate** | `validated / AMBIENT_STATE` | Ambient state accuracy | >80% |
| **Decision Latency** | `percentile(latencies)` | Performance metrics | p50 <100ms |
| **Decision Stability** | `consistent / similar questions` | Decision consistency | >80% |

## 🚀 Quick Start

### Python API
```python
from agentos.metrics.info_need_metrics import InfoNeedMetrics

calculator = InfoNeedMetrics()
metrics = calculator.calculate_metrics()

print(f"Comm Trigger Rate: {metrics['comm_trigger_rate']:.2%}")
print(f"False Positive Rate: {metrics['false_positive_rate']:.2%}")
```

### CLI
```bash
# Show metrics for last 24h
python -m agentos.cli.metrics show

# Show metrics for last 7 days
python -m agentos.cli.metrics show --last 7d

# Generate JSON report
python -m agentos.cli.metrics generate --output report.json

# Export CSV
python -m agentos.cli.metrics export --format csv --output metrics.csv
```

## 📊 Audit Events

### Classification Event
```json
{
  "event_type": "info_need_classification",
  "payload": {
    "message_id": "msg_123",
    "question": "What is the latest Python version?",
    "decision": "REQUIRE_COMM",
    "classified_type": "external_fact_uncertain",
    "confidence_level": "low",
    "latency_ms": 150.5
  }
}
```

### Outcome Event
```json
{
  "event_type": "info_need_outcome",
  "payload": {
    "message_id": "msg_123",
    "outcome": "validated"
  }
}
```

**Outcome Types:**
- `validated`: Classification was correct
- `unnecessary_comm`: False positive
- `user_corrected`: False negative
- `user_cancelled`: User cancelled action

## 📝 Integration Example

```python
from agentos.core.audit import log_audit_event
from agentos.core.chat.info_need_classifier import InfoNeedClassifier

# Classify question
classifier = InfoNeedClassifier()
result = classifier.classify("What is the latest Python version?")

# Log classification
log_audit_event(
    event_type="info_need_classification",
    task_id=task_id,
    metadata={
        "message_id": message_id,
        "question": question,
        "decision": result.decision_action.value,
        "classified_type": result.info_need_type.value,
        "confidence_level": result.confidence_level.value,
        "latency_ms": latency_ms,
    }
)

# Log outcome after user feedback
log_audit_event(
    event_type="info_need_outcome",
    task_id=task_id,
    metadata={
        "message_id": message_id,
        "outcome": "validated",
    }
)
```

## ⏰ Scheduled Jobs

### Cron (Daily Report)
```bash
# Add to crontab
0 2 * * * cd /path/to/agentos && \
  python -m agentos.cli.metrics generate \
  --last 24h \
  --output /var/log/metrics/daily_$(date +\%Y\%m\%d).json
```

### Systemd Timer
```ini
# /etc/systemd/system/agentos-metrics.service
[Unit]
Description=AgentOS InfoNeed Metrics Report

[Service]
Type=oneshot
ExecStart=/usr/bin/python -m agentos.cli.metrics generate --last 24h --output /var/log/metrics/daily_report.json
WorkingDirectory=/opt/agentos
User=agentos
```

```ini
# /etc/systemd/system/agentos-metrics.timer
[Unit]
Description=Daily AgentOS Metrics

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
```

## 🧪 Testing

```bash
# Run all metrics tests
pytest tests/unit/metrics/

# Run specific test file
pytest tests/unit/metrics/test_info_need_metrics.py

# Run with coverage
pytest tests/unit/metrics/ --cov=agentos.metrics --cov-report=html
```

## 📂 Files

```
agentos/metrics/
├── __init__.py
├── info_need_metrics.py       # Core calculator
└── README.md                   # Full documentation

agentos/cli/
└── metrics.py                  # CLI interface

tests/unit/metrics/
├── __init__.py
└── test_info_need_metrics.py  # Unit tests

examples/
└── info_need_metrics_demo.py  # Demo script
```

## 🎨 Example Output

```
======================================================================
InfoNeed Classification Quality Metrics
======================================================================

Period: 2025-01-30T10:00:00+00:00 to 2025-01-31T10:00:00+00:00
Total Classifications: 150
Total Outcomes: 120

Core Metrics:
  Comm Trigger Rate:     25.00%
  False Positive Rate:   8.00%
  False Negative Rate:   5.00%
  Ambient Hit Rate:      85.00%
  Decision Stability:    82.00%

Decision Latency:
  P50: 95.0ms
  P95: 350.0ms
  P99: 520.0ms
  Avg: 125.5ms

Breakdown by Type:
  local_knowledge                :  60 (40.0%) - avg 80.0ms
  external_fact_uncertain        :  40 (26.7%) - avg 200.0ms
  AMBIENT_STATE                  :  30 (20.0%) - avg 100.0ms
  opinion                        :  20 (13.3%) - avg 150.0ms

Outcome Distribution:
  validated                      :  90
  unnecessary_comm               :  10
  user_corrected                 :   8
  user_cancelled                 :  12

======================================================================
```

## 🔗 Related

- Full Documentation: `agentos/metrics/README.md`
- Implementation Summary: `INFO_NEED_METRICS_IMPLEMENTATION_SUMMARY.md`
- InfoNeed Classifier: `agentos/core/chat/info_need_classifier.py`
- Audit System: `agentos/core/audit.py`

## ⚡ Key Features

- ✅ Pure statistical calculations (no LLM)
- ✅ Audit log only (no external dependencies)
- ✅ Offline capable (batch job friendly)
- ✅ Time range filtering support
- ✅ Comprehensive error handling
- ✅ Multiple export formats (JSON, CSV)
- ✅ 14 unit tests (all passing)

## 📌 Status

**Implementation**: ✅ COMPLETE
**Tests**: ✅ 14/14 PASSING
**Documentation**: ✅ COMPLETE
**Ready for**: Task #21 (WebUI Dashboard) and Task #19 (Audit Integration)
