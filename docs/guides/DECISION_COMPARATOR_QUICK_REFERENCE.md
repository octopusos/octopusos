# Decision Comparator - Quick Reference Guide

## What Is It?

The **Decision Comparator** generates comparison metrics between active and shadow classifier versions to help humans evaluate which shadow version is worth migrating to production.

## Quick Start

```python
from agentos.core.chat.decision_comparator import get_comparator

# Get singleton instance
comparator = get_comparator()

# Compare versions
result = comparator.compare_versions(
    active_version="v1",
    shadow_version="v2-shadow-a"
)

# Check key metrics
print(f"Sample count: {result['comparison']['sample_count']}")
print(f"Divergence rate: {result['comparison']['divergence_rate']:.2%}")
print(f"Improvement rate: {result['comparison']['improvement_rate']:.2%}")
```

## Key Features

✅ **Version Comparison**: Compare active vs shadow decisions
✅ **Multi-dimensional Filtering**: By session, time, info_need_type
✅ **Aggregation**: Group by info_need_type or compare multiple shadows
✅ **Improvement Metrics**: Calculate improvement rates from scores
✅ **Distribution Analysis**: Decision and info need distributions

## Run the Demo

```bash
python3 examples/decision_comparator_demo.py
```

Output shows:
1. Basic version comparison
2. Multi-shadow ranking
3. Grouped comparison by info need type
4. Filtered comparison with time range

## Run Tests

```bash
# All tests (26 tests, 100% passing)
python3 -m pytest tests/unit/core/chat/test_decision_comparator.py tests/integration/chat/test_decision_comparator_e2e.py -v
```

## API Methods

### `compare_versions(active, shadow, **filters)`
Compare two versions with optional filters.

### `compare_by_info_need_type(active, shadow, **filters)`
Compare versions grouped by info need type.

### `get_summary_statistics(active, shadows, **filters)`
Compare one active to multiple shadows, ranked by improvement.

## Key Metrics

- **Divergence Rate**: % of decisions where active and shadow disagree
- **Improvement Rate**: % improvement in Reality Alignment Score
- **Better/Worse/Neutral**: Count of shadow performance vs active

## Documentation

- [Full Acceptance Report](./TASK_5_DECISION_COMPARATOR_ACCEPTANCE_REPORT.md)
- [Demo Script](./examples/decision_comparator_demo.py)

## Status

✅ **Complete** - Ready for production use
