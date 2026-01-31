# Governance Dashboard API Documentation

## Overview

The Governance Dashboard API provides aggregated governance health metrics for C-level visibility into the AgentOS governance system. It combines data from multiple sources to provide a real-time view of system health, risks, and Guardian coverage.

## Key Features

- **Read-only aggregation**: No new storage tables, queries existing data
- **Multi-source data**: Combines lead_findings, task_audits, guardian_reviews, and tasks
- **High performance**: < 1s response time with 5-minute caching
- **Graceful degradation**: Returns meaningful results even with partial data

## API Endpoint

### GET /api/governance/dashboard

Get complete Governance Dashboard data.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| timeframe | string | No | 7d | Time window: `7d`, `30d`, or `90d` |
| project_id | string | No | None | Filter by project ID (optional) |

**Example Request:**

```bash
curl http://localhost:8080/api/governance/dashboard?timeframe=7d
```

**Response Structure:**

```json
{
  "metrics": {
    "risk_level": "HIGH",
    "open_findings": 12,
    "blocked_rate": 0.084,
    "guarded_percentage": 0.92
  },
  "trends": {
    "findings": {
      "current": 12,
      "previous": 15,
      "change": -0.20,
      "direction": "down",
      "data_points": [10, 12, 15, 13, 11, 12, 12]
    },
    "blocked_decisions": {
      "current": 8.4,
      "previous": 12.1,
      "change": -0.306,
      "direction": "down",
      "data_points": [12.1, 11.5, 10.2, 9.8, 8.9, 8.5, 8.4]
    },
    "guardian_coverage": {
      "current": 92,
      "previous": 88,
      "change": 0.045,
      "direction": "up",
      "data_points": [88, 89, 90, 91, 91, 92, 92]
    }
  },
  "top_risks": [
    {
      "id": "finding_123",
      "type": "blocked_reason_spike",
      "severity": "CRITICAL",
      "title": "Blocked decisions increased 45% in 24h",
      "affected_tasks": 12,
      "first_seen": "2026-01-28T10:00:00Z"
    },
    {
      "id": "finding_456",
      "type": "high_risk_allow",
      "severity": "HIGH",
      "title": "High-risk operation allowed without Guardian review",
      "affected_tasks": 3,
      "first_seen": "2026-01-28T09:30:00Z"
    }
  ],
  "health": {
    "guardian_coverage": 0.92,
    "avg_decision_latency_ms": 1200,
    "tasks_with_audits": 0.98,
    "active_guardians": 5,
    "last_scan": "2026-01-28T11:30:00Z"
  },
  "generated_at": "2026-01-28T12:00:00Z"
}
```

## Response Fields

### Metrics

Core governance health metrics:

- **risk_level** (string): Overall system risk level
  - `CRITICAL`: System has critical findings requiring immediate attention
  - `HIGH`: System has significant risks (>5 HIGH findings)
  - `MEDIUM`: System has moderate risks (1-5 HIGH findings)
  - `LOW`: System is healthy with minimal risks
  - `UNKNOWN`: Unable to determine risk level (data unavailable)

- **open_findings** (integer): Number of findings without linked follow-up tasks

- **blocked_rate** (float): Ratio of blocked decisions to total decisions (0.0-1.0)
  - Formula: `blocked_count / total_decisions`
  - Example: 0.084 = 8.4% of decisions were blocked

- **guarded_percentage** (float): Ratio of tasks with Guardian reviews (0.0-1.0)
  - Formula: `reviewed_tasks / total_tasks`
  - Example: 0.92 = 92% of tasks have Guardian coverage

### Trends

Trend data for key metrics over time:

Each trend object contains:
- **current** (float): Current period value
- **previous** (float): Previous period average
- **change** (float): Percentage change (-1.0 to +1.0)
  - Formula: `(current - previous) / previous`
  - Example: -0.20 = 20% decrease
