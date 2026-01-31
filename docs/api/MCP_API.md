# MCP Management API

API endpoints for observing and managing MCP (Model Context Protocol) servers and tools.

Part of PR-4: WebUI MCP Management Page & API

## Overview

The MCP Management API provides observability and control over MCP servers integrated with AgentOS. It allows:

- Viewing server status and health
- Browsing available tools
- Testing tool invocations
- Refreshing server connections

All tool invocations go through the complete 6-layer security gate system.

## Base URL

```
/api/mcp
```

## Authentication

Most endpoints are read-only and don't require authentication. Tool invocation requires:
- **Project ID**: Required for auditing (all tool calls must be bound to a project)
- **Admin Token**: Required for CRITICAL risk level tools (via `X-Admin-Token` header)

## Endpoints

### GET /api/mcp/servers

List all MCP servers with their status and health.

**Response:**

```json
[
  {
    "id": "postman",
    "enabled": true,
    "status": "connected",
    "health": "healthy",
    "last_seen": "2025-01-30T10:30:00Z",
    "tool_count": 5,
    "error_message": null
  },
  {
    "id": "filesystem",
    "enabled": true,
    "status": "disconnected",
    "health": "unhealthy",
    "last_seen": null,
    "tool_count": 0,
    "error_message": "Not connected"
  }
]
```

**Response Fields:**

- `id` (string): Server identifier
- `enabled` (boolean): Whether server is enabled in config
- `status` (string): Connection status
  - `connected`: Server is connected and responsive
  - `disconnected`: Server is not connected
  - `disabled`: Server is disabled in config
  - `error`: Server encountered an error
- `health` (string): Health status
  - `healthy`: Server is functioning normally
  - `degraded`: Server is connected but experiencing issues
  - `unhealthy`: Server is not functioning
  - `n/a`: Health not applicable (disabled servers)
- `last_seen` (string, nullable): ISO timestamp of last successful communication
- `tool_count` (integer): Number of tools available from this server
- `error_message` (string, nullable): Error message if status is error

**Status Codes:**

- `200 OK`: Success
- `500 Internal Server Error`: Server error

---

### POST /api/mcp/servers/refresh

Refresh MCP server connections and tool listings.

This triggers a full refresh of the capability cache:
- Reconnects to all enabled MCP servers
- Re-fetches tool listings from each server
- Updates the unified tool cache

**Response:**

```json
{
  "message": "Successfully refreshed 2 MCP servers",
  "refreshed_count": 2
}
```

**Response Fields:**

- `message` (string): Human-readable result message
- `refreshed_count` (integer): Number of servers successfully refreshed

**Status Codes:**

- `200 OK`: Success
- `500 Internal Server Error`: Refresh failed

---

### GET /api/mcp/tools

List all MCP tools with optional filtering.

**Query Parameters:**

- `server_id` (string, optional): Filter by specific MCP server
- `risk_level_max` (string, optional): Maximum risk level to include
  - Valid values: `LOW`, `MED`, `HIGH`, `CRITICAL`
  - Example: `risk_level_max=MED` includes LOW and MED tools only

**Response:**

```json
[
  {
    "tool_id": "mcp:postman:get_request",
    "server_id": "postman",
    "name": "get_request",
    "description": "Make an HTTP GET request",
    "risk_level": "MED",
    "side_effects": ["network.http"],
    "requires_admin_token": false,
    "input_schema": {
      "type": "object",
      "properties": {
        "url": {
          "type": "string",
          "description": "URL to request"
        }
      },
      "required": ["url"]
    }
  },
  {
    "tool_id": "mcp:postman:post_request",
    "server_id": "postman",
    "name": "post_request",
    "description": "Make an HTTP POST request",
    "risk_level": "HIGH",
    "side_effects": ["network.http", "fs.write"],
    "requires_admin_token": false,
    "input_schema": {
      "type": "object",
      "properties": {
        "url": {"type": "string"},
        "body": {"type": "object"}
      },
      "required": ["url"]
    }
  }
]
```

**Response Fields:**

- `tool_id` (string): Unique tool identifier (format: `mcp:<server>:<tool>`)
- `server_id` (string): MCP server identifier
- `name` (string): Tool name
- `description` (string): Tool description
- `risk_level` (string): Risk level classification
  - `LOW`: Read-only operations, no side effects
  - `MED`: Limited side effects, reversible
  - `HIGH`: Significant side effects (write/delete, network)
  - `CRITICAL`: Dangerous operations (payments, cloud resources)
