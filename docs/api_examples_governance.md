# Governance APIs - Testing Examples

This document provides curl/httpie examples for testing the 4 Capability Governance API endpoints.

## Prerequisites

Start the WebUI server:
```bash
python -m agentos.webui.app
# Or
uvicorn agentos.webui.app:app --host 0.0.0.0 --port 8080
```

## API Endpoints

### 1. GET /api/governance/summary

Get governance system overview including capabilities, quotas, and recent events.

**curl:**
```bash
curl http://localhost:8080/api/governance/summary
```

**httpie:**
```bash
http GET http://localhost:8080/api/governance/summary
```

**Expected Response:**
```json
{
  "capabilities": {
    "total": 5,
    "by_trust_tier": {
      "local_extension": 3,
      "cloud_mcp": 2
    },
    "by_source": {
      "extension": 3,
      "mcp": 2
    }
  },
  "quota": {
    "warnings": 1,
    "denied": 0,
    "total_tracked": 3
  },
  "recent_events": [
    {
      "timestamp": "2024-01-15T10:30:00Z",
      "event_type": "quota_warning",
      "capability_id": "ext:tools.postman:get",
      "message": "Calls per minute limit reached: 85/100"
    }
  ]
}
```

### 2. GET /api/governance/quotas

Get quota status for all tracked capabilities.

**curl:**
```bash
curl http://localhost:8080/api/governance/quotas
```

**httpie:**
```bash
http GET http://localhost:8080/api/governance/quotas
```

**Expected Response:**
```json
{
  "quotas": [
    {
      "capability_id": "quota_1",
      "tool_id": "ext:tools.postman:get",
      "trust_tier": "local_extension",
      "quota": {
        "calls_per_minute": {
          "limit": 100,
          "used": 85,
          "usage_percent": 85.0
        },
        "max_concurrent": {
          "limit": 5,
          "used": 2,
          "usage_percent": 40.0
        }
      },
      "status": "warning",
      "last_triggered": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### 3. GET /api/governance/trust-tiers

Get trust tier configurations and policies.

**curl:**
```bash
curl http://localhost:8080/api/governance/trust-tiers
```

**httpie:**
```bash
http GET http://localhost:8080/api/governance/trust-tiers
```

**Expected Response:**
```json
{
  "tiers": [
    {
      "tier": "T0",
      "name": "Local Extension",
      "capabilities": [
        "ext:tools.postman:get",
        "ext:tools.postman:post"
      ],
      "count": 2,
      "default_policy": {
        "risk_level": "LOW",
        "requires_admin_token": false,
        "default_quota_profile": {
          "calls_per_minute": 1000,
          "max_concurrent": 10,
          "max_runtime_ms": 300000
        }
      }
    },
    {
      "tier": "T3",
      "name": "Cloud MCP",
      "capabilities": [
        "mcp:remote_server:dangerous_tool"
      ],
      "count": 1,
      "default_policy": {
        "risk_level": "HIGH",
        "requires_admin_token": true,
        "default_quota_profile": {
          "calls_per_minute": 100,
          "max_concurrent": 2,
          "max_runtime_ms": 60000
        }
      }
    }
  ]
}
```

### 4. GET /api/governance/provenance/{invocation_id}

Get provenance information for a specific tool invocation.

**curl:**
```bash
curl http://localhost:8080/api/governance/provenance/inv_abc123xyz
```

**httpie:**
```bash
http GET http://localhost:8080/api/governance/provenance/inv_abc123xyz
```

**Expected Response:**
```json
{
  "provenance": {
    "capability_id": "ext:tools.postman:get",
    "tool_id": "ext:tools.postman:get",
    "capability_type": "extension",
    "source_id": "tools.postman",
    "execution_env": {
      "hostname": "macbook-pro",
      "pid": 12345,
      "container_id": null
    },
    "trust_tier": "T0",
    "timestamp": "2024-01-15T10:30:00Z",
    "invocation_id": "inv_abc123xyz"
  },
  "audit_chain": [
    {
      "event_type": "tool_invocation_start",
      "timestamp": "2024-01-15T10:30:00Z",
      "gate": null,
      "result": "pending"
    },
    {
      "event_type": "tool_invocation_end",
      "timestamp": "2024-01-15T10:30:05Z",
      "gate": null,
      "result": "success"
    }
  ]
}
```

**Error Response (404 - Not Found):**
```bash
curl http://localhost:8080/api/governance/provenance/non_existent_id
```

```json
{
  "ok": false,
  "data": null,
  "error": "Provenance not found for invocation: non_existent_id",
  "hint": "Check the invocation ID and ensure the invocation has completed",
  "reason_code": "NOT_FOUND"
}
```

## Testing with Different States

### Test Empty Registry
```bash
# When no capabilities are registered
curl http://localhost:8080/api/governance/summary
# Returns: capabilities.total = 0
```

### Test Quota Warning State
```bash
# After consuming 85% of quota
curl http://localhost:8080/api/governance/quotas
# Returns: status = "warning" for affected quota
```

### Test Quota Denied State
```bash
# After exceeding quota (>100%)
curl http://localhost:8080/api/governance/quotas
# Returns: status = "denied" for affected quota
```

## Error Handling

All endpoints return standardized error responses:

```json
{
  "ok": false,
  "data": null,
  "error": "Human-readable error message",
  "hint": "User-actionable hint",
  "reason_code": "ERROR_CODE"
}
```

Common reason codes:
- `NOT_FOUND` - Resource not found (404)
- `INTERNAL_ERROR` - Server error (500)

## Read-Only Guarantee

All these endpoints are **read-only** and do not modify any state:
- ✅ No data mutations
- ✅ No quota updates
- ✅ No trust tier changes
- ✅ No capability modifications

Attempting non-GET methods returns 405 Method Not Allowed:
```bash
curl -X POST http://localhost:8080/api/governance/summary
# Returns: 405 Method Not Allowed
```

## Performance Notes

- **Caching**: Capability registry uses 60-second TTL cache
- **Database**: Provenance queries use SQLite LIKE searches (indexed)
- **Graceful Degradation**: If audit database is unavailable, endpoints return empty arrays instead of errors

## Integration with WebUI

These APIs are designed for WebUI visualization:
- `/summary` - Overview dashboard card
- `/quotas` - Quota monitoring table
- `/trust-tiers` - Trust tier configuration view
- `/provenance/{id}` - Provenance trace viewer

See PR-1 documentation for WebUI integration details.
