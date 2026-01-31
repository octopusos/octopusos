# MCP Quick Start Guide

This guide shows you how to get started with Model Context Protocol (MCP) integration in AgentOS.

## Prerequisites

- Node.js (for running MCP servers)
- Python 3.9+ (for AgentOS)
- AgentOS installed and configured

## 1. Configure MCP Servers

Create or edit `~/.agentos/mcp_servers.yaml`:

```yaml
mcp_servers:
  # Echo/Math Demo Server (low-risk testing)
  - id: echo-math
    enabled: true
    transport: stdio
    command: ["node", "/path/to/AgentOS/servers/echo-math-mcp/index.js"]
    allow_tools: []  # Empty = allow all
    deny_side_effect_tags: []
    timeout_ms: 5000
```

Replace `/path/to/AgentOS` with your actual project path.

## 2. Start AgentOS

```bash
python3 -m agentos.webui.app
```

The system will automatically:
- Load MCP server configurations
- Connect to enabled MCP servers
- Discover available tools
- Register them in the unified capability registry

## 3. Verify MCP Integration

### List Available Tools

```bash
curl http://localhost:8000/api/capabilities/tools | jq '.[] | select(.source_type == "mcp")'
```

You should see tools from the echo-math server:
- `mcp:echo-math:echo`
- `mcp:echo-math:sum`
- `mcp:echo-math:multiply`

### Check MCP Server Status

```bash
curl http://localhost:8000/api/mcp/status | jq
```

## 4. Test Tool Invocation

### Echo Tool

```bash
curl -X POST http://localhost:8000/api/capabilities/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "tool_id": "mcp:echo-math:echo",
    "invocation_id": "test_001",
    "task_id": "test_task",
    "project_id": "test_project",
    "spec_frozen": true,
    "spec_hash": "test",
    "mode": "execution",
    "inputs": {"text": "hello world"},
    "actor": "test@example.com"
  }'
```

### Sum Tool

```bash
curl -X POST http://localhost:8000/api/capabilities/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "tool_id": "mcp:echo-math:sum",
    "invocation_id": "test_002",
    "task_id": "test_task",
    "project_id": "test_project",
    "spec_frozen": true,
    "spec_hash": "test",
    "mode": "execution",
    "inputs": {"a": 10, "b": 20},
    "actor": "test@example.com"
  }'
```

## 5. View Audit Trail

All MCP tool invocations are automatically audited. Check the audit trail:

```bash
# View recent audit events
curl http://localhost:8000/api/audit/events?limit=10 | jq

# Filter by tool invocations
curl http://localhost:8000/api/audit/events?event_type=tool_invocation_start | jq
```

## 6. Verify MCP Implementation

### One-Click Verification Script

Run the complete acceptance test suite with a single command:

```bash
./scripts/verify_mcp_acceptance.sh
```

This script will:
- Check your environment (Python, pytest, Node.js versions)
- Run all 61 core MCP tests across three test suites
- Display clear pass/fail status for each suite
- Provide a summary result

Expected output when all tests pass:

```
========================================
MCP Acceptance Verification
========================================

Environment:
  OS: Darwin 25.2.0
  Python: 3.14.2
  pytest: 9.0.2
  Node.js: v20.19.5

========================================
Running Test Suite: MCP Client (25 tests)
========================================
[test output...]
✅ PASSED: 25/25 tests

========================================
Running Test Suite: Policy Gates (19 tests)
========================================
[test output...]
✅ PASSED: 19/19 tests

========================================
Running Test Suite: MCP Integration (17 tests)
========================================
[test output...]
✅ PASSED: 17/17 tests

========================================
FINAL RESULT: ✅ PASS (61/61)
========================================

All MCP acceptance tests passed!
```

### Manual Test Execution

You can also run individual test suites:

```bash
# Run all MCP integration tests
python3 -m pytest tests/integration/mcp/test_mcp_full_chain.py -v

# Run specific test class
python3 -m pytest tests/integration/mcp/test_mcp_full_chain.py::TestMCPClientBasics -v

# Run with detailed output
python3 -m pytest tests/integration/mcp/test_mcp_full_chain.py -v -s
```

## Security Features

MCP integration includes comprehensive security controls:

### 1. 6-Layer Security Gates

All MCP tool invocations go through 6 security gates:
1. **Mode Check**: Planning vs Execution mode validation
2. **Spec Freeze**: Execution mode requires frozen spec
3. **Risk Level**: Risk-based filtering (LOW/MED/HIGH/CRITICAL)
4. **Side Effects**: Side effect tag validation
5. **Admin Token**: CRITICAL tools require admin approval
6. **Permissions**: Tool-specific permission checks

### 2. Tool Filtering

Configure `allow_tools` to whitelist specific tools:

```yaml
allow_tools:
  - "echo"  # Only allow echo tool
```

Configure `deny_side_effect_tags` to block dangerous operations:

```yaml
deny_side_effect_tags:
  - "fs_write"
  - "fs_delete"
  - "payments"
```

### 3. Audit Trail

Every tool invocation is logged with:
- Invocation ID
- Tool ID and source
- Actor (user)
- Inputs and outputs
- Success/failure status
- Duration
- Policy decisions

## Troubleshooting

### Server Won't Connect

Check the logs:
```bash
tail -f logs/agentos.log | grep MCP
```

Common issues:
- Node.js not installed or not in PATH
- Incorrect command path in config
- Server script has syntax errors

### Tools Not Appearing

1. Verify server is enabled in config
2. Check server status: `curl http://localhost:8000/api/mcp/status`
3. Refresh cache: `curl -X POST http://localhost:8000/api/capabilities/refresh`
4. Check logs for connection errors

### Tool Invocation Fails

Check the error message:
- `spec_frozen` error: Set `spec_frozen: true` for execution mode
- `Policy violation` error: Tool may require admin token or violate policy
- `MCP server not alive`: Server crashed or disconnected

## Next Steps

- Read [MCP Architecture](./ARCHITECTURE.md) for implementation details
- See [Security Guide](./SECURITY.md) for security best practices
- Check [Extension Development](../extensions/DEVELOPMENT.md) for creating custom extensions
- Explore [API Reference](../../API_REFERENCE.md) for complete API documentation

## Example: Adding a New MCP Server

1. Find or create an MCP server (see https://modelcontextprotocol.io)
2. Add configuration to `~/.agentos/mcp_servers.yaml`
3. Restart AgentOS
4. Verify tools appear: `curl http://localhost:8000/api/capabilities/tools`
5. Test invocation through API or WebUI

Example configuration for filesystem server:

```yaml
mcp_servers:
  - id: filesystem
    enabled: true
    transport: stdio
    command: ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"]
    allow_tools:
      - "read_file"
      - "list_directory"
    deny_side_effect_tags:
      - "fs_write"
      - "fs_delete"
    timeout_ms: 10000
```