- `side_effects` (array of strings): Declared side effects
  - Examples: `fs.write`, `network.http`, `cloud.resource_create`, `payments`
- `requires_admin_token` (boolean): Whether admin token is required for invocation
- `input_schema` (object): JSON Schema describing tool inputs

**Status Codes:**

- `200 OK`: Success
- `400 Bad Request`: Invalid risk_level_max value
- `500 Internal Server Error`: Server error

**Example Requests:**

```bash
# List all MCP tools
GET /api/mcp/tools

# List tools from specific server
GET /api/mcp/tools?server_id=postman

# List only low-risk tools
GET /api/mcp/tools?risk_level_max=LOW

# Combine filters
GET /api/mcp/tools?server_id=postman&risk_level_max=MED
```

---

### POST /api/mcp/call

Test call an MCP tool with full security gates.

This endpoint allows testing MCP tool invocations through the WebUI. All calls go through the complete 6-layer security gate system:

1. **Tool Enablement Gate**: Tool must be enabled
2. **Risk Level Gate**: Risk level must be acceptable
3. **Side Effect Gate**: Side effects must be allowed
4. **Project Binding Gate**: Must provide valid project_id
5. **Spec Freezing Gate**: Task spec must be frozen (if task_id provided)
6. **Admin Token Gate**: Admin token required for CRITICAL risk tools

**Request Body:**

```json
{
  "tool_id": "mcp:postman:get_request",
  "inputs": {
    "url": "https://api.example.com/data"
  },
  "project_id": "proj_abc123",
  "task_id": "task_xyz789",
  "admin_token": "secret_token_here"
}
```

**Request Fields:**

