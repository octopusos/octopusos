# Blind Spot Detection - Quick Reference

## TL;DR

Blind Spot Detection identifies "I know that I don't know" - critical gaps in understanding within the BrainOS knowledge graph.

**Performance**: ~4ms for 12k entities | **Types**: 3 | **Tests**: 13/13 ✅

## Quick Start

### Import and Use
```python
from agentos.core.brain.service import detect_blind_spots
from agentos.core.brain.store import SQLiteStore

store = SQLiteStore("./brainos.db")
store.connect()

report = detect_blind_spots(store, high_fan_in_threshold=5, max_results=50)

print(f"Total blind spots: {report.total_blind_spots}")
print(f"High severity: {report.by_severity['high']}")

store.close()
```

### Run Demo
```bash
python3 demo_blind_spot.py
```

### Run Tests
```bash
python3 -m pytest tests/unit/core/brain/test_blind_spot.py -v
```

### Run Benchmark
```bash
python3 benchmark_blind_spot.py
```

## 3 Types of Blind Spots

### Type 1: High Fan-In Undocumented
**What**: Files with many dependents but no documentation
**Why Critical**: Architectural bottlenecks without rationale
**Severity**: `min(1.0, fan_in / 20)`
**Example**: `Button.tsx` with 15 dependents, 0 docs → severity 0.75

### Type 2: Capability Without Implementation
**What**: Declared capabilities with no code implementation
**Why Critical**: Gap between claims and reality
**Severity**: Fixed 0.8 (high)
**Example**: `capability:governance` declared but no implementation

### Type 3: Trace Discontinuity
**What**: Files with git history but no documented evolution
**Why Critical**: Changes without design rationale
**Severity**: `min(1.0, commits / 10)`
**Example**: File with 5 commits but 0 docs → severity 0.5

## Data Structures

### BlindSpotType
```python
class BlindSpotType(Enum):
    HIGH_FAN_IN_UNDOCUMENTED = "high_fan_in_undocumented"
    CAPABILITY_NO_IMPLEMENTATION = "capability_no_implementation"
    TRACE_DISCONTINUITY = "trace_discontinuity"
```

### BlindSpot
```python
@dataclass
class BlindSpot:
    entity_type: str          # 'file', 'capability'
    entity_key: str           # Unique key
    entity_name: str          # Display name
    blind_spot_type: BlindSpotType
    severity: float           # 0.0-1.0
    reason: str               # Human-readable explanation
    metrics: Dict[str, int]   # Metrics (fan_in, commits, etc.)
    suggested_action: str     # Actionable recommendation
    detected_at: str          # ISO timestamp
```

### BlindSpotReport
```python
@dataclass
class BlindSpotReport:
    total_blind_spots: int
    by_type: Dict[BlindSpotType, int]
    by_severity: Dict[str, int]  # {"high": 5, "medium": 10, "low": 15}
    blind_spots: List[BlindSpot]  # Sorted by severity (descending)
    graph_version: str
    computed_at: str
```

## Core Functions

### `detect_blind_spots(store, high_fan_in_threshold=5, max_results=50)`
Main entry point. Runs all 3 detection types and returns unified report.

**Parameters**:
- `store`: SQLiteStore instance
- `high_fan_in_threshold`: Min fan-in for Type 1 (default: 5)
- `max_results`: Max blind spots to return (default: 50)

**Returns**: `BlindSpotReport`

### `calculate_severity(blind_spot_type, metrics)`
Calculate severity (0-1) based on type and metrics.

**Type 1**: `min(1.0, fan_in_count / 20)`
**Type 2**: Fixed `0.8`
**Type 3**: `min(1.0, commit_count / 10)`

## Severity Categories

- **HIGH** (≥0.7): Urgent attention required
- **MEDIUM** (0.4-0.7): Should be addressed
- **LOW** (<0.4): Nice to have

## Real-World Results (AgentOS)

**Database**: v0.1_mvp.db (12,729 entities, 62,255 edges)

**Detection Results**:
```
Total: 17 blind spots
Type 1: 4 (high fan-in undocumented)
Type 2: 13 (capabilities without implementation)
Type 3: 0 (trace discontinuities)

Severity:
  HIGH: 14
  MEDIUM: 1
  LOW: 2
```

**Top Blind Spots**:
1. 🔴 HIGH (0.80) - `capability:governance` (no implementation)
2. 🔴 HIGH (0.80) - `capability:execution gate` (no implementation)
3. 🔴 HIGH (0.75) - `Button.tsx` (15 dependents, no docs)
4. 🟡 MEDIUM (0.40) - `Router.py` (8 dependents, no docs)

## Performance

**Timing** (12k entities):
- Type 1: ~4ms
- Type 2: ~0.5ms
- Type 3: ~0.2ms
- **Total: ~4ms**

