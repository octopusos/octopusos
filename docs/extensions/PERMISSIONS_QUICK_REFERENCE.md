# Extension Permissions Quick Reference

**PR-E3: Permissions + Deny/Audit System**

## Quick Start

### 1. Declare Permissions in Manifest

Every capability in your extension manifest must declare required permissions:

```json
{
  "id": "tools.myextension",
  "name": "My Extension",
  "version": "0.1.0",
  "capabilities": [
    {
      "command": "/mycommand",
      "runner": "exec.mytool",
      "permissions": ["exec_shell", "network_http"]
    }
  ]
}
```

### 2. Available Permissions

| Permission | Description | Risk Level |
|------------|-------------|------------|
| `read_status` | Read system/project status | Low |
| `fs_read` | Read files from filesystem | Low |
| `network_http` | Make HTTP/HTTPS requests | Medium |
| `fs_write` | Write files to filesystem | High |
| `exec_shell` | Execute shell commands | High |

### 3. Deployment Modes

| Mode | Description | Restrictions |
|------|-------------|--------------|
| `LOCAL_OPEN` | Development mode | Allows all declared permissions |
| `LOCAL_LOCKED` | Locked-down local | Denies `exec_shell`, `fs_write` |
| `REMOTE_EXPOSED` | Multi-user production | Denies `exec_shell`, `fs_write` |

Set mode via environment:
```bash
export AGENTOS_DEPLOYMENT_MODE=local_open
```

## Common Patterns

### Read-Only Extension
```json
{
  "permissions": ["read_status", "fs_read"]
}
```
✅ Works in all modes

### Network Extension
```json
{
  "permissions": ["network_http", "fs_read"]
}
```
✅ Works in all modes

### Tool Executor Extension
```json
{
  "permissions": ["exec_shell", "fs_read", "fs_write"]
}
```
⚠️ Only works in LOCAL_OPEN mode
❌ Denied in LOCAL_LOCKED and REMOTE_EXPOSED

## Validation Rules

### Installation Time
- ❌ Missing `permissions` field → Installation fails
- ❌ Empty `permissions` array → Installation fails
- ❌ Invalid permission value → Installation fails
- ✅ All valid permissions declared → Installation succeeds

### Execution Time
- ❌ Permission not declared → Execution denied
- ❌ Permission denied by mode → Execution denied
- ✅ Permission declared and allowed → Execution proceeds

## Audit Trail

Every execution attempt is logged:

### Successful Execution
```
1. EXT_CMD_ROUTED    - Command received
2. EXT_RUN_STARTED   - Execution begins
3. EXT_RUN_FINISHED  - Execution completes
```

### Denied Execution
```
1. EXT_CMD_ROUTED    - Command received
2. EXT_RUN_DENIED    - Execution denied (with reason)
```

Query audit logs:
```python
from agentos.core.capabilities.audit_logger import get_audit_logger

logger = get_audit_logger()
denied = logger.get_denied_events(ext_id="tools.myext", limit=10)
```

## Error Messages

### "Permission not declared"
**Cause**: Extension didn't declare required permission in manifest
**Fix**: Add permission to `permissions` array in manifest

### "Permission denied in REMOTE_EXPOSED mode"
**Cause**: High-risk permission (exec_shell, fs_write) blocked in remote mode
**Fix**: Design extension to work without dangerous permissions, or use LOCAL_OPEN mode

### "Missing required field: permissions"
**Cause**: Capability doesn't have `permissions` field
**Fix**: Add `permissions` array to capability definition

## Migration Guide

### Updating Existing Extensions

Before (will fail validation):
```json
{
  "command": "/mycommand",
  "runner": "exec.mytool"
}
```

After (valid):
```json
{
  "command": "/mycommand",
  "runner": "exec.mytool",
  "permissions": ["exec_shell"]
}
```

### Minimal Permissions Principle

Always declare the minimum required permissions:

❌ Too permissive:
```json
{
  "permissions": ["exec_shell", "fs_write", "network_http", "fs_read"]
}
```

✅ Just what's needed:
```json
{
  "permissions": ["network_http"]
}
```

## Best Practices

1. **Declare Minimum Permissions**
   - Only request permissions you actually need
   - Reduces security risk and improves compatibility

2. **Test in Multiple Modes**
   - Test in LOCAL_OPEN during development
   - Test in REMOTE_EXPOSED before release
   - Document mode requirements

3. **Handle Denials Gracefully**
   - Check audit logs for denial reasons
   - Provide helpful error messages to users
   - Document required deployment mode

4. **Document Security Impact**
   - Explain why each permission is needed
   - Document security implications in README
   - Provide safer alternatives if available

## Examples

### Example 1: HTTP Client Extension

```json
{
  "id": "tools.httpclient",
  "name": "HTTP Client",
  "version": "1.0.0",
  "capabilities": [
    {
      "command": "/http",
      "runner": "exec.curl",
      "permissions": ["network_http", "fs_read"],
      "description": "Make HTTP requests"
    }
  ]
}
```

**Works in**: All modes ✅

### Example 2: File Processor Extension

```json
{
  "id": "tools.fileprocessor",
  "name": "File Processor",
  "version": "1.0.0",
  "capabilities": [
    {
      "command": "/process",
      "runner": "exec.processor",
      "permissions": ["fs_read", "fs_write"],
      "description": "Process files"
    }
  ]
}
```

**Works in**: LOCAL_OPEN only ⚠️

### Example 3: System Monitor Extension

```json
{
  "id": "tools.monitor",
  "name": "System Monitor",
  "version": "1.0.0",
  "capabilities": [
    {
      "command": "/monitor",
      "runner": "exec.monitor",
      "permissions": ["read_status"],
      "description": "Monitor system status"
    }
  ]
}
```

**Works in**: All modes ✅

## Troubleshooting

### Installation Fails with "Missing required field: permissions"

**Solution**: Add permissions field to all capabilities:
```json
{
  "capabilities": [
    {
      "command": "/mycommand",
      "runner": "exec.mytool",
      "permissions": ["exec_shell"]  // Add this
    }
  ]
}
```

### Execution Denied with "Permission not declared in extension manifest"

**Solution**: Add missing permission to manifest and reinstall:
```json
{
  "permissions": ["exec_shell", "network_http"]  // Add missing permission
}
```

### Execution Denied in Production but Works Locally

**Cause**: Production uses REMOTE_EXPOSED mode
**Solution**: Redesign extension to avoid exec_shell and fs_write, or document LOCAL_OPEN requirement

## References

- Full Implementation: `/agentos/core/capabilities/permissions.py`
- Schema Validator: `/agentos/core/capabilities/schema.py`
- Audit System: `/agentos/core/capabilities/audit_logger.py`
- Test Examples: `/tests/integration/extensions/test_permissions_audit_e2e.py`
- Implementation Report: `/PR_E3_IMPLEMENTATION_REPORT.md`

---

**Version**: PR-E3
**Last Updated**: 2026-01-30