- `tool_id` (string, required): Tool identifier (must start with `mcp:`)
- `inputs` (object, required): Tool input parameters (must match tool's input_schema)
- `project_id` (string, required): Project ID for auditing
- `task_id` (string, optional): Task ID if call is part of a task
- `admin_token` (string, optional): Admin token for CRITICAL risk operations

**Response (Success):**

```json
{
  "success": true,
  "invocation_id": "inv_abc123def456",
  "payload": {
    "status": 200,
    "body": "{\"data\": \"example\"}"
  },
  "error": null,
  "duration_ms": 1250,
  "declared_side_effects": ["network.http"]
}
```

**Response (Failure):**

```json
{
  "success": false,
  "invocation_id": "inv_abc123def456",
  "payload": null,
  "error": "Policy violation: Tool requires admin_token",
  "duration_ms": 5,
  "declared_side_effects": []
}
```

**Response Fields:**

- `success` (boolean): Whether the invocation succeeded
- `invocation_id` (string): Unique invocation identifier (for auditing)
- `payload` (any): Tool output payload (null if failed)
- `error` (string, nullable): Error message if failed
- `duration_ms` (integer): Execution duration in milliseconds
- `declared_side_effects` (array of strings): Side effects that occurred

**Status Codes:**

- `200 OK`: Call completed (check `success` field for actual result)
- `400 Bad Request`: Invalid request (bad tool_id format, missing required fields)
- `500 Internal Server Error`: Unexpected server error

**Policy Violation Examples:**

```json
// Tool disabled
{
  "success": false,
  "error": "Policy violation: Tool is disabled",
  ...
}

// Missing admin token
{
  "success": false,
  "error": "Policy violation: Tool requires admin_token",
  ...
}

// Missing project binding
{
  "success": false,
  "error": "Policy violation: Tool invocation must be bound to a project",
  ...
}
```

**Example Requests:**

```bash
# Simple GET request
curl -X POST /api/mcp/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool_id": "mcp:postman:get_request",
    "inputs": {"url": "https://api.example.com"},
    "project_id": "proj_123"
  }'

# Critical operation with admin token
curl -X POST /api/mcp/call \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: your-admin-token" \
  -d '{
    "tool_id": "mcp:cloud:create_resource",
    "inputs": {"type": "storage", "size": "10GB"},
    "project_id": "proj_123",
    "admin_token": "your-admin-token"
  }'
```

---

### GET /api/mcp/health

MCP subsystem health check.

**Response:**

```json
{
  "status": "healthy",
  "connected_servers": 2,
  "available_tools": 15
}
```

**Response Fields:**

- `status` (string): Overall health status
  - `healthy`: MCP subsystem is functioning normally
  - `degraded`: Some servers connected but limited functionality
  - `unhealthy`: No servers connected or critical issues
- `connected_servers` (integer): Number of MCP servers currently connected
- `available_tools` (integer): Total number of MCP tools available

**Status Codes:**

- `200 OK`: Always returns 200 (check `status` field for health)

---

## Security & Auditing

### Security Gates

All tool invocations through `/api/mcp/call` go through 6 security gates:

1. **Tool Enablement Gate**
   - Checks if tool's source (extension/server) is enabled
   - Prevents disabled tools from being invoked

2. **Risk Level Gate**
   - Validates risk level is acceptable
   - CRITICAL tools require admin token

3. **Side Effect Gate**
   - Checks if tool's side effects are allowed
   - Can filter out dangerous operations

4. **Project Binding Gate**
   - Requires all tool calls to be bound to a project
   - Enables proper auditing and tracking

5. **Spec Freezing Gate**
   - For task-bound calls, validates spec is frozen
   - Prevents unauthorized plan modifications

6. **Admin Token Gate**
   - CRITICAL risk tools require admin approval
   - Token validated via `X-Admin-Token` header or request body

### Audit Trail

All tool invocations are audited:

- **Before**: `tool_invocation_start` event logged
- **After**: `tool_invocation_end` event logged
- **Policy Violations**: `policy_violation` event logged

Audit events include:
- Invocation ID (unique identifier)
- Tool ID and metadata
- Actor (user/agent)
- Project and task IDs
- Inputs and outputs
- Duration and timestamp
- Success/failure status

## Error Handling

All endpoints use the standard AgentOS error format:

```json
{
  "ok": false,
  "data": null,
  "error": "Human-readable error message",
  "hint": "Suggestion for fixing the error",
  "reason_code": "MACHINE_READABLE_CODE"
}
```

**Common Reason Codes:**

- `INVALID_INPUT`: Invalid request parameters
- `NOT_FOUND`: Resource not found
- `POLICY_VIOLATION`: Security policy violation
- `INTERNAL_ERROR`: Unexpected server error

## Usage Examples

### Example 1: Browse Available MCP Tools

```bash
# 1. Check MCP health
curl /api/mcp/health

# 2. List all MCP servers
curl /api/mcp/servers

# 3. List tools from specific server
curl '/api/mcp/tools?server_id=postman'

# 4. Filter by risk level
curl '/api/mcp/tools?risk_level_max=MED'
```

### Example 2: Test Tool Invocation

```bash
# 1. Find tool ID
curl /api/mcp/tools | jq '.[] | select(.name == "get_request")'

# 2. Prepare request
TOOL_ID="mcp:postman:get_request"
PROJECT_ID="proj_test_123"

# 3. Invoke tool
curl -X POST /api/mcp/call \
  -H "Content-Type: application/json" \
  -d "{
    \"tool_id\": \"$TOOL_ID\",
    \"inputs\": {\"url\": \"https://httpbin.org/get\"},
    \"project_id\": \"$PROJECT_ID\"
  }"
```

### Example 3: Refresh Servers After Config Change

```bash
# 1. Edit MCP config
vi ~/.agentos/mcp_servers.yaml

# 2. Refresh servers
curl -X POST /api/mcp/servers/refresh

# 3. Verify new tools are available
curl /api/mcp/tools
```

## Integration with WebUI

The MCP Management API is designed to power a WebUI interface with:

### Server Status Page
- Real-time server status display
- Connection health indicators
- Tool count per server
- Refresh button

### Tool Browser Page
- Searchable tool list
- Filter by server and risk level
- Tool detail view with schema
- Side effect indicators

### Tool Testing Page
- Interactive form for tool invocation
- Input schema validation
- Real-time result display
- Error handling with suggestions

## Related Documentation

- [Capability Abstraction Layer](../capabilities/CAPABILITY_ABSTRACTION.md)
- [MCP Integration Guide](../mcp/INTEGRATION.md)
- [Security Gates Documentation](../security/SECURITY_GATES.md)
- [Audit System](../audit/AUDIT_SYSTEM.md)

## Changelog

### v0.3.2 (PR-4)
- Initial MCP Management API implementation
- Server status and health endpoints
- Tool browsing with filtering
- Tool invocation with security gates
- Comprehensive audit integration
