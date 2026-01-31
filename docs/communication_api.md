# Communication API Documentation

**Version:** 1.0
**Status:** Implemented
**Module:** `agentos.webui.api.communication`

---

## Overview

The Communication API provides REST endpoints for managing and monitoring external communication operations through CommunicationOS. It enables:

- Policy configuration retrieval
- Audit log querying and filtering
- Web search operations
- Web fetch operations
- Service status monitoring

All operations are secured with policy enforcement, rate limiting, and comprehensive audit logging.

---

## Base URL

All endpoints are prefixed with `/api/communication`.

---

## Authentication

Currently, the Communication API uses the same authentication mechanism as other AgentOS APIs. Authentication requirements will be enforced based on the system configuration.

---

## Endpoints

### 1. Get All Policies

**Endpoint:** `GET /api/communication/policy`

**Description:** Retrieve policy configuration for all registered connectors.

**Response:**
```json
{
  "ok": true,
  "data": {
    "web_search": {
      "name": "default_web_search",
      "connector_type": "web_search",
      "enabled": true,
      "allowed_operations": ["search"],
      "blocked_domains": ["localhost", "127.0.0.1", "0.0.0.0"],
      "allowed_domains": [],
      "require_approval": false,
      "rate_limit_per_minute": 30,
      "max_response_size_mb": 5,
      "timeout_seconds": 30,
      "sanitize_inputs": true,
      "sanitize_outputs": true
    },
    "web_fetch": {
      "name": "default_web_fetch",
      "connector_type": "web_fetch",
      "enabled": true,
      "allowed_operations": ["fetch", "download"],
      "blocked_domains": ["localhost", "127.0.0.1", "0.0.0.0"],
      "allowed_domains": [],
      "require_approval": false,
      "rate_limit_per_minute": 20,
      "max_response_size_mb": 10,
      "timeout_seconds": 60,
      "sanitize_inputs": true,
      "sanitize_outputs": true
    }
  }
}
```

---

### 2. Get Connector Policy

**Endpoint:** `GET /api/communication/policy/{connector_type}`

**Description:** Retrieve policy configuration for a specific connector type.

**Path Parameters:**
- `connector_type` (string, required): Type of connector (e.g., `web_search`, `web_fetch`, `rss`, `email_smtp`, `slack`)

**Example Request:**
```bash
curl -X GET "http://localhost:8080/api/communication/policy/web_search"
```

**Response:**
```json
{
  "ok": true,
  "data": {
    "name": "default_web_search",
    "connector_type": "web_search",
    "enabled": true,
    "allowed_operations": ["search"],
    "blocked_domains": ["localhost", "127.0.0.1"],
    "rate_limit_per_minute": 30,
    "max_response_size_mb": 5,
    "timeout_seconds": 30
  }
}
```

**Error Response (Invalid Connector Type):**
```json
{
  "ok": false,
  "error": "Invalid connector type: invalid_type",
  "hint": "Valid types: web_search, web_fetch, rss, email_smtp, slack, custom",
  "reason_code": "INVALID_INPUT"
}
```

---

### 3. List Audit Records

**Endpoint:** `GET /api/communication/audits`

**Description:** List audit records with optional filtering and pagination.

**Query Parameters:**
- `connector_type` (string, optional): Filter by connector type
- `operation` (string, optional): Filter by operation name
- `status` (string, optional): Filter by request status (e.g., `success`, `failed`, `denied`)
- `start_date` (string, optional): Start date in ISO 8601 format
- `end_date` (string, optional): End date in ISO 8601 format
- `limit` (integer, optional): Maximum number of results (default: 100, max: 1000)

**Example Request:**
```bash
curl -X GET "http://localhost:8080/api/communication/audits?connector_type=web_search&status=success&limit=50"
```

**Response:**
```json
{
  "ok": true,
  "data": {
    "audits": [
      {
        "id": "ev-abc123def456",
        "request_id": "comm-xyz789",
        "connector_type": "web_search",
        "operation": "search",
        "status": "success",
        "risk_level": "low",
        "created_at": "2026-01-30T10:30:00Z"
      }
    ],
    "total": 1,
    "filters_applied": {
      "connector_type": "web_search",
      "operation": null,
      "status": "success",
      "start_date": null,
      "end_date": null,
      "limit": 50
    }
  }
}
```

---

### 4. Get Audit Detail

**Endpoint:** `GET /api/communication/audits/{audit_id}`

**Description:** Get detailed information for a specific audit record.

**Path Parameters:**
- `audit_id` (string, required): Audit record ID

**Example Request:**
```bash
curl -X GET "http://localhost:8080/api/communication/audits/ev-abc123def456"
```

