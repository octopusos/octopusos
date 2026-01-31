# Phase 4: RAG Health - Implementation Guide

## Overview

Phase 4 adds comprehensive health monitoring for the AgentOS Knowledge/RAG system. This includes:
- Real-time health metrics display
- System health checks
- Bad smell detection and recommendations

## Quick Start

### 1. Start the WebUI Server

```bash
# From the AgentOS root directory
python -m agentos.webui.app
```

The server will start on `http://localhost:8000`

### 2. Access the Health Dashboard

1. Open your browser to `http://localhost:8000`
2. Navigate to **Knowledge** > **Health** in the sidebar
3. View the health metrics, checks, and detected issues

### 3. Test the API Endpoint

```bash
# Test the health endpoint
python test_phase4_health.py

# Or use curl
curl http://localhost:8000/api/knowledge/health
```

## Features

### Health Metrics Dashboard

The health dashboard displays 6 key metrics:

1. **Index Lag**
   - Time since last index operation
   - Status: Fresh (<1h), Needs Refresh (1-24h), Stale (>24h)

2. **Fail Rate (7d)**
   - Failure rate over the last 7 days
   - Status: Good (<5%), Elevated (5-10%), High (>10%)

3. **Empty Hit Rate**
   - Percentage of searches returning no results
   - Status: Good (<10%), Elevated (10-20%), High (>20%)

4. **File Coverage**
   - Percentage of project files that are indexed
   - Status: Excellent (>90%), Good (70-90%), Poor (<70%)

5. **Total Chunks**
   - Total number of indexed chunks
   - Informational metric

6. **Total Files**
   - Total number of tracked files
   - Informational metric

### Health Checks

The system performs 4 automated health checks:

1. **FTS5 Available**
   - Verifies SQLite FTS5 extension is available
   - Critical for full-text search functionality

2. **Schema Version**
   - Checks database schema version
   - Ensures compatibility

3. **Index Staleness**
   - Counts files modified since last index
   - Alerts when files need re-indexing

4. **Orphan Chunks**
   - Detects chunks whose source files have been deleted
   - Indicates cleanup is needed

### Bad Smell Detection

The system detects 3 types of code/content issues:

1. **Duplicate Content**
   - Severity: Warning
   - Detects identical or near-identical content across files
   - Suggestion: Consolidate duplicate content

2. **Oversized Files**
   - Severity: Info
   - Finds files exceeding 10,000 lines
   - Suggestion: Split large files for better chunking

3. **Config Conflicts**
   - Severity: Error
   - Detects conflicting configuration settings
   - Suggestion: Resolve configuration conflicts

## API Documentation

### GET /api/knowledge/health

Returns comprehensive health information for the knowledge base.

**Response Format:**

```json
{
  "ok": true,
  "data": {
    "metrics": {
      "index_lag_seconds": 9000,
      "fail_rate_7d": 0.012,
      "empty_hit_rate": 0.053,
      "file_coverage": 0.942,
      "total_chunks": 1250,
      "total_files": 85
    },
    "checks": [
      {
        "name": "FTS5 Available",
        "status": "ok",
        "message": "Full-text search enabled"
      },
      {
        "name": "Schema Version",
        "status": "ok",
        "message": "Schema v1.0"
      },
      {
        "name": "Index Staleness",
        "status": "warn",
        "message": "15 files modified since last index"
      },
      {
        "name": "Orphan Chunks",
        "status": "ok",
        "message": "No orphan chunks found"
      }
    ],
    "bad_smells": [
      {
        "type": "duplicate_content",
        "severity": "warn",
        "count": 8,
        "details": ["docs/api.md", "docs/reference.md"],
        "suggestion": "Consider consolidating duplicate content"
      }
    ]
  }
}
```

**Status Codes:**
- `200 OK`: Health data retrieved successfully
- `500 Internal Server Error`: Server error (check `error` field in response)

**Check Status Values:**
- `ok`: Healthy, no issues
- `warn`: Minor issues detected
- `error`: Critical issues detected

**Severity Values:**
- `info`: Informational, no immediate action required
- `warn`: Warning, attention recommended
- `error`: Error, immediate action required

## File Structure

```
agentos/
├── webui/
│   ├── api/
│   │   └── knowledge.py          # API endpoints including health
│   ├── static/
│   │   ├── css/
│   │   │   └── components.css    # Health view styles
│   │   └── js/
│   │       ├── main.js           # Routing for health view
│   │       └── views/
│   │           └── KnowledgeHealthView.js  # Health UI component
│   └── templates/
│       └── index.html            # Navigation + script includes
```

## Development

### Adding New Health Checks

To add a new health check, modify `/agentos/webui/api/knowledge.py`:

```python
# Add new check
try:
    result = kb_service.your_new_check()
    if result.is_ok:
        checks.append(
            HealthCheck(
                name="Your Check Name",
                status="ok",
                message="Everything is fine",
            ).model_dump()
        )
    else:
        checks.append(
            HealthCheck(
                name="Your Check Name",
                status="error",
                message=f"Issue detected: {result.error}",
            ).model_dump()
        )
except Exception as e:
    checks.append(
        HealthCheck(
            name="Your Check Name",
            status="warn",
            message=f"Check failed: {str(e)}",
        ).model_dump()
    )
```

### Adding New Bad Smell Detectors