- **direction** (string): Trend direction
  - `up`: Metric increased (change > 5%)
  - `down`: Metric decreased (change < -5%)
  - `stable`: Metric is stable (|change| <= 5%)
- **data_points** (array): Last 7 data points for sparkline visualization

Trend categories:
- **findings**: Number of open findings over time
- **blocked_decisions**: Blocked decision rate (%) over time
- **guardian_coverage**: Guardian coverage rate (%) over time

### Top Risks

Top 5 highest-priority risks identified by the system:

- **id** (string): Unique risk identifier (finding fingerprint)
- **type** (string): Risk type code (e.g., `blocked_reason_spike`)
- **severity** (string): Risk severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`)
- **title** (string): Human-readable risk title
- **affected_tasks** (integer): Number of tasks affected by this risk
- **first_seen** (string): ISO8601 timestamp of first detection

**Risk Scoring Algorithm:**

Risks are scored and prioritized based on:

1. **Severity weight**:
   - CRITICAL: 10 points
   - HIGH: 5 points
   - MEDIUM: 2 points
   - LOW: 1 point

2. **Impact weight**:
   - affected_tasks × 0.5

3. **Time weight**:
   - Recent (< 24h): ×1.5 multiplier
   - Older (>= 24h): ×1.0 multiplier

Final score = (severity_weight × time_weight) + (affected_tasks × 0.5)

### Health

System health indicators:

- **guardian_coverage** (float): Overall Guardian coverage ratio (0.0-1.0)
- **avg_decision_latency_ms** (integer): Average decision processing latency in milliseconds
  - Calculated from: `supervisor_processed_at - source_event_ts`
- **tasks_with_audits** (float): Ratio of tasks with audit records (0.0-1.0)
- **active_guardians** (integer): Number of unique Guardians active in timeframe
- **last_scan** (string|null): ISO8601 timestamp of last Lead scan (may be null)

### Generated At

- **generated_at** (string): ISO8601 timestamp when dashboard was generated

## Aggregation Logic

### Data Sources

The dashboard queries data from four tables:

1. **lead_findings**: Risk findings from Lead Agent scans
   - Filtered by: `last_seen_at >= cutoff_date`
   - Used for: risk_level, open_findings, top_risks

2. **task_audits**: Supervisor decision audit trail
   - Filtered by: `event_type LIKE 'SUPERVISOR_%' AND created_at >= cutoff_date`
   - Used for: blocked_rate, avg_decision_latency_ms

3. **guardian_reviews**: Guardian verification records
   - Filtered by: `created_at >= cutoff_date`
   - Used for: guarded_percentage, active_guardians

4. **tasks**: Task records
   - Filtered by: `created_at >= cutoff_date`
   - Used for: guardian_coverage, tasks_with_audits

### Aggregation Functions

#### Risk Level Calculation

```python
def aggregate_risk_level(findings):
    if any(f.severity == "CRITICAL"):
        return "CRITICAL"
    elif count(f.severity == "HIGH") > 5:
        return "HIGH"
    elif count(f.severity == "HIGH") > 0:
        return "MEDIUM"
    else:
        return "LOW"
```

#### Blocked Rate Calculation

```python
def calculate_blocked_rate(audits):
    total = count(audits with event_type LIKE 'SUPERVISOR_%')
    blocked = count(audits with event_type == 'SUPERVISOR_BLOCKED')
    return blocked / total if total > 0 else 0.0
```

#### Guardian Coverage Calculation

```python
def calculate_guardian_coverage(tasks, reviews):
    task_ids = set(task.task_id for task in tasks)
    reviewed_ids = set(r.target_id for r in reviews if r.target_type == 'task')
    intersection = task_ids & reviewed_ids
    return len(intersection) / len(task_ids) if task_ids else 0.0