**Response:**
```json
{
  "ok": true,
  "data": {
    "id": "ev-abc123def456",
    "request_id": "comm-xyz789",
    "connector_type": "web_search",
    "operation": "search",
    "request_summary": {
      "connector_type": "web_search",
      "operation": "search",
      "timestamp": "2026-01-30T10:30:00Z",
      "params": {
        "query": "artificial intelligence news"
      }
    },
    "response_summary": {
      "status": "success",
      "timestamp": "2026-01-30T10:30:02Z",
      "has_data": true,
      "data_type": "dict",
      "metadata": {
        "content_type": "application/json"
      }
    },
    "status": "success",
    "metadata": {
      "risk_level": "low",
      "context": {
        "task_id": "task-123",
        "session_id": "session-456"
      }
    },
    "created_at": "2026-01-30T10:30:02Z"
  }
}
```

**Error Response (Not Found):**
```json
{
  "ok": false,
  "error": "Audit record not found: ev-nonexistent",
  "hint": "Check the audit_id and ensure the record exists",
  "reason_code": "NOT_FOUND"
}
```

---

### 5. Execute Web Search

**Endpoint:** `POST /api/communication/search`

**Description:** Execute a web search operation.

**Request Body:**
```json
{
  "query": "artificial intelligence news",
  "max_results": 10,
  "context": {
    "task_id": "task-123",
    "session_id": "session-456"
  }
}
```

**Parameters:**
- `query` (string, required): Search query string
- `max_results` (integer, optional): Maximum number of results (default: 10, max: 100)
- `context` (object, optional): Additional context (task_id, session_id, etc.)

**Example Request:**
```bash
curl -X POST "http://localhost:8080/api/communication/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "artificial intelligence news",
    "max_results": 5
  }'
```

**Response:**
```json
{
  "ok": true,
  "data": {
    "request_id": "comm-abc123",
    "status": "success",
    "data": {
      "results": [
        {
          "title": "Latest AI News",
          "url": "https://example.com/ai-news",
          "snippet": "Recent developments in artificial intelligence..."
        }
      ],
      "total_results": 5
    },
    "metadata": {
      "search_time_ms": 234
    },
    "evidence_id": "ev-xyz789",
    "created_at": "2026-01-30T10:30:00Z"
  }
}
```

**Error Response (Policy Denied):**
```json
{
  "ok": false,
  "error": "Search request denied by policy",
  "hint": "Check policy configuration and domain restrictions",
  "reason_code": "AUTH_FORBIDDEN"
}
```

**Error Response (Rate Limited):**
```json
{
  "ok": false,
  "error": "Rate limit exceeded",
  "hint": "Wait before making more requests",
  "reason_code": "RATE_LIMITED"
}
```

---

### 6. Fetch Web Content

**Endpoint:** `POST /api/communication/fetch`

**Description:** Fetch content from a URL.

**Request Body:**
```json
{
  "url": "https://example.com/page",
  "timeout": 30,
  "context": {
    "task_id": "task-123",
    "session_id": "session-456"
  }
}
```

**Parameters:**
- `url` (string, required): URL to fetch
- `timeout` (integer, optional): Request timeout in seconds (default: 30, max: 120)
- `context` (object, optional): Additional context (task_id, session_id, etc.)

**Example Request:**
```bash
curl -X POST "http://localhost:8080/api/communication/fetch" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/page",
    "timeout": 30
  }'
```

**Response:**
```json
{
  "ok": true,
  "data": {
    "request_id": "comm-def456",
    "status": "success",
    "data": {
      "content": "<!DOCTYPE html>...",
      "content_type": "text/html",
      "status_code": 200,
      "content_length": 12345
    },
    "metadata": {
      "fetch_time_ms": 567
    },
    "evidence_id": "ev-ghi789",
    "created_at": "2026-01-30T10:35:00Z"
  }
}
```

**Error Response (Blocked Domain):**
```json
{
  "ok": false,
  "error": "Fetch request denied by policy",
  "hint": "Check policy configuration and domain restrictions",
  "reason_code": "AUTH_FORBIDDEN"
}
```

---

### 7. Get Service Status

**Endpoint:** `GET /api/communication/status`

**Description:** Get communication service status and statistics.

**Example Request:**
```bash
curl -X GET "http://localhost:8080/api/communication/status"
```

**Response:**
```json
{
  "ok": true,
  "data": {
    "status": "operational",
    "connectors": {
      "web_search": {
        "type": "web_search",
        "enabled": true,
        "operations": ["search"],
        "rate_limit": 30
      },
      "web_fetch": {
        "type": "web_fetch",
        "enabled": true,
        "operations": ["fetch", "download"],
        "rate_limit": 20
      }
    },
    "statistics": {
      "total_requests": 1234,
      "success_rate": 95.6,
      "by_connector": {
        "web_search": 567,
        "web_fetch": 667
      }
    },
    "timestamp": "2026-01-30T10:40:00Z"
  }
}
```

---

## Error Handling

All endpoints follow the AgentOS API contract for error responses:

