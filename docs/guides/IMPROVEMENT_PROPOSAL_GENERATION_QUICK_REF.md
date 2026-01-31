# Improvement Proposal Generation - Quick Reference

## Overview
Daily BrainOS job that analyzes shadow vs active classifier performance and generates improvement proposals for human review.

---

## Quick Start

### Run Manually (Dry Run)
```bash
python3 -m agentos.jobs.improvement_proposal_generation \
  --shadow=v2-shadow-a \
  --dry-run
```

### Run in Production
```bash
python3 -m agentos.jobs.improvement_proposal_generation \
  --active=v1 \
  --shadow=v2-shadow-a \
  --shadow=v2-shadow-b \
  --time-window=7
```

### Run via Cron (Daily at 2 AM)
```cron
0 2 * * * cd /path/to/AgentOS && python3 -m agentos.jobs.improvement_proposal_generation --active=v1 --shadow=v2-shadow-a
```

---

## Risk Assessment

### LOW Risk → PROMOTE
- ≥100 samples
- ≥15% improvement
- High confidence
- **Saved to database**

### MEDIUM Risk → TEST
- ≥50 samples
- ≥10% improvement
- Moderate confidence
- **Saved to database**

### HIGH Risk → DEFER
- <50 samples or <10% improvement
- **Filtered (not saved)**

---

## CLI Arguments

```bash
--active=VERSION_ID         # Active classifier version (default: v1)
--shadow=VERSION_ID         # Shadow version to analyze (repeatable)
--time-window=DAYS          # Analysis time window (default: 7)
--dry-run                   # Don't save proposals (testing)
```

---

## Programmatic Usage

```python
from agentos.jobs.improvement_proposal_generation import (
    run_improvement_proposal_generation
)

stats = await run_improvement_proposal_generation(
    time_window_days=7,
    active_version="v1",
    shadow_versions=["v2-shadow-a"],
    dry_run=False,
)

print(f"Generated {stats['proposals_generated']} proposals")
print(f"  LOW: {stats['proposals_low_risk']}")
print(f"  MEDIUM: {stats['proposals_medium_risk']}")
print(f"  HIGH (filtered): {stats['proposals_high_risk_filtered']}")
```

---

## Output Statistics

```python
{
    "status": "completed",
    "shadow_versions_analyzed": 2,
    "proposals_generated": 5,
    "proposals_low_risk": 3,
    "proposals_medium_risk": 2,
    "proposals_high_risk_filtered": 1,
    "error": None,
}
```

---

## Proposal Structure

```json
{
  "proposal_id": "BP-XXXXXX",
  "scope": "LOCAL_KNOWLEDGE",
  "change_type": "promote_shadow",
  "evidence": {
    "samples": 100,
    "improvement_rate": 0.18,
    "shadow_accuracy": 0.92,
    "active_accuracy": 0.78,
    "risk": "LOW",
    "confidence_score": 0.95
  },
  "recommendation": "Promote to v2",
  "status": "pending"
}
```

---

## Integration Points

### Inputs
- **Shadow Evaluator** (Task #4): Reality Alignment Scores
- **Decision Comparator** (Task #5): Performance metrics
- **Audit Log** (Task #3): Decision history

### Outputs
- **ImprovementProposal** (Task #7): Proposal objects
- **Review Queue API** (Task #9): Human review interface

---

## Monitoring

### Key Metrics
- Proposals generated per run
- LOW/MEDIUM risk ratio
- HIGH risk filtered count
- Job execution time
- Database write success rate

### Alert Conditions
- Job fails 3+ times in a row
- Zero proposals for 7+ days
- Database write failures >10%

---

## Troubleshooting

### No Proposals Generated
**Cause**: Insufficient data or no improvements
**Fix**: Check if decision sets exist, verify shadow is running

### All Proposals Filtered (HIGH risk)
**Cause**: Low sample count or marginal improvements
**Fix**: Increase time window or wait for more data

### Database Write Failures
**Cause**: Missing tables or schema mismatch
**Fix**: Run database migrations, check schema_v41

### DecisionComparator Warnings
**Cause**: No decision sets found for shadow version
**Fix**: Verify shadow classifier is registered and running

---

## Best Practices

### 1. Schedule Daily
Run at low-traffic time (2-4 AM)

### 2. Monitor Output
Track proposals_generated trend

### 3. Test First
Always dry-run after config changes

### 4. Review Regularly
Check pending proposals weekly

### 5. Adjust Thresholds
Tune risk thresholds based on domain

---

## File Locations

```
agentos/jobs/
  └── improvement_proposal_generation.py   # Main job

tests/integration/jobs/
  ├── test_improvement_proposal_generation_e2e.py
  └── test_简化版_proposal_generation.py
```

---

## Dependencies

- Python 3.13+
- SQLite database
- Shadow classifiers registered
- Decision audit logs present

---

## Support

**Documentation**: `/docs/brain/IMPROVEMENT_PROPOSAL_GENERATION.md`
**Tests**: `/tests/integration/jobs/test_*proposal_generation*.py`
**Acceptance Report**: `/IMPROVEMENT_PROPOSAL_GENERATION_ACCEPTANCE_REPORT.md`

---

*Last Updated: 2026-01-31*
*Version: 1.0*
*Status: Production Ready ✅*