**Throughput**: 3.3M entities/sec

**Scalability**:
- 100k entities: ~30ms
- 1M entities: ~0.3s

**Memory**: ~8 KB for 17 blind spots

## Common Patterns

### Iterate Through Blind Spots
```python
for bs in report.blind_spots:
    print(f"{bs.severity:.2f} - {bs.entity_name}")
    print(f"  Type: {bs.blind_spot_type.value}")
    print(f"  Reason: {bs.reason}")
    print(f"  Action: {bs.suggested_action}")
```

### Filter by Type
```python
high_fan_in = [
    bs for bs in report.blind_spots
    if bs.blind_spot_type == BlindSpotType.HIGH_FAN_IN_UNDOCUMENTED
]
```

### Filter by Severity
```python
critical = [bs for bs in report.blind_spots if bs.severity >= 0.7]
```

### Export to JSON
```python
import json
report_dict = report.to_dict()
json.dump(report_dict, open("blind_spots.json", "w"), indent=2)
```

## Suggested Actions by Type

### Type 1: High Fan-In Undocumented
```
→ Add ADR explaining architectural decision
→ Add design doc describing purpose
→ Add inline comments for complex logic
```

### Type 2: Capability Without Implementation
```
→ Add implementation file
→ Remove orphaned capability declaration
→ Create GitHub issue to track implementation
```

### Type 3: Trace Discontinuity
```
→ Add ADR documenting evolution
→ Improve commit messages (explain WHY)
→ Add changelog entry
```

## Integration Examples

### CLI Tool
```python
def cli_blind_spots(db_path: str):
    store = SQLiteStore(db_path)
    store.connect()

    report = detect_blind_spots(store)

    print(f"Found {report.total_blind_spots} blind spots:")
    for bs in report.blind_spots[:10]:
        print(f"  {bs.severity:.2f} - {bs.entity_name}")

    store.close()
```

### WebUI Integration
```python
@app.route('/api/brain/blind-spots')
def api_blind_spots():
    store = SQLiteStore(get_db_path())
    store.connect()

    report = detect_blind_spots(store, max_results=20)

    store.close()

    return jsonify(report.to_dict())
```

### Continuous Monitoring
```python
def monitor_blind_spots():
    store = SQLiteStore("brainos.db")
    store.connect()

    report = detect_blind_spots(store)

    # Alert on high severity
    high_severity = [bs for bs in report.blind_spots if bs.severity >= 0.7]
    if len(high_severity) > 10:
        send_alert(f"High blind spot count: {len(high_severity)}")

    store.close()
```

## Testing

### Unit Tests
```bash
# Run all tests
pytest tests/unit/core/brain/test_blind_spot.py -v

# Run specific test
pytest tests/unit/core/brain/test_blind_spot.py::TestBlindSpotDetection::test_detect_high_fan_in_undocumented -v
```

### Test Coverage
- ✅ Type 1 detection (with/without docs)
- ✅ Type 2 detection (with/without implementation)
- ✅ Type 3 detection (with/without docs)
- ✅ Severity calculation (all types)
- ✅ Report generation and serialization
- ✅ Max results limiting
- ✅ Severity categorization

## Files

```
agentos/core/brain/service/blind_spot.py          # Main implementation (600+ lines)
tests/unit/core/brain/test_blind_spot.py          # Unit tests (13 tests)
demo_blind_spot.py                                 # Demo script
benchmark_blind_spot.py                            # Performance benchmark
P1_A_TASK2_BLIND_SPOT_COMPLETION.md              # Full completion report
BLIND_SPOT_QUICK_REFERENCE.md                     # This file
```

## Troubleshooting

### "No blind spots detected"
- ✅ Good! Your knowledge graph is well-documented
- Check if threshold is too high: try `high_fan_in_threshold=3`

### "Too many blind spots"
- Increase threshold: `high_fan_in_threshold=10`
- Limit results: `max_results=20`
- Focus on high severity: `[bs for bs in report.blind_spots if bs.severity >= 0.7]`

### Performance issues
- Check database size: `store.get_stats()`
- Ensure SQLite indexes exist
- Consider running detection asynchronously

## Next Steps

1. **WebUI Integration**: Add blind spot view to dashboard
2. **Automated Fixes**: Generate documentation templates
3. **Continuous Monitoring**: Track blind spot trends over time
4. **Extended Detection**: Add Type 4 (test coverage gaps)

## References

- **Implementation**: `agentos/core/brain/service/blind_spot.py`
- **Tests**: `tests/unit/core/brain/test_blind_spot.py`
- **Full Report**: `P1_A_TASK2_BLIND_SPOT_COMPLETION.md`