```

## Performance Characteristics

### Caching Strategy

- **Cache Duration**: 5 minutes
- **Cache Key**: Based on `timeframe` and `project_id`
- **Implementation**: Python `functools.lru_cache`
- **Cache Size**: 32 entries (LRU eviction)

### Performance Benchmarks

- **Target**: < 1s response time
- **Tested with**: 100 findings, 100 audits, 100 reviews, 100 tasks
- **Actual**: ~0.5s (without cache), ~0.001s (with cache)

### Query Optimization

All queries use indexed columns:
- `lead_findings.last_seen_at` (indexed)
- `task_audits.created_at` (indexed)
- `guardian_reviews.created_at` (indexed)
- `tasks.created_at` (indexed)

## Graceful Degradation

The dashboard is designed to provide meaningful results even with partial data:

### Missing Findings Table

If `lead_findings` table doesn't exist or is empty:
- `risk_level`: Returns `"LOW"`
- `open_findings`: Returns `0`
- `top_risks`: Returns `[]`

### Missing Guardian Reviews Table

If `guardian_reviews` table doesn't exist or is empty:
- `guarded_percentage`: Returns `0.0`
- `active_guardians`: Returns `0`

### Missing Task Audits Table

If `task_audits` table doesn't exist or is empty:
- `blocked_rate`: Returns `0.0`
- `avg_decision_latency_ms`: Returns `0`

### Complete Data Loss

If all data sources fail:
- Returns valid JSON structure with zero/empty values
- `risk_level`: `"UNKNOWN"`
- HTTP 200 status (not 500) to allow frontend to display empty state

## Error Handling

### Safe Aggregation Wrapper

All aggregation functions are wrapped with `safe_aggregate()`:

```python
def safe_aggregate(func, fallback_value, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.warning(f"Aggregation failed: {func.__name__}, using fallback: {e}")
        return fallback_value
```

This ensures:
- No unhandled exceptions
- Meaningful fallback values
- Logged warnings for debugging

### HTTP Status Codes

- **200 OK**: Successful response (even with degraded data)
- **400 Bad Request**: Invalid query parameters (e.g., invalid timeframe)
- **500 Internal Server Error**: Unexpected server error (should be rare)

## Usage Examples

### Basic Usage

```bash
# Get 7-day dashboard
curl http://localhost:8080/api/governance/dashboard

# Get 30-day dashboard
curl http://localhost:8080/api/governance/dashboard?timeframe=30d

# Get 90-day dashboard
curl http://localhost:8080/api/governance/dashboard?timeframe=90d
```

### With Project Filter

```bash
# Filter by project ID
curl http://localhost:8080/api/governance/dashboard?project_id=proj-123
```

### Integration Example (JavaScript)

```javascript
async function fetchDashboard(timeframe = '7d') {
  const response = await fetch(
    `/api/governance/dashboard?timeframe=${timeframe}`
  );

  if (!response.ok) {
    throw new Error(`Dashboard API error: ${response.statusText}`);
  }

  const dashboard = await response.json();

  // Display metrics
  console.log(`Risk Level: ${dashboard.metrics.risk_level}`);
  console.log(`Open Findings: ${dashboard.metrics.open_findings}`);
  console.log(`Blocked Rate: ${(dashboard.metrics.blocked_rate * 100).toFixed(1)}%`);
  console.log(`Guardian Coverage: ${(dashboard.metrics.guarded_percentage * 100).toFixed(1)}%`);

  return dashboard;
}
```

### Integration Example (Python)

```python
import requests

def fetch_dashboard(timeframe='7d', project_id=None):
    """Fetch governance dashboard data"""
    params = {'timeframe': timeframe}
    if project_id:
        params['project_id'] = project_id

    response = requests.get(
        'http://localhost:8080/api/governance/dashboard',
        params=params
    )
    response.raise_for_status()

    dashboard = response.json()

    # Extract key metrics
    metrics = dashboard['metrics']
    print(f"Risk Level: {metrics['risk_level']}")
    print(f"Open Findings: {metrics['open_findings']}")
    print(f"Blocked Rate: {metrics['blocked_rate']:.1%}")
    print(f"Guardian Coverage: {metrics['guarded_percentage']:.1%}")

    return dashboard
```

## Best Practices

### Client-Side Caching

While the API has server-side caching, consider implementing client-side caching:

```javascript
// Cache dashboard data for 5 minutes
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

class DashboardCache {
  constructor() {
    this.cache = new Map();
  }

  get(timeframe) {
    const entry = this.cache.get(timeframe);
    if (!entry) return null;

    const now = Date.now();
    if (now - entry.timestamp > CACHE_TTL) {
      this.cache.delete(timeframe);
      return null;
    }

    return entry.data;
  }

  set(timeframe, data) {
    this.cache.set(timeframe, {
      data,
      timestamp: Date.now()
    });
  }
}
```

### Polling Strategy

For real-time dashboards, use appropriate polling intervals:

```javascript
// Poll every 5 minutes (aligned with server cache)
const POLL_INTERVAL = 5 * 60 * 1000;

function startDashboardPolling(timeframe) {
  async function poll() {
    try {
      const dashboard = await fetchDashboard(timeframe);
      updateUI(dashboard);
    } catch (error) {
      console.error('Dashboard polling error:', error);
    }
  }

  // Initial fetch
  poll();

  // Set up polling
  return setInterval(poll, POLL_INTERVAL);
}

// Usage
const intervalId = startDashboardPolling('7d');

// Cleanup
clearInterval(intervalId);
```

### Error Handling

Always handle errors gracefully:

```javascript
async function safeFetchDashboard(timeframe) {
  try {
    return await fetchDashboard(timeframe);
  } catch (error) {
    console.error('Failed to fetch dashboard:', error);

    // Return fallback empty dashboard
    return {
      metrics: {
        risk_level: 'UNKNOWN',
        open_findings: 0,
        blocked_rate: 0.0,
        guarded_percentage: 0.0
      },
      trends: {
        findings: { current: 0, previous: 0, change: 0, direction: 'stable', data_points: [] },
        blocked_decisions: { current: 0, previous: 0, change: 0, direction: 'stable', data_points: [] },
        guardian_coverage: { current: 0, previous: 0, change: 0, direction: 'stable', data_points: [] }
      },
      top_risks: [],
      health: {
        guardian_coverage: 0.0,
        avg_decision_latency_ms: 0,
        tasks_with_audits: 0.0,
        active_guardians: 0,
        last_scan: null
      },
      generated_at: new Date().toISOString()
    };
  }
}
```

## Troubleshooting

### Slow Response Times

If response times exceed 1s:

1. **Check database size**: Large tables may need optimization
2. **Verify indexes**: Ensure all time-based indexes exist
3. **Check timeframe**: Longer timeframes (90d) require more data processing
4. **Review logs**: Look for `WARNING` messages about slow queries

### Empty or Zero Metrics

If dashboard returns all zeros:

1. **Verify data exists**: Check that tables have data in the timeframe
2. **Check timeframe**: Ensure data exists within the selected timeframe
3. **Review logs**: Look for `WARNING` messages about failed aggregations
4. **Test queries**: Run individual data fetching functions directly

### Cache Not Working

If cache doesn't seem effective:

1. **Check cache key**: Verify `get_cache_key()` returns consistent values
2. **Review parameters**: Ensure `project_id` is consistent (None vs empty string)
3. **Clear cache**: Restart application to clear LRU cache
4. **Check logs**: Look for cache hit/miss patterns

## Related Documentation

- [Lead Agent Risk Mining](./lead_agent.md)
- [Guardian Verification](./guardian_verification.md)
- [Supervisor Decision Audit](./supervisor_audit.md)
- [Task Management](../task/task_management.md)

## Changelog

### Version 1.0.0 (2026-01-28)

- Initial implementation
- Support for 7d, 30d, 90d timeframes
- 5-minute server-side caching
- Graceful degradation for missing data
- Complete test coverage
