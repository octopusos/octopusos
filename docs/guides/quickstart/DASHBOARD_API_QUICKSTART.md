# Governance Dashboard API - Quick Start Guide

## TL;DR

```bash
# Start WebUI
python -m agentos.webui.app

# Get dashboard data
curl http://localhost:8080/api/governance/dashboard?timeframe=7d
```

## API Endpoint

```
GET /api/governance/dashboard
```

### Parameters

- `timeframe`: `7d` (default), `30d`, or `90d`
- `project_id`: Optional project filter

### Example Responses

**Healthy System**:
```json
{
  "metrics": {
    "risk_level": "LOW",
    "open_findings": 2,
    "blocked_rate": 0.05,
    "guarded_percentage": 0.95
  }
}
```

**At-Risk System**:
```json
{
  "metrics": {
    "risk_level": "HIGH",
    "open_findings": 15,
    "blocked_rate": 0.25,
    "guarded_percentage": 0.60
  }
}
```

## Response Fields

### Metrics

| Field | Type | Range | Meaning |
|-------|------|-------|---------|
| `risk_level` | string | CRITICAL/HIGH/MEDIUM/LOW | Overall system risk |
| `open_findings` | int | 0+ | Findings without follow-up tasks |
| `blocked_rate` | float | 0.0-1.0 | % of decisions blocked |
| `guarded_percentage` | float | 0.0-1.0 | % of tasks with Guardian review |

### Trends

Each trend has:
- `current`: Current period value
- `previous`: Previous period value
- `change`: Percentage change (-1.0 to +1.0)
- `direction`: "up", "down", or "stable"
- `data_points`: Array of last 7 values (for sparkline)

### Top Risks

Up to 5 risks, each with:
- `id`: Unique identifier
- `type`: Risk type code
- `severity`: CRITICAL/HIGH/MEDIUM/LOW
- `title`: Human-readable description
- `affected_tasks`: Number of tasks affected
- `first_seen`: ISO8601 timestamp

### Health

- `guardian_coverage`: Guardian review coverage (0.0-1.0)
- `avg_decision_latency_ms`: Average decision processing time
- `tasks_with_audits`: % of tasks with audit records (0.0-1.0)
- `active_guardians`: Number of active Guardians
- `last_scan`: ISO8601 timestamp of last scan (may be null)

## Usage Examples

### Bash

```bash
# 7-day dashboard
curl http://localhost:8080/api/governance/dashboard

# 30-day dashboard
curl http://localhost:8080/api/governance/dashboard?timeframe=30d

# With jq formatting
curl http://localhost:8080/api/governance/dashboard | jq .
```

### Python

```python
import requests

def get_dashboard(timeframe='7d'):
    response = requests.get(
        'http://localhost:8080/api/governance/dashboard',
        params={'timeframe': timeframe}
    )
    return response.json()

dashboard = get_dashboard('7d')
print(f"Risk: {dashboard['metrics']['risk_level']}")
print(f"Open Findings: {dashboard['metrics']['open_findings']}")
```

### JavaScript

```javascript
async function fetchDashboard(timeframe = '7d') {
  const response = await fetch(
    `/api/governance/dashboard?timeframe=${timeframe}`
  );
  return response.json();
}

const dashboard = await fetchDashboard('7d');
console.log(`Risk Level: ${dashboard.metrics.risk_level}`);
```

## Risk Level Interpretation

| Level | Meaning | Action Required |
|-------|---------|-----------------|
| **CRITICAL** | System has critical findings | Immediate attention needed |
| **HIGH** | >5 high-severity findings | Review and address soon |
| **MEDIUM** | 1-5 high-severity findings | Monitor and plan fixes |
| **LOW** | System healthy | Routine monitoring |
| **UNKNOWN** | Cannot determine risk | Check data sources |

## Performance

- **Response Time**: < 1s (guaranteed)
- **Cache Duration**: 5 minutes
- **Cache Hit Rate**: ~99% (after first request)
- **Supported Data Size**: 1000+ records

## Data Sources

- `lead_findings`: Risk findings from Lead Agent
- `task_audits`: Supervisor decision trail
- `guardian_reviews`: Guardian verification records
- `tasks`: Task records

## Graceful Degradation

If data is missing, API returns valid response with zeros:

```json
{
  "metrics": {
    "risk_level": "UNKNOWN",
    "open_findings": 0,
    "blocked_rate": 0.0,
    "guarded_percentage": 0.0
  }
}
```

## Error Handling

- **200 OK**: Success (even with degraded data)
- **400 Bad Request**: Invalid parameters
- **500 Internal Server Error**: Unexpected error

## OpenAPI Documentation

View interactive API docs:
```
http://localhost:8080/docs
```

Look for the `governance_dashboard` tag.

## Troubleshooting

### Empty Metrics

**Problem**: All metrics are zero.

**Solution**:
1. Check that Lead Agent has run scans
2. Verify data exists in timeframe
3. Try longer timeframe (30d or 90d)

### Slow Response

**Problem**: Response takes > 1s.

**Solution**:
1. Check database size
2. Verify indexes exist on time columns
3. Clear cache (restart WebUI)

### Unknown Risk Level

**Problem**: `risk_level` is "UNKNOWN".

**Solution**:
1. Check `lead_findings` table has data
2. Verify Lead Agent is configured
3. Run manual Lead scan

## Quick Checks

```bash
# Check if API is running
curl http://localhost:8080/api/governance/dashboard

# Check with verbose output
curl -v http://localhost:8080/api/governance/dashboard

# Check specific timeframe
curl http://localhost:8080/api/governance/dashboard?timeframe=90d

# Pretty print with jq
curl http://localhost:8080/api/governance/dashboard | jq .metrics
```

## Integration Checklist

- [ ] API endpoint accessible
- [ ] Response format validated
- [ ] Frontend can parse response
- [ ] Metrics displayed correctly
- [ ] Trends render as sparklines
- [ ] Top risks shown in list
- [ ] Health indicators displayed
- [ ] Error states handled

## Related Documentation

- Full API docs: `docs/governance/dashboard_api.md`
- Delivery report: `TASK_5_DASHBOARD_API_DELIVERY.md`
- Lead Agent: `docs/governance/lead_agent.md`
- Guardian: `docs/governance/guardian_verification.md`

## Support

For issues or questions:
1. Check logs: `agentos.webui.api.governance_dashboard`
2. Review full documentation: `docs/governance/dashboard_api.md`
3. Run verification: `python verify_dashboard_implementation.py`

---

**Last Updated**: 2026-01-28
**Version**: 1.0.0
**Status**: Production Ready
