# Decision Replay API

Complete API documentation for the Governance Replay system.

## Overview

The Decision Replay API provides endpoints to answer "Why was this task allowed/paused/blocked?" by exposing complete decision history and audit trails.

All endpoints are prefixed with `/api/governance`.

## Authentication

Currently, no authentication is required. In production deployments, add authentication middleware.

## Endpoints

### 1. Task Governance Summary

Get a high-level overview of a task's governance status.

```bash
GET /api/governance/tasks/{task_id}/summary
```

**Parameters:**
- `task_id` (path, required): Task ID

**Response:**
```json
{
  "task_id": "task-123",
  "status": "BLOCKED",
  "last_decision_type": "BLOCK",
  "last_decision_ts": "2024-01-28T10:30:00Z",
  "blocked_reason_code": "REDLINE_001",
  "inbox_backlog": 2,
  "decision_count": 5
}
```

**Fields:**
- `task_id`: Task identifier
- `status`: Current task status (PENDING, RUNNING, BLOCKED, PAUSED, etc.)
- `last_decision_type`: Type of last decision (ALLOW, BLOCK, PAUSE, RETRY) or null
- `last_decision_ts`: Timestamp of last decision (ISO8601) or null
- `blocked_reason_code`: Code of blocking reason if status is BLOCKED, null otherwise
- `inbox_backlog`: Number of pending events in supervisor inbox
- `decision_count`: Total number of supervisor decisions for this task

**Status Codes:**
- `200`: Success
- `404`: Task not found
- `500`: Internal server error

**Example:**
```bash
curl http://localhost:8080/api/governance/tasks/task-123/summary
```

---

### 2. Task Decision Trace

Get complete decision history for a task (core endpoint).

```bash
GET /api/governance/tasks/{task_id}/decision-trace
```

**Parameters:**
- `task_id` (path, required): Task ID
- `limit` (query, optional): Maximum number of trace items (1-500, default: 200)
- `cursor` (query, optional): Pagination cursor for next page

**Response:**
```json
{
  "task_id": "task-123",
  "trace_items": [
    {
      "ts": "2024-01-28T10:30:00Z",
      "kind": "audit",
      "audit_id": "audit-001",
      "event_type": "SUPERVISOR_BLOCKED",
      "decision_id": "dec-001",
      "decision_snapshot": { /* complete snapshot */ }
    },
    {
      "ts": "2024-01-28T10:25:00Z",
      "kind": "event",
      "event_id": 123,
      "event_type": "TASK_CREATED",
      "payload": { /* event data */ }
    }
  ],
  "next_cursor": "2024-01-28T10:20:00Z_456",
  "count": 2
}
```

**Trace Item Types:**

**audit**: Supervisor decision record
- `audit_id`: Audit record ID
- `event_type`: Decision event type (SUPERVISOR_ALLOWED, SUPERVISOR_BLOCKED, etc.)
- `decision_id`: Decision ID
- `decision_snapshot`: Complete decision snapshot (see DecisionSnapshot schema)

**event**: Original task event
- `event_id`: Event ID
- `event_type`: Event type (TASK_CREATED, TASK_STEP_COMPLETED, etc.)
- `payload`: Event payload

**Status Codes:**
- `200`: Success
- `400`: Invalid parameters
- `404`: Task not found
- `500`: Internal server error

**Example:**
```bash
# Get first page
curl http://localhost:8080/api/governance/tasks/task-123/decision-trace?limit=50

# Get next page
curl "http://localhost:8080/api/governance/tasks/task-123/decision-trace?limit=50&cursor=2024-01-28T10:20:00Z_456"
```

---

### 3. Decision Details

Get complete details of a single decision.

```bash
GET /api/governance/decisions/{decision_id}
```

**Parameters:**
- `decision_id` (path, required): Decision ID

**Response:**
```json
{
  "decision_id": "dec-001",
  "decision_snapshot": {
    "decision_id": "dec-001",
    "policy": "default",
    "event": {
      "event_id": "evt-001",
      "event_type": "TASK_CREATED",
      "source": "eventbus",
      "ts": "2024-01-28T10:25:00Z"
    },
    "inputs": {
      "task_status": "PENDING",
      "context": {}
    },
    "findings": [
      {
        "kind": "REDLINE",
        "severity": "HIGH",
        "code": "REDLINE_001",
        "message": "Dangerous operation detected",
        "evidence": {
          "tool": "file_delete",
          "path": "/etc/passwd"
        }
      }
    ],
    "decision": {
      "decision_type": "BLOCK",
      "reason": "Redline violation"
    },
    "actions": [
      {
        "action_type": "BLOCK_TASK",
        "status": "OK"
      }
    ],
    "metrics": {
      "decision_time_ms": 123
    }
  }
}
```

