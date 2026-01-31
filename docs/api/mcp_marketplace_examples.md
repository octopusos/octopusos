# MCP Marketplace API Examples

This document provides `curl` examples for testing the 4 MCP Marketplace API endpoints.

## Prerequisites

Start the AgentOS WebUI server:

```bash
python -m agentos.webui.app
```

Server runs at: `http://localhost:8000`

---

## 1. List MCP Packages (Discover)

### List all packages

```bash
curl -X GET "http://localhost:8000/api/mcp/marketplace/packages"
```

**Expected Response:**
```json
{
  "packages": [
    {
      "package_id": "agentos.official/echo-math",
      "name": "Echo Math Calculator",
      "version": "1.0.0",
      "author": "AgentOS Team",
      "description": "Simple echo and math tools for testing and demonstrations",
      "tools_count": 2,
      "transport": "stdio",
      "recommended_trust_tier": "T0",
      "requires_admin_token": false,
      "is_connected": false,
      "tags": ["official", "testing", "math", "utilities"]
    }
  ],
  "total": 3
}
```

### Search packages

```bash
curl -X GET "http://localhost:8000/api/mcp/marketplace/packages?search=github"
```

### Filter by tag

```bash
curl -X GET "http://localhost:8000/api/mcp/marketplace/packages?tag=local"
```

### Show only connected packages

```bash
curl -X GET "http://localhost:8000/api/mcp/marketplace/packages?connected_only=true"
```

---

## 2. Get Package Details (Inspect)

```bash
curl -X GET "http://localhost:8000/api/mcp/marketplace/packages/agentos.official/echo-math"
```

**Expected Response:**
```json
{
  "ok": true,
  "data": {
    "package_id": "agentos.official/echo-math",
    "name": "Echo Math Calculator",
    "version": "1.0.0",
    "author": "AgentOS Team",
    "description": "Simple echo and math tools for testing and demonstrations",
    "long_description": "A minimal MCP server providing echo and basic arithmetic operations.\nPerfect for testing MCP integration without side effects.\n",
    "tools": [
      {
        "name": "echo",
        "description": "Echo back the input message",
        "input_schema": {
          "type": "object",
          "properties": {
            "message": {
              "type": "string",
              "description": "Message to echo"
            }
          },
          "required": ["message"]
        },
        "side_effects": [],
        "requires_confirmation": false
      },
      {
        "name": "add",
        "description": "Add two numbers",
        "input_schema": {
          "type": "object",
          "properties": {
            "a": {"type": "number", "description": "First number"},
            "b": {"type": "number", "description": "Second number"}
          },
          "required": ["a", "b"]
        },
        "side_effects": [],
        "requires_confirmation": false
      }
    ],
    "declared_side_effects": [],
    "transport": "stdio",
    "connection_template": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-echo"],
      "env": {}
    },
    "recommended_trust_tier": "T0",
    "recommended_quota_profile": "loose",
    "requires_admin_token": false,
    "homepage": "https://github.com/modelcontextprotocol/servers/tree/main/src/echo",
    "repository": "https://github.com/modelcontextprotocol/servers",
    "license": "MIT",
    "tags": ["official", "testing", "math", "utilities"],
    "is_connected": false,
    "connected_at": null
  }
}
```

---

## 3. Get Governance Preview (Approve)

```bash
curl -X GET "http://localhost:8000/api/mcp/marketplace/governance-preview/agentos.official/echo-math"
```

**Expected Response:**
```json
{
  "ok": true,
  "data": {
    "package_id": "agentos.official/echo-math",
    "inferred_trust_tier": "T1",
    "inferred_risk_level": "MEDIUM",
    "default_quota": {
      "calls_per_minute": 100,
      "max_concurrent": 10,
      "max_runtime_ms": 300000
    },
    "requires_admin_token_for": [],
    "gate_warnings": [
      "No side effects declared - may be blocked by Policy Gate"
    ],
    "audit_level": "standard"
  }
}
```

### High-risk package example (GitHub)

```bash
curl -X GET "http://localhost:8000/api/mcp/marketplace/governance-preview/smithery.ai/github"
```