```json
{
  "ok": false,
  "data": null,
  "error": "Human-readable error message",
  "hint": "User-actionable hint for fixing the error",
  "reason_code": "MACHINE_READABLE_CODE"
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_INPUT` | 400 | Validation error in request parameters |
| `NOT_FOUND` | 404 | Resource not found |
| `AUTH_FORBIDDEN` | 403 | Request denied by policy |
| `RATE_LIMITED` | 429 | Rate limit exceeded |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

---

## Security Features

### 1. Policy Enforcement
- Domain whitelisting/blacklisting
- Operation restrictions
- Approval requirements

### 2. Rate Limiting
- Configurable per-connector limits
- Prevents abuse and DoS attacks

### 3. SSRF Protection
- Blocks private IP ranges
- Prevents localhost access
- Validates URL schemes

### 4. Input/Output Sanitization
- Configurable sanitization rules
- Prevents injection attacks
- Filters sensitive data

### 5. Comprehensive Auditing
- All operations logged
- Full request/response summaries
- Tamper-proof evidence records

---

## Integration Example

### Python Client

```python
import httpx
import asyncio

async def search_web(query: str, max_results: int = 10):
    """Execute a web search."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8080/api/communication/search",
            json={
                "query": query,
                "max_results": max_results,
                "context": {
                    "source": "python_client"
                }
            }
        )
        return response.json()

async def fetch_url(url: str):
    """Fetch content from a URL."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8080/api/communication/fetch",
            json={
                "url": url,
                "timeout": 30
            }
        )
        return response.json()

async def get_audit_logs(connector_type: str = None, limit: int = 100):
    """Get audit logs with optional filtering."""
    async with httpx.AsyncClient() as client:
        params = {"limit": limit}
        if connector_type:
            params["connector_type"] = connector_type

        response = await client.get(
            "http://localhost:8080/api/communication/audits",
            params=params
        )
        return response.json()

# Example usage
async def main():
    # Search the web
    search_result = await search_web("artificial intelligence")
    print(f"Search results: {search_result}")

    # Fetch a URL
    fetch_result = await fetch_url("https://example.com")
    print(f"Fetched content: {fetch_result}")

    # Get audit logs
    audits = await get_audit_logs(connector_type="web_search")
    print(f"Audit logs: {audits}")

asyncio.run(main())
```

### JavaScript/TypeScript Client

```typescript
interface SearchRequest {
  query: string;
  max_results?: number;
  context?: Record<string, any>;
}

interface FetchRequest {
  url: string;
  timeout?: number;
  context?: Record<string, any>;
}

class CommunicationClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://localhost:8080") {
    this.baseUrl = baseUrl;
  }

  async search(request: SearchRequest) {
    const response = await fetch(`${this.baseUrl}/api/communication/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    return await response.json();
  }

  async fetch(request: FetchRequest) {
    const response = await fetch(`${this.baseUrl}/api/communication/fetch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    return await response.json();
  }

  async getAudits(filters?: {
    connector_type?: string;
    status?: string;
    limit?: number;
  }) {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined) {
          params.append(key, String(value));
        }
      });
    }

    const response = await fetch(
      `${this.baseUrl}/api/communication/audits?${params}`
    );
    return await response.json();
  }

  async getStatus() {
    const response = await fetch(`${this.baseUrl}/api/communication/status`);
    return await response.json();
  }
}

// Example usage
const client = new CommunicationClient();

// Search the web
const searchResult = await client.search({
  query: "artificial intelligence",
  max_results: 10,
});

// Fetch a URL
const fetchResult = await client.fetch({
  url: "https://example.com",
  timeout: 30,
});

// Get audit logs
const audits = await client.getAudits({
  connector_type: "web_search",
  limit: 50,
});

// Get service status
const status = await client.getStatus();
```

---

## Testing

The Communication API includes comprehensive tests. Run the test suite:

```bash
python test_communication_api.py
```

All tests validate:
- API module structure
- Router configuration
- Endpoint definitions
- Pydantic model validation
- API contract integration
- Service initialization

---

## Dependencies

The Communication API requires the following dependencies:

- `fastapi` - Web framework
- `pydantic` - Data validation
- `httpx` - HTTP client (for web connectors)
- `beautifulsoup4` - HTML parsing (for web fetch)

Install dependencies:
```bash
pip install fastapi pydantic httpx beautifulsoup4
```

---

## Future Enhancements

1. **Additional Connectors**
   - RSS feed reader
   - Email SMTP sender
   - Slack integration

2. **Enhanced Filtering**
   - Advanced audit search
   - Multi-field sorting
   - Date range presets

3. **Real-time Monitoring**
   - WebSocket support for live updates
   - Real-time audit streaming

4. **Export Capabilities**
   - CSV/JSON export for audits
   - Report generation

5. **Policy Management UI**
   - Web interface for policy configuration
   - Visual policy editor

---

## Support

For issues, questions, or contributions, please refer to the main AgentOS documentation.