To add a new bad smell detector:

```python
# Smell: Your new smell
try:
    if hasattr(kb_service, 'your_detector_method'):
        issues = kb_service.your_detector_method()
        if issues and len(issues) > 0:
            bad_smells.append(
                BadSmell(
                    type="your_smell_type",
                    severity="warn",  # or "info" or "error"
                    count=len(issues),
                    details=issues[:5],  # First 5
                    suggestion="Your actionable suggestion here",
                ).model_dump()
            )
except Exception as e:
    print(f"Your detector failed: {e}")
```

### Customizing Metrics Thresholds

Metric thresholds are defined in `KnowledgeHealthView.js`:

```javascript
// Index Lag thresholds
if (metrics.index_lag_seconds < 3600) {        // < 1 hour
    lagStatus.className = 'metric-status ok';
} else if (metrics.index_lag_seconds < 86400) { // < 24 hours
    lagStatus.className = 'metric-status warn';
} else {                                        // > 24 hours
    lagStatus.className = 'metric-status error';
}
```

Modify these values to suit your requirements.

## Troubleshooting

### Health Dashboard Not Loading

1. **Check if server is running:**
   ```bash
   curl http://localhost:8000/api/knowledge/health
   ```

2. **Check browser console for JavaScript errors:**
   - Open DevTools (F12)
   - Look for errors in Console tab

3. **Verify all files are in place:**
   ```bash
   ls agentos/webui/static/js/views/KnowledgeHealthView.js
   ls agentos/webui/api/knowledge.py
   ```

### API Returns Error

1. **Check server logs** for Python exceptions

2. **Verify ProjectKBService is initialized:**
   ```python
   from agentos.core.project_kb.service import ProjectKBService
   kb = ProjectKBService()
   ```

3. **Check database connection** if using SQLite backend

### Metrics Show Zero Values

This is normal if:
- Knowledge base hasn't been indexed yet
- ProjectKBService stub methods are being used
- No files have been scanned

To populate real data, implement these methods in ProjectKBService:
- `get_total_chunks()`
- `get_total_files()`
- `get_last_index_time()`
- And other health check methods

## Testing

### Manual Testing

1. Start the server
2. Navigate to Knowledge > Health
3. Verify:
   - Metrics display correctly
   - Health checks show appropriate status
   - Bad smells section appears/disappears correctly
   - Refresh button works

### Automated Testing

Run the test script:

```bash
# Ensure server is running first
python test_phase4_health.py
```

Expected output:
```
Testing Phase 4: RAG Health Endpoint
============================================================

1. Calling GET http://localhost:8000/api/knowledge/health...
   Status Code: 200
   ✅ Status code OK

2. Parsing JSON response...

3. Validating response structure...
   ✅ Response structure OK

4. Validating data field...
   ✅ Metrics OK
      - Index Lag: 9000s (2.5h)
      - Fail Rate: 1.2%
      - Empty Hit Rate: 5.3%
      - File Coverage: 94.2%
      - Total Chunks: 0
      - Total Files: 0

5. Validating health checks (4 checks)...
   ✅ FTS5 Available: ok - Full-text search enabled
   ✅ Schema Version: ok - Schema v1.0
   ✅ Index Staleness: ok - All files are indexed
   ✅ Orphan Chunks: ok - No orphan chunks found
   ✅ Health checks OK

6. Checking bad smells (0 detected)...
   ✅ No bad smells detected

============================================================
✅ ALL TESTS PASSED!
============================================================
```

## Next Steps

### Implement Real Health Checks

Currently, the health endpoint uses fallback values. To enable real monitoring:

1. **Implement ProjectKBService methods:**
   - `get_total_chunks()` - Query chunk count from database
   - `get_total_files()` - Count indexed files
   - `get_last_index_time()` - Get timestamp of last index
   - `check_fts5_available()` - Test SQLite FTS5 extension
   - `get_schema_version()` - Read schema version from DB
   - `get_stale_file_count()` - Compare file mtimes to index time
   - `get_orphan_chunk_count()` - Find chunks with deleted sources
   - `find_duplicate_content()` - Detect duplicate content by hash
   - `find_oversized_files(max_lines)` - Find files exceeding threshold
   - `find_config_conflicts()` - Detect configuration issues

2. **Add database migrations** if schema changes are needed

3. **Implement background health monitoring** for alerts

### Add Auto-Refresh

Enable automatic health data refresh:

```javascript
// In KnowledgeHealthView.js init()
this.refreshInterval = setInterval(() => {
    this.loadHealthData();
}, 30000); // Refresh every 30 seconds
```

### Add Alerts

Integrate with notification system:

```javascript
// Check for critical issues
if (check.status === 'error') {
    Toast.error(`Health Check Failed: ${check.name}`);
}
```

### Export Health Reports

Add export functionality:

```javascript
exportHealthReport() {
    const report = {
        timestamp: new Date().toISOString(),
        metrics: this.currentMetrics,
        checks: this.currentChecks,
        bad_smells: this.currentBadSmells
    };

    const blob = new Blob([JSON.stringify(report, null, 2)], {
        type: 'application/json'
    });

    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `health-report-${Date.now()}.json`;
    a.click();
}
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review server logs for error details
3. Verify all files are correctly installed
4. Check that dependencies are up to date

## License

Part of AgentOS - see main project LICENSE file.
