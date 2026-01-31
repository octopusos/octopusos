# InfoNeed Metrics Dashboard

## Overview

The InfoNeed Metrics Dashboard provides real-time quality monitoring for InfoNeed classification in AgentOS. It displays 6 core metrics that help you understand how well the system is identifying when external communication is needed.

**Location**: WebUI → Quality → InfoNeed Metrics

## Features

### 6 Core Metrics

1. **Comm Trigger Rate**
   - How often `REQUIRE_COMM` is triggered
   - Target range: 15-35%
   - Shows: Percentage of queries that request external communication

2. **False Positive Rate**
   - Unnecessary communication requests
   - Target: <10% (lower is better)
   - Shows: Queries incorrectly marked as needing communication

3. **False Negative Rate**
   - Missed communication opportunities
   - Target: <15% (lower is better)
   - Shows: Queries that should have triggered communication but didn't

4. **Ambient Hit Rate**
   - AMBIENT_STATE classification accuracy
   - Target: >85%
   - Shows: How accurately the system identifies ambient/background queries

5. **Decision Latency**
   - Classification performance metrics
   - Shows: P50, P95, P99, and average latency in milliseconds
   - Target: <150ms average

6. **Decision Stability**
   - Consistency for similar questions
   - Target: >75%
   - Shows: Whether the system gives consistent answers to similar queries

### Interactive Features

- **Time Range Selection**: View metrics for 24h, 7d, 30d, or custom ranges
- **Manual Refresh**: Update metrics on demand
- **Trend Visualization**: Chart.js-powered line graphs showing metric trends over time
- **Export**: Download full metrics data as JSON for further analysis
- **Color-Coded Cards**: Visual indicators for metric status (green/yellow/red)

## Usage

### Accessing the Dashboard

1. Start AgentOS WebUI:
   ```bash
   python -m agentos.webui.app
   ```

2. Navigate to: **Quality → InfoNeed Metrics**

### Time Range Selection

Use the dropdown to select your desired time range:
- **Last 24 Hours** (default) - Recent performance
- **Last 7 Days** - Weekly trends
- **Last 30 Days** - Monthly overview

### Interpreting Metrics

#### Good Status (Green Border)
- Metric is within optimal range
- System is performing well for this metric

#### Warning Status (Yellow Border)
- Metric is outside optimal range but not critical
- Consider monitoring this metric more closely

#### Danger Status (Red Border)
- Metric is significantly outside optimal range
- Investigation recommended

### Exporting Data

1. Click the **Export** button
2. Select format (currently JSON only)
3. File will download automatically with filename: `info_need_metrics_{timerange}_{timestamp}.json`

The exported file contains:
- All 6 core metrics
- Breakdown by classification type
- Outcome distribution
- Complete period information
- Metadata (calculated timestamp, version)

## API Endpoints

For programmatic access, use these REST API endpoints:

### GET /api/info-need-metrics/summary

Get metrics summary for a time period.

**Parameters:**
- `time_range` (required): `24h`, `7d`, `30d`, or `custom`
- `start_time` (optional): ISO datetime for custom range
- `end_time` (optional): ISO datetime for custom range

**Example:**
```bash
curl "http://localhost:8000/api/info-need-metrics/summary?time_range=24h"
```

**Response:**
```json
{
  "ok": true,
  "data": {
    "time_range": "24h",
    "period": {
      "start": "2026-01-30T10:30:00Z",
      "end": "2026-01-31T10:30:00Z"
    },
    "last_updated": "2026-01-31T10:30:00Z",
    "metrics": {
      "comm_trigger_rate": 0.234,
      "false_positive_rate": 0.087,
      "false_negative_rate": 0.142,
      "ambient_hit_rate": 0.956,
      "decision_latency": {
        "p50": 145.3,
        "p95": 234.2,
        "p99": 345.1,
        "avg": 165.4,
        "count": 450
      },
      "decision_stability": 0.892
    },
    "counts": {
      "total_classifications": 450,
      "comm_triggered": 105,
      "ambient_queries": 90,
      "false_positives": 12,
      "false_negatives": 18
    }
  },
  "error": null
}
```

### GET /api/info-need-metrics/history

Get historical trend data for visualization.

**Parameters:**
- `time_range` (required): `24h`, `7d`, `30d`, or `custom`
- `granularity` (required): `hour` or `day`
- `start_time` (optional): ISO datetime for custom range
- `end_time` (optional): ISO datetime for custom range

**Example:**
```bash
curl "http://localhost:8000/api/info-need-metrics/history?time_range=7d&granularity=hour"
```

**Response:**
```json
{
  "ok": true,
  "data": {
    "time_range": "7d",
    "granularity": "hour",
    "data_points": [
      {
        "timestamp": "2026-01-30T10:00:00Z",
        "comm_trigger_rate": 0.234,
        "false_positive_rate": 0.087,
        "false_negative_rate": 0.142,
        "ambient_hit_rate": 0.956,
        "decision_latency_avg": 145.3,
        "decision_stability": 0.892,
        "sample_count": 45
      }
    ]
  },
  "error": null
}
```

### GET /api/info-need-metrics/export

Export full metrics data.

**Parameters:**
- `time_range` (required): `24h`, `7d`, `30d`, or `custom`
- `format` (required): `json` (only format currently supported)
- `start_time` (optional): ISO datetime for custom range
- `end_time` (optional): ISO datetime for custom range

**Example:**
```bash
curl "http://localhost:8000/api/info-need-metrics/export?time_range=24h&format=json" > metrics.json
```

## Data Sources

All metrics are calculated from audit logs in the AgentOS database:
- **Classification Events**: `event_type = 'info_need_classification'`
- **Outcome Events**: `event_type = 'info_need_outcome'`

No semantic analysis or LLM calls are involved - all metrics are pure statistics.

## Constraints

- **Read-only**: Dashboard displays data only, no actions
- **No Semantic Analysis**: Pure statistical calculations
- **No LLM Calls**: Can run offline as batch job
- **Audit Log Based**: Requires audit logging to be enabled

## Troubleshooting

### No Data Displayed

**Possible causes:**
1. No InfoNeed classification events in the selected time range
2. Audit logging not enabled
3. Database connection issues

**Solutions:**
- Verify audit logging is enabled in configuration
- Check database connectivity
- Try a different time range

### Metrics Show as N/A

**Cause:** Insufficient data for calculation (e.g., no AMBIENT_STATE classifications for ambient_hit_rate)

**Solution:** This is normal if certain classification types haven't occurred. Continue using the system to accumulate data.

### Chart Not Rendering

**Possible causes:**
1. Chart.js failed to load
2. No historical data points
3. Browser JavaScript error

**Solutions:**
- Check browser console for errors
- Verify network connectivity
- Try refreshing the page

## Performance

- **Metrics Calculation**: O(n) where n = number of audit events
- **Typical Response Time**: <500ms for 24h range
- **Browser Memory**: ~50MB with charts loaded
- **Recommended Refresh Interval**: Manual or 5-minute auto-refresh

## Future Enhancements

Potential improvements (not yet implemented):
- CSV/Excel export formats
- Email alerts for metric thresholds
- Metric comparison between time periods
- Drill-down to individual classification events
- Real-time streaming updates (WebSocket)
- Custom metric thresholds configuration

## Related Documentation

- [InfoNeed Classification](./INFO_NEED_CLASSIFICATION.md)
- [Audit Logging](./AUDIT_LOGGING.md)
- [Chat Communication Adapter](./chat/COMMUNICATION_ADAPTER.md)
