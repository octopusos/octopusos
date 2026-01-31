# CommunicationOS User Manual

**Version**: 1.0.0
**Audience**: System administrators, operators, end users
**Last Updated**: 2026-01-30

---

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Configuration](#configuration)
4. [Using Communication Features](#using-communication-features)
5. [Monitoring and Auditing](#monitoring-and-auditing)
6. [Troubleshooting](#troubleshooting)
7. [FAQ](#faq)

---

## Introduction

### What is CommunicationOS?

CommunicationOS is AgentOS's **secure gateway for external communications**. It allows AI agents to safely interact with the outside world while maintaining:

- **Security**: All requests pass through policy enforcement
- **Auditability**: Complete record of all external communications
- **Control**: Fine-grained configuration of what's allowed
- **Visibility**: Real-time monitoring and statistics

### What Can You Do with CommunicationOS?

✅ **Web Operations**:
- Search the web for information
- Fetch content from websites
- Download files and documents

✅ **Communication**:
- Send emails (SMTP)
- Post messages to Slack
- Subscribe to RSS feeds

✅ **Monitoring**:
- View audit logs of all communications
- Check policy configurations
- Monitor service health and statistics

---

## Getting Started

### Prerequisites

- AgentOS v0.6.0 or later
- Python 3.11+
- Network access to external services

### Quick Start

1. **Start AgentOS with WebUI**:
```bash
cd /path/to/agentos
uv run agentos --web
```

2. **Access Communication Dashboard**:
```
Open browser: http://localhost:8080
Navigate to: Communication → Dashboard
```

3. **Verify Service Status**:
```bash
# Via API
curl http://localhost:8080/api/communication/status

# Expected response:
{
  "ok": true,
  "data": {
    "status": "operational",
    "connectors": {
      "web_search": {"enabled": true, ...},
      "web_fetch": {"enabled": true, ...}
    }
  }
}
```

---

## Configuration

### Policy Configuration

Policies control what operations are allowed and under what conditions.

#### Viewing Current Policies

**Via WebUI**:
1. Navigate to Communication → Policies
2. Select connector type (e.g., web_search)
3. View policy details

**Via API**:
```bash
# Get all policies
curl http://localhost:8080/api/communication/policy

# Get specific policy
curl http://localhost:8080/api/communication/policy/web_search
```

#### Policy Parameters

Each connector has a policy with these settings:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `enabled` | Master switch for connector | `true` / `false` |
| `allowed_operations` | List of allowed operations | `["search", "fetch"]` |
| `blocked_domains` | Domains to block | `["localhost", "127.0.0.1"]` |
| `allowed_domains` | Domains to allow (if set, only these) | `["example.com"]` |
| `require_approval` | Manual approval required? | `true` / `false` |
| `rate_limit_per_minute` | Max requests per minute | `30` |
| `max_response_size_mb` | Max response size | `5` |
| `timeout_seconds` | Request timeout | `30` |
| `sanitize_inputs` | Enable input sanitization | `true` |
| `sanitize_outputs` | Enable output sanitization | `true` |

#### Default Policies

**Web Search** (DuckDuckGo):
```yaml
enabled: true
allowed_operations: [search]
rate_limit_per_minute: 30
max_response_size_mb: 5
timeout_seconds: 30
blocked_domains: [localhost, 127.0.0.1, 0.0.0.0]
require_approval: false
```

**Web Fetch** (HTTP content):
```yaml
enabled: true
allowed_operations: [fetch, download]
rate_limit_per_minute: 20
max_response_size_mb: 10
timeout_seconds: 60
blocked_domains: [localhost, 127.0.0.1, 0.0.0.0]
require_approval: false
```

**Email SMTP**:
```yaml
enabled: true
allowed_operations: [send]
rate_limit_per_minute: 5
timeout_seconds: 30
require_approval: true  # ⚠️ High risk - requires approval
```

**Slack**:
```yaml
enabled: true
allowed_operations: [send_message, upload_file]
rate_limit_per_minute: 10
timeout_seconds: 30
require_approval: false
```

### Customizing Policies

#### Example 1: Allow Only Specific Domains

To restrict web fetch to only trusted domains:

```python
# In your configuration file or environment
from agentos.core.communication import PolicyEngine, CommunicationPolicy, ConnectorType

policy_engine = PolicyEngine()

# Custom policy for web_fetch
custom_policy = CommunicationPolicy(
    name="restricted_web_fetch",
    connector_type=ConnectorType.WEB_FETCH,
    allowed_operations=["fetch"],
    allowed_domains=[
        "api.github.com",
        "docs.python.org",
        "stackoverflow.com",
    ],
    blocked_domains=[],  # Explicit allowlist, so no blocklist needed
    rate_limit_per_minute=20,
    timeout_seconds=60,
)

policy_engine.register_policy(custom_policy)
```

#### Example 2: Increase Rate Limits for Production

```python
# Higher limits for production environment
production_policy = CommunicationPolicy(
    name="production_web_search",
    connector_type=ConnectorType.WEB_SEARCH,
    allowed_operations=["search"],
    rate_limit_per_minute=100,  # Increased from default 30
    max_response_size_mb=10,    # Increased from default 5
    timeout_seconds=30,
)
```

#### Example 3: Require Approval for Sensitive Operations

```python
# Email requires manual approval
email_policy = CommunicationPolicy(
    name="approved_email",
    connector_type=ConnectorType.EMAIL_SMTP,
    allowed_operations=["send"],
    require_approval=True,  # ⚠️ Human must approve each email
    rate_limit_per_minute=5,
)
```

### Environment Variables

Configure connectors via environment variables:

```bash
# Email SMTP
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=your-email@gmail.com
export SMTP_PASSWORD=your-app-password
export SMTP_FROM=agentos@example.com

# Slack
export SLACK_API_TOKEN=xoxb-your-token-here
export SLACK_DEFAULT_CHANNEL=#general

# Custom connectors
export MY_CUSTOM_API_KEY=your-api-key
export MY_CUSTOM_BASE_URL=https://api.customservice.com
```

---

## Using Communication Features

### Web Search

Search the web for information using DuckDuckGo.

**Via WebUI**:
1. Navigate to Communication → Web Search
2. Enter search query
3. Set max results (default: 10)
4. Click "Search"

**Via API**:
```bash
curl -X POST http://localhost:8080/api/communication/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Python asyncio tutorial",
    "max_results": 10
  }'
```

**Response**:
```json
{
  "ok": true,
  "data": {
    "request_id": "comm-abc123",
    "status": "success",
    "data": {
      "results": [
        {
          "title": "Asyncio — Asynchronous I/O",
          "url": "https://docs.python.org/3/library/asyncio.html",
          "snippet": "asyncio is a library to write concurrent code..."
        }
      ],
      "total_results": 10
    },
    "evidence_id": "ev-xyz789"
  }
}
```

### Web Fetch

Fetch content from a URL.

**Via WebUI**:
1. Navigate to Communication → Web Fetch
2. Enter URL
3. Set timeout (optional)
4. Click "Fetch"

**Via API**:
```bash
curl -X POST http://localhost:8080/api/communication/fetch \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://api.github.com/repos/python/cpython",
    "timeout": 30
  }'
```

**Response**:
```json
{
  "ok": true,
  "data": {
    "request_id": "comm-def456",
    "status": "success",
    "data": {
      "content": "{\"id\": 123, \"name\": \"cpython\", ...}",
      "content_type": "application/json",
      "status_code": 200,
      "size_bytes": 1024
    },
    "evidence_id": "ev-abc123"
  }
}
```

### Email (SMTP)

Send emails via SMTP.

**Configuration Required**:
```bash
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=your-email@gmail.com
export SMTP_PASSWORD=your-app-password
```

**Via API**:
```bash
curl -X POST http://localhost:8080/api/communication/email/send \
  -H "Content-Type: application/json" \
  -d '{
    "to": "recipient@example.com",
    "subject": "Task Completed",
    "body": "The task has been completed successfully.",
    "context": {"task_id": "task-123"}
  }'
```

**Note**: If `require_approval: true` in policy, request will be queued for manual approval.

### Slack Integration

Post messages or upload files to Slack.

**Configuration Required**:
```bash
export SLACK_API_TOKEN=xoxb-your-slack-bot-token
```

**Send Message**:
```bash
curl -X POST http://localhost:8080/api/communication/slack/send \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "#general",
    "text": "Deployment completed successfully!",
    "context": {"task_id": "task-456"}
  }'
```

**Upload File**:
```bash
curl -X POST http://localhost:8080/api/communication/slack/upload \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "#reports",
    "file_path": "/path/to/report.pdf",
    "title": "Monthly Report",
    "comment": "Here is the monthly report."
  }'
```

---

## Monitoring and Auditing

### Viewing Audit Logs

Every communication operation generates an audit record.

**Via WebUI**:
1. Navigate to Communication → Audit Logs
2. Apply filters:
   - Connector type
   - Operation
   - Status (success/failed/denied)
   - Date range
3. Click "Search"

**Via API**:
```bash
# List all audit records
curl "http://localhost:8080/api/communication/audits?limit=100"

# Filter by connector type
curl "http://localhost:8080/api/communication/audits?connector_type=web_search"

# Filter by status
curl "http://localhost:8080/api/communication/audits?status=denied"

# Filter by date range
curl "http://localhost:8080/api/communication/audits?start_date=2026-01-01T00:00:00Z&end_date=2026-01-30T23:59:59Z"
```

**Response**:
```json
{
  "ok": true,
  "data": {
    "audits": [
      {
        "id": "ev-abc123",
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
      "limit": 100
    }
  }
}
```

### Viewing Audit Details

Get detailed information about a specific operation:

```bash
curl "http://localhost:8080/api/communication/audits/ev-abc123"
```

**Response**:
```json
{
  "ok": true,
  "data": {
    "id": "ev-abc123",
    "request_id": "comm-xyz789",
    "connector_type": "web_search",
    "operation": "search",
    "request_summary": {
      "query": "Python asyncio",
      "max_results": 10
    },
    "response_summary": {
      "total_results": 10,
      "execution_time_ms": 245
    },
    "status": "success",
    "metadata": {
      "risk_level": "low",
      "task_id": "task-123",
      "session_id": "session-456"
    },
    "created_at": "2026-01-30T10:30:00Z"
  }
}
```

### Service Statistics

Get overall statistics and health metrics:

```bash
curl "http://localhost:8080/api/communication/status"
```

**Response**:
```json
{
  "ok": true,
  "data": {
    "status": "operational",
    "connectors": {
      "web_search": {
        "enabled": true,
        "operations": ["search"],
        "rate_limit": 30
      },
      "web_fetch": {
        "enabled": true,
        "operations": ["fetch", "download"],
        "rate_limit": 20
      }
    },
    "statistics": {
      "total_requests": 1234,
      "success_rate": 95.6,
      "by_connector": {
        "web_search": {
          "total": 500,
          "success": 490,
          "failed": 8,
          "denied": 2
        },
        "web_fetch": {
          "total": 734,
          "success": 700,
          "failed": 30,
          "denied": 4
        }
      }
    },
    "timestamp": "2026-01-30T12:00:00Z"
  }
}
```

---

## Troubleshooting

### Problem: Request Denied - SSRF Protection

**Error**:
```json
{
  "ok": false,
  "error": "SSRF protection: Localhost access blocked",
  "reason_code": "AUTH_FORBIDDEN"
}
```

**Cause**: Attempting to access internal/private network resources.

**Solution**:
- Only use public URLs
- Blocked patterns: `localhost`, `127.*`, `10.*`, `172.16-31.*`, `192.168.*`
- If legitimate internal API, add to `allowed_domains` (not recommended)

### Problem: Rate Limit Exceeded

**Error**:
```json
{
  "ok": false,
  "error": "Rate limit exceeded",
  "reason_code": "RATE_LIMITED"
}
```

**Cause**: Too many requests in a short time.

**Solution**:
- Wait for rate limit window to reset (check `Retry-After` header)
- Increase rate limit in policy configuration (if justified)
- Implement exponential backoff in client code

### Problem: Operation Not Allowed

**Error**:
```json
{
  "ok": false,
  "error": "Operation 'delete' not allowed for web_fetch",
  "reason_code": "AUTH_FORBIDDEN"
}
```

**Cause**: Operation not in `allowed_operations` list.

**Solution**:
- Check policy configuration for allowed operations
- Use a supported operation
- Add operation to policy if appropriate

### Problem: Domain Blocked

**Error**:
```json
{
  "ok": false,
  "error": "Domain example.com is blocked",
  "reason_code": "AUTH_FORBIDDEN"
}
```

**Cause**: Domain is in `blocked_domains` list.

**Solution**:
- Use a different, non-blocked domain
- Remove domain from `blocked_domains` (if safe)
- Add domain to `allowed_domains` (if using allowlist)

### Problem: Timeout Error

**Error**:
```json
{
  "ok": false,
  "error": "Request timeout after 30 seconds",
  "reason_code": "INTERNAL_ERROR"
}
```

**Cause**: External service took too long to respond.

**Solution**:
- Increase `timeout_seconds` in policy
- Check if external service is slow/down
- Retry the request

### Problem: Connector Disabled

**Error**:
```json
{
  "ok": false,
  "error": "Connector web_fetch is disabled",
  "reason_code": "AUTH_FORBIDDEN"
}
```

**Cause**: Connector's `enabled` flag is set to `false`.

**Solution**:
- Enable the connector in policy configuration
- Check if connector was intentionally disabled for security

### Problem: Config Validation Failed

**Error**:
```
Connector validation failed: Missing required config 'api_key'
```

**Cause**: Connector requires configuration that wasn't provided.

**Solution**:
- Set required environment variables (e.g., `SMTP_HOST`, `SLACK_API_TOKEN`)
- Provide config when registering connector
- Check connector documentation for required config

---

## FAQ

### Q: How do I enable/disable a connector?

**A**: Update the policy configuration:
```python
from agentos.core.communication import PolicyEngine

policy_engine = PolicyEngine()
policy = policy_engine.get_policy(ConnectorType.WEB_FETCH)
policy.enabled = False  # Disable
policy_engine.register_policy(policy)
```

### Q: Can I see what data was sent/received?

**A**: Yes, check the audit logs:
```bash
curl "http://localhost:8080/api/communication/audits/ev-abc123"
```
Note: Sensitive data is redacted in logs for security.

### Q: How do I add a custom domain to the allowlist?

**A**: Update the policy:
```python
policy = policy_engine.get_policy(ConnectorType.WEB_FETCH)
policy.allowed_domains.append("my-internal-api.com")
policy_engine.register_policy(policy)
```

### Q: What happens if I exceed the rate limit?

**A**: Your request is rejected with status `429 Too Many Requests`. Wait for the rate limit window to reset (check `Retry-After` header).

### Q: Can I use CommunicationOS for internal APIs?

**A**: Yes, but you must explicitly add them to `allowed_domains` and understand the SSRF risks. It's recommended to use external APIs only.

### Q: How do I configure credentials for connectors?

**A**: Use environment variables:
```bash
export SMTP_USER=your-email@example.com
export SMTP_PASSWORD=your-password
export SLACK_API_TOKEN=xoxb-your-token
```

### Q: Are my API keys safe in logs?

**A**: Yes, sensitive data (API keys, passwords, tokens) is automatically redacted in audit logs and outputs.

### Q: Can I create custom connectors?

**A**: Yes! See the [Developer Guide](../extensions/CommunicationOS-Developer-Guide.md) for instructions.

### Q: How do I monitor CommunicationOS health?

**A**: Check the status endpoint:
```bash
curl "http://localhost:8080/api/communication/status"
```

### Q: What's the difference between `blocked_domains` and `allowed_domains`?

**A**:
- `blocked_domains`: Explicitly deny these domains (blacklist)
- `allowed_domains`: If set, ONLY allow these domains (whitelist)
- If both are empty, all public domains are allowed (except SSRF patterns)

### Q: Can I export audit logs?

**A**: Yes, query the audit API and save results:
```bash
curl "http://localhost:8080/api/communication/audits?limit=1000" > audit_export.json
```

---

## Best Practices

### Security

1. **Use allowlists, not blocklists** when possible
2. **Require approval** for high-risk operations (email, file uploads)
3. **Regularly review** audit logs for suspicious activity
4. **Keep rate limits** reasonable to prevent abuse
5. **Enable sanitization** for all connectors

### Performance

1. **Set appropriate timeouts** (30-60s for most operations)
2. **Use caching** for frequently accessed data
3. **Implement retry logic** with exponential backoff
4. **Monitor statistics** to identify bottlenecks

### Operations

1. **Review policies** quarterly
2. **Audit logs** regularly (weekly recommended)
3. **Update credentials** periodically
4. **Test connectors** after configuration changes
5. **Document custom policies** for team awareness

---

## Next Steps

- **Architecture**: Learn how CommunicationOS works - [Architecture Guide](../communication/CommunicationOS-Architecture.md)
- **Development**: Create custom connectors - [Developer Guide](../extensions/CommunicationOS-Developer-Guide.md)
- **Security**: Harden your setup - [Security Guide](../security/CommunicationOS-Security-Guide.md)
- **API Reference**: Detailed API docs - [Communication API](../communication_api.md)

---

## Support

- **Documentation**: `/docs/communication/`
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Community**: Discord (link in repo)