**Expected Response:**
```json
{
  "ok": true,
  "data": {
    "package_id": "smithery.ai/github",
    "inferred_trust_tier": "T1",
    "inferred_risk_level": "MEDIUM",
    "default_quota": {
      "calls_per_minute": 100,
      "max_concurrent": 10,
      "max_runtime_ms": 300000
    },
    "requires_admin_token_for": ["side_effects"],
    "gate_warnings": [],
    "audit_level": "standard"
  }
}
```

---

## 4. Attach MCP Package (Attach)

### Basic attach

```bash
curl -X POST "http://localhost:8000/api/mcp/marketplace/attach" \
  -H "Content-Type: application/json" \
  -d '{
    "package_id": "agentos.official/echo-math"
  }'
```

**Expected Response:**
```json
{
  "ok": true,
  "data": {
    "server_id": "echo-math",
    "status": "attached",
    "enabled": false,
    "trust_tier": "T0",
    "audit_id": "audit_abc123",
    "warnings": [
      "MCP is attached but not enabled. Use CLI to enable."
    ],
    "next_steps": [
      "Review the MCP in Capabilities → MCP",
      "Enable using: agentos mcp enable echo-math"
    ]
  }
}
```

### Attach with trust tier override

```bash
curl -X POST "http://localhost:8000/api/mcp/marketplace/attach" \
  -H "Content-Type: application/json" \
  -d '{
    "package_id": "community/filesystem",
    "override_trust_tier": "T2"
  }'
```

**Expected Response:**
```json
{
  "ok": true,
  "data": {
    "server_id": "filesystem",
    "status": "attached",
    "enabled": false,
    "trust_tier": "T2",
    "audit_id": "audit_def456",
    "warnings": [
      "⚠️ Trust Tier overridden: T1 → T2",
      "MCP is attached but not enabled. Use CLI to enable.",
      "This MCP declares side effects. Admin token may be required.",
      "Trust Tier T2 - requires careful approval before enabling."
    ],
    "next_steps": [
      "Review the MCP in Capabilities → MCP",
      "Enable using: agentos mcp enable filesystem"
    ]
  }
}
```

### Attach with custom config

```bash
curl -X POST "http://localhost:8000/api/mcp/marketplace/attach" \
  -H "Content-Type: application/json" \
  -d '{
    "package_id": "community/filesystem",
    "custom_config": {
      "command": "python",
      "args": ["-m", "my_custom_server"],
      "env": {
        "CUSTOM_VAR": "value"
      }
    }
  }'
```

---

## Error Handling

### Package not found

```bash
curl -X GET "http://localhost:8000/api/mcp/marketplace/packages/nonexistent/package"
```

**Response (404):**
```json
{
  "ok": false,
  "data": null,
  "error": "Package not found: nonexistent/package",
  "hint": null,
  "reason_code": "INTERNAL_ERROR"
}
```

### Package already connected

```bash
# First attach
curl -X POST "http://localhost:8000/api/mcp/marketplace/attach" \
  -H "Content-Type: application/json" \
  -d '{"package_id": "agentos.official/echo-math"}'

# Try to attach again
curl -X POST "http://localhost:8000/api/mcp/marketplace/attach" \
  -H "Content-Type: application/json" \
  -d '{"package_id": "agentos.official/echo-math"}'
```

**Response (400):**
```json
{
  "ok": false,
  "data": null,
  "error": "Package already connected: agentos.official/echo-math",
  "hint": null,
  "reason_code": "INTERNAL_ERROR"
}
```

---

## Security Validation

### Verify MCP is disabled after attach

After attaching, check the config file:

```bash
cat ~/.agentos/mcp/echo-math.yaml
```

**Expected:**
```yaml
server_id: echo-math
name: Echo Math Calculator
transport: stdio
enabled: false  # ← CRITICAL: Must be false
trust_tier: T0
config:
  command: npx
  args:
    - "-y"
    - "@modelcontextprotocol/server-echo"
  env: {}
metadata:
  package_id: agentos.official/echo-math
  version: 1.0.0
  attached_at: "2026-01-31T12:00:00"
```

### Enable MCP (requires explicit action)

```bash
# This would be a CLI command (not API)
agentos mcp enable echo-math
```

---

## Notes

1. **All attach operations create DISABLED MCPs** - This is a security requirement
2. **Audit events are emitted** - Check logs for `mcp_attached` events
3. **Trust tier can be overridden** - But warnings are shown
4. **Next steps are always provided** - Guide users to enable safely