**Status Codes:**
- `200`: Success
- `404`: Decision not found
- `500`: Internal server error

**Example:**
```bash
curl http://localhost:8080/api/governance/decisions/dec-001
```

---

### 4. Blocked Reasons Statistics

Get top N blocked/paused tasks by frequency (for dashboard).

```bash
GET /api/governance/stats/blocked-reasons
```

**Parameters:**
- `window` (query, optional): Time window - `24h`, `7d`, or `30d` (default: `7d`)
- `top_n` (query, optional): Number of top results (1-100, default: 20)

**Response:**
```json
{
  "window": "7d",
  "top_n": 20,
  "blocked_tasks": [
    {
      "task_id": "task-456",
      "block_count": 15,
      "last_blocked_at": "2024-01-28T10:30:00Z",
      "reason_code": "REDLINE_001"
    },
    {
      "task_id": "task-789",
      "block_count": 8,
      "last_blocked_at": "2024-01-27T14:20:00Z",
      "reason_code": "CONFLICT_API_LIMIT"
    }
  ]
}
```

**Fields:**
- `window`: Time window used
- `top_n`: Number of results requested
- `blocked_tasks`: Array of blocked task summaries
  - `task_id`: Task identifier
  - `block_count`: Number of times blocked
  - `last_blocked_at`: Timestamp of most recent block
  - `reason_code`: Most recent blocking reason code

**Status Codes:**
- `200`: Success
- `400`: Invalid parameters
- `500`: Internal server error

**Example:**
```bash
curl http://localhost:8080/api/governance/stats/blocked-reasons?window=7d&top_n=10
```

---

### 5. Decision Types Statistics

Get distribution of decision types within a time window.

```bash
GET /api/governance/stats/decision-types
```

**Parameters:**
- `window` (query, optional): Time window - `24h`, `7d`, or `30d` (default: `24h`)

**Response:**
```json
{
  "window": "24h",
  "decision_types": {
    "ALLOWED": 150,
    "BLOCKED": 5,
    "PAUSED": 2,
    "RETRY": 1
  },
  "total": 158
}
```

**Fields:**
- `window`: Time window used
- `decision_types`: Map of decision type to count
- `total`: Total number of decisions

**Status Codes:**
- `200`: Success
- `422`: Invalid window parameter
- `500`: Internal server error

**Example:**
```bash
curl http://localhost:8080/api/governance/stats/decision-types?window=24h
```

---

### 6. Decision Lag Statistics

Calculate decision processing lag percentiles (time from event to decision).

```bash
GET /api/governance/stats/decision-lag
```

**Parameters:**
- `window` (query, optional): Time window - `24h`, `7d`, or `30d` (default: `24h`)
- `pctl` (query, optional): Percentile to calculate (50-99, default: 95)

**Response:**
```json
{
  "window": "24h",
  "percentile": 95,
  "p50": 0.123,
  "p95": 0.456,
  "count": 158
}
```

**Fields:**
- `window`: Time window used
- `percentile`: Requested percentile
- `p50`: Median lag in seconds (null if no data)
- `p95`: 95th percentile lag in seconds (null if no data)
- `count`: Number of samples

**Status Codes:**
- `200`: Success
- `400`: Invalid parameters
- `500`: Internal server error

**Example:**
```bash
curl http://localhost:8080/api/governance/stats/decision-lag?window=24h&pctl=95
```

---

## Error Responses

All endpoints return errors in the following format:

```json
{
  "detail": "Error message"
}
```

**Common Status Codes:**
- `400`: Bad Request - Invalid parameters
- `404`: Not Found - Resource doesn't exist
- `422`: Unprocessable Entity - FastAPI validation error
- `500`: Internal Server Error - Unexpected error

---

## Rate Limiting

No rate limiting is currently implemented. In production, add rate limiting middleware.

---

## OpenAPI Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`

---

## Usage Examples

### Debug a Blocked Task

```bash
# 1. Get summary to understand current state
curl http://localhost:8080/api/governance/tasks/task-123/summary

# 2. Get decision trace to see full history
curl http://localhost:8080/api/governance/tasks/task-123/decision-trace

# 3. Get details of specific decision
curl http://localhost:8080/api/governance/decisions/dec-001
```

### Monitor System Health

```bash
# Get decision type distribution
curl http://localhost:8080/api/governance/stats/decision-types?window=24h

# Get decision lag (performance monitoring)
curl http://localhost:8080/api/governance/stats/decision-lag?window=24h

# Get top blocked tasks
curl http://localhost:8080/api/governance/stats/blocked-reasons?window=7d&top_n=10
```

---

## Next Steps

- Add authentication and authorization
- Implement rate limiting
- Add request/response caching
- Add export functionality (CSV, JSON)
- Add GraphQL endpoint for complex queries
