# CommunicationOS Architecture

**Version**: 1.0.0
**Date**: 2026-01-30
**Status**: Active

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Module Design](#module-design)
4. [Data Flow](#data-flow)
5. [Component Interactions](#component-interactions)
6. [Integration with AgentOS](#integration-with-agentos)
7. [Security Architecture](#security-architecture)
8. [Performance Considerations](#performance-considerations)

---

## Overview

CommunicationOS is the **external communication gateway** for AgentOS. It provides a secure, auditable, and policy-enforced interface for agents to interact with external systems such as:

- Web APIs and search engines
- Email and messaging platforms (Slack, etc.)
- RSS feeds and content aggregators
- File storage and cloud services

**Core Design Principles**:
- **Security by default**: Deny-first, explicit allow policies
- **Comprehensive auditing**: Every operation generates evidence
- **Extensible architecture**: Easy to add new connectors
- **Centralized control**: Single policy enforcement point
- **Defense in depth**: Multiple security layers

---

## Architecture Diagram

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         AgentOS Core                             │
│                                                                   │
│  ┌─────────────┐     ┌──────────────┐      ┌─────────────┐     │
│  │ TaskRunner  │────▶│ ExecutorEngine│─────▶│ Capability  │     │
│  │             │     │               │      │   System    │     │
│  └─────────────┘     └──────────────┘      └──────┬──────┘     │
│                                                     │            │
└─────────────────────────────────────────────────────┼────────────┘
                                                      │
                              ┌───────────────────────▼───────────────────────┐
                              │      CommunicationOS Boundary                 │
                              │  ┌─────────────────────────────────────────┐ │
                              │  │    CommunicationService (Main Gateway)  │ │
                              │  └───────────────┬─────────────────────────┘ │
                              │                  │                            │
                              │  ┌───────────────▼─────────────────────────┐ │
                              │  │  1. PolicyEngine (Security Evaluation)  │ │
                              │  │     - Allowed/Denied/Approval           │ │
                              │  │     - SSRF Protection                   │ │
                              │  │     - Domain Filtering                  │ │
                              │  │     - Risk Assessment                   │ │
                              │  └───────────────┬─────────────────────────┘ │
                              │                  │                            │
                              │  ┌───────────────▼─────────────────────────┐ │
                              │  │  2. RateLimiter (Throttling)            │ │
                              │  │     - Per-connector limits              │ │
                              │  │     - Global limits                     │ │
                              │  │     - Sliding window algorithm          │ │
                              │  └───────────────┬─────────────────────────┘ │
                              │                  │                            │
                              │  ┌───────────────▼─────────────────────────┐ │
                              │  │  3. InputSanitizer (Input Validation)   │ │
                              │  │     - SQL injection prevention          │ │
                              │  │     - Command injection prevention      │ │
                              │  │     - XSS prevention                    │ │
                              │  └───────────────┬─────────────────────────┘ │
                              │                  │                            │
                              │  ┌───────────────▼─────────────────────────┐ │
                              │  │  4. Connector Dispatch                  │ │
                              │  │     ┌─────────────────────────────────┐ │ │
                              │  │     │  BaseConnector Interface        │ │ │
                              │  │     └────┬────────────────────────────┘ │ │
                              │  │          │                              │ │
                              │  │  ┌───────┴────────┬──────────┬────────┐│ │
                              │  │  │                │          │        ││ │
                              │  │  ▼                ▼          ▼        ││ │
                              │  │ Web            Web        RSS        ││ │
                              │  │ Search         Fetch      Feed       ││ │
                              │  │                                       ││ │
                              │  │  ▼                ▼          ▼        ││ │
                              │  │ Email          Slack      Custom      ││ │
                              │  │ SMTP           API        Connector   ││ │
                              │  └────────────────┬──────────────────────┘│ │
                              │                   │                        │ │
                              │  ┌────────────────▼──────────────────────┐│ │
                              │  │  5. OutputSanitizer (Data Protection) ││ │
                              │  │     - Sensitive data redaction        ││ │
                              │  │     - Response size limiting          ││ │
                              │  └────────────────┬──────────────────────┘│ │
                              │                   │                        │ │
                              │  ┌────────────────▼──────────────────────┐│ │
                              │  │  6. EvidenceLogger (Audit Trail)      ││ │
                              │  │     - Request/response logging        ││ │
                              │  │     - Searchable evidence DB          ││ │
                              │  │     - Statistics and reports          ││ │
                              │  └───────────────────────────────────────┘│ │
                              └───────────────────────────────────────────┘ │
                                                    │
                                    ┌───────────────┴───────────────┐
                                    │                               │
                              ┌─────▼─────┐                 ┌──────▼──────┐
                              │ External  │                 │   Audit     │
                              │  APIs     │                 │  Database   │
                              │           │                 │  (SQLite)   │
                              └───────────┘                 └─────────────┘
```

### Request Flow Sequence

```
Agent Request
    │
    ▼
CommunicationService.execute()
    │
    ├─▶ [1] PolicyEngine.validate_params()
    │        └─▶ Check required parameters
    │
    ├─▶ [2] PolicyEngine.assess_risk()
    │        └─▶ Calculate risk level (LOW/MEDIUM/HIGH/CRITICAL)
    │
    ├─▶ [3] PolicyEngine.evaluate_request()
    │        ├─▶ Check if connector enabled
    │        ├─▶ Check if operation allowed
    │        ├─▶ Check domain policy (blocked/allowed lists)
    │        └─▶ Run SSRF checks
    │
    ├─▶ [4] RateLimiter.check_limit()
    │        └─▶ Verify rate limit not exceeded
    │
    ├─▶ [5] InputSanitizer.sanitize()
    │        ├─▶ Detect SQL injection patterns
    │        ├─▶ Detect command injection patterns
    │        ├─▶ Detect XSS patterns
    │        └─▶ Apply HTML escaping
    │
    ├─▶ [6] Connector.execute()
    │        └─▶ Make actual external API call
    │
    ├─▶ [7] OutputSanitizer.sanitize()
    │        ├─▶ Redact sensitive data (keys, passwords)
    │        ├─▶ Truncate large responses
    │        └─▶ Filter fields
    │
    ├─▶ [8] EvidenceLogger.log_operation()
    │        ├─▶ Create evidence record
    │        ├─▶ Store request/response summary
    │        ├─▶ Record metadata (risk, status, timestamps)
    │        └─▶ Persist to database
    │
    └─▶ Return CommunicationResponse
         ├─▶ status: success/failed/denied/rate_limited
         ├─▶ data: sanitized response
         ├─▶ evidence_id: audit trail reference
         └─▶ error: failure reason (if any)
```

---

## Module Design

### 1. CommunicationService (service.py)

**Purpose**: Main orchestrator that coordinates all communication operations.

**Key Methods**:
```python
class CommunicationService:
    def __init__(self, policy_engine, evidence_logger, rate_limiter,
                 input_sanitizer, output_sanitizer)

    async def execute(connector_type, operation, params, context) -> Response

    def register_connector(connector_type, connector) -> None

    def get_connector(connector_type) -> BaseConnector

    async def list_connectors() -> Dict[str, Any]

    async def get_statistics() -> Dict[str, Any]
```

**Responsibilities**:
- Request orchestration
- Component coordination
- Error handling and recovery
- Connector registry management

### 2. PolicyEngine (policy.py)

**Purpose**: Evaluate security policies and enforce access control.

**Key Methods**:
```python
class PolicyEngine:
    def evaluate_request(request) -> tuple[bool, str]

    def validate_params(request) -> tuple[bool, str]

    def assess_risk(request) -> RiskLevel

    def _check_domain_policy(url, policy) -> tuple[bool, str]

    def _check_ssrf(url) -> tuple[bool, str]

    def register_policy(policy) -> None

    def get_policy(connector_type) -> CommunicationPolicy
```

**Responsibilities**:
- Policy evaluation (allow/deny/approve)
- SSRF protection
- Domain filtering (blocked/allowed lists)
- Risk assessment (low/medium/high/critical)
- Operation validation

**Default Policies**:
```python
# Web Search: 30 req/min, 5MB max, 30s timeout
# Web Fetch: 20 req/min, 10MB max, 60s timeout
# RSS: 10 req/min, 5MB max, 30s timeout
# Email: 5 req/min, requires approval
# Slack: 10 req/min, 30s timeout
```

### 3. Sanitizers (sanitizers.py)

**Purpose**: Protect against injection attacks and data leakage.

#### InputSanitizer

**Key Methods**:
```python
class InputSanitizer:
    def sanitize(data) -> Any

    def _sanitize_string(value) -> str

    def validate_email(email) -> bool

    def validate_url(url) -> bool
```

**Protection Patterns**:
- SQL injection: `SELECT`, `INSERT`, `OR`, `--`, etc.
- Command injection: `;&|`, `$()`, backticks, `${}`
- XSS: `<script>`, `javascript:`, `on*=` event handlers

#### OutputSanitizer

**Key Methods**:
```python
class OutputSanitizer:
    def sanitize(data, redact_sensitive=True) -> Any

    def _redact_sensitive(value) -> str

    def truncate_large_output(data, max_size) -> str

    def filter_fields(data, allowed_fields) -> Dict
```

**Redaction Patterns**:
- API keys: `api_key=abcd***************`
- Passwords: `password=pass****`
- Tokens: `token=eyJh***************`
- Credit cards: `4532-****-****-9876`
- SSN: `123-**-****`

### 4. RateLimiter (rate_limit.py)

**Purpose**: Prevent abuse through request throttling.

**Key Methods**:
```python
class RateLimiter:
    def check_limit(identifier, limit) -> tuple[bool, str]

    def get_usage(identifier) -> Dict[str, Any]

    def reset_limit(identifier) -> None

    def _cleanup_old_requests() -> None
```

**Algorithm**: Sliding window
- Tracks timestamps of recent requests
- Automatically cleans up old entries
- Per-connector and global limits

**Example**:
```python
# Web search: 30 requests/minute
# Window: last 60 seconds
# Request at t=0, t=1, t=2, ... t=59 → all allowed
# Request at t=60 → allowed (t=0 expired)
```

### 5. EvidenceLogger (evidence.py)

**Purpose**: Maintain comprehensive audit trail of all communications.

**Key Methods**:
```python
class EvidenceLogger:
    async def log_operation(request, response) -> str

    async def get_evidence(evidence_id) -> EvidenceRecord

    async def search_evidence(connector_type, operation, status,
                             start_date, end_date, limit) -> List[EvidenceRecord]

    async def get_total_requests() -> int

    async def get_success_rate() -> float

    async def get_stats_by_connector() -> Dict[str, Any]
```

**Evidence Record Structure**:
```python
@dataclass
class EvidenceRecord:
    id: str                        # Unique evidence ID
    request_id: str                # Original request ID
    connector_type: ConnectorType  # Connector used
    operation: str                 # Operation performed
    request_summary: Dict          # Sanitized request details
    response_summary: Dict         # Sanitized response details
    status: RequestStatus          # Result status
    metadata: Dict                 # Additional context
    created_at: datetime           # Timestamp
```

### 6. Connectors (connectors/*.py)

**Purpose**: Implement actual integrations with external services.

#### BaseConnector Interface

```python
class BaseConnector(ABC):
    @abstractmethod
    async def execute(operation: str, params: Dict) -> Any

    @abstractmethod
    def get_supported_operations() -> List[str]

    def validate_config() -> bool

    def get_status() -> Dict[str, Any]

    async def health_check() -> bool
```

#### Implemented Connectors

**WebSearchConnector** (web_search.py):
- Operations: `search`
- Providers: DuckDuckGo (default), configurable
- Features: Query sanitization, result filtering, safe search

**WebFetchConnector** (web_fetch.py):
- Operations: `fetch`, `download`
- Features: Content type detection, encoding handling, size limits
- Supported formats: HTML, JSON, XML, text, binary

**RSSConnector** (rss.py):
- Operations: `fetch_feed`
- Formats: RSS 2.0, Atom
- Features: Entry parsing, metadata extraction

**EmailSMTPConnector** (email_smtp.py):
- Operations: `send`
- Features: TLS support, attachment handling
- Requires: SMTP credentials

**SlackConnector** (slack.py):
- Operations: `send_message`, `upload_file`
- Features: Channel/DM support, rich formatting
- Requires: Slack API token

---

## Data Flow

### 1. Successful Request Flow

```
User → TaskRunner → CommunicationService
         ↓
    Policy Check ✅
         ↓
    Rate Limit ✅
         ↓
    Sanitize Input ✅
         ↓
    Execute Connector
         ↓
    External API → Response
         ↓
    Sanitize Output ✅
         ↓
    Log Evidence ✅
         ↓
    Return to User (with evidence_id)
```

### 2. Denied Request Flow (SSRF)

```
User → TaskRunner → CommunicationService
         ↓
    Policy Check ❌ (SSRF detected)
         ↓
    Log Denial Evidence
         ↓
    Return Error: "SSRF protection: Localhost access blocked"
         ↓
    User receives 403 Forbidden
```

### 3. Rate Limited Flow

```
User → TaskRunner → CommunicationService
         ↓
    Policy Check ✅
         ↓
    Rate Limit ❌ (30/min exceeded)
         ↓
    Log Rate Limit Evidence
         ↓
    Return Error: "Rate limit exceeded"
         ↓
    User receives 429 Too Many Requests (Retry-After: 30s)
```

---

## Component Interactions

### Initialization Flow

```python
# 1. Create components
policy_engine = PolicyEngine()
evidence_logger = EvidenceLogger()
rate_limiter = RateLimiter()
input_sanitizer = InputSanitizer()
output_sanitizer = OutputSanitizer()

# 2. Create service
service = CommunicationService(
    policy_engine=policy_engine,
    evidence_logger=evidence_logger,
    rate_limiter=rate_limiter,
    input_sanitizer=input_sanitizer,
    output_sanitizer=output_sanitizer,
)

# 3. Register connectors
service.register_connector(ConnectorType.WEB_SEARCH, WebSearchConnector())
service.register_connector(ConnectorType.WEB_FETCH, WebFetchConnector())

# 4. Service is ready
```

### Execution Flow

```python
# Agent makes request
response = await service.execute(
    connector_type=ConnectorType.WEB_SEARCH,
    operation="search",
    params={"query": "Python programming"},
    context={"task_id": "task-123"},
)

# Service orchestrates:
# - Policy evaluation
# - Rate limiting
# - Input sanitization
# - Connector execution
# - Output sanitization
# - Evidence logging

# Response includes:
response.status          # "success"
response.data            # Search results
response.evidence_id     # "ev-abc123"
```

---

## Integration with AgentOS

### 1. TaskRunner Integration

```python
# TaskRunner calls CommunicationService for external operations
from agentos.core.communication import CommunicationService, ConnectorType

service = get_communication_service()

# During task execution
response = await service.execute(
    connector_type=ConnectorType.WEB_FETCH,
    operation="fetch",
    params={"url": "https://example.com/api/data"},
    context={"task_id": task.id, "session_id": session.id},
)
```

### 2. ExecutorEngine Integration

```python
# Communication is a capability in the executor sandbox
capabilities = {
    "network": "restricted",  # Only through CommunicationOS
    "communication": "allowed",
}

# Agents cannot make direct HTTP calls
# All external access must go through CommunicationService
```

### 3. WebUI Integration

```python
# REST API exposes communication operations
# /api/communication/search  - Execute search
# /api/communication/fetch   - Fetch content
# /api/communication/policy  - View policies
# /api/communication/audits  - View audit trail
```

### 4. Database Integration

```python
# Evidence records stored in SQLite
# Same database as task evidence

agentos.db
├── tasks                 # Task records
├── task_evidence         # Execution evidence
├── communication_evidence # Communication evidence
└── communication_stats   # Usage statistics
```

---

## Security Architecture

### Defense in Depth Layers

```
Layer 1: Policy Enforcement
    - Connector enabled check
    - Operation allowlist
    - Domain filtering
    - Approval requirements

Layer 2: SSRF Protection
    - Localhost blocking
    - Private IP blocking
    - Link-local blocking
    - Scheme validation

Layer 3: Injection Prevention
    - SQL injection detection
    - Command injection detection
    - XSS detection
    - HTML escaping

Layer 4: Rate Limiting
    - Per-connector limits
    - Global limits
    - Sliding window algorithm

Layer 5: Output Sanitization
    - Sensitive data redaction
    - Response size limits
    - Field filtering

Layer 6: Audit Logging
    - Every operation logged
    - Searchable evidence
    - Compliance reporting
```

### Threat Model

| Threat | Mitigation | Layer |
|--------|-----------|-------|
| **SSRF** | IP/domain filtering, scheme validation | Policy |
| **Data exfiltration** | Output sanitization, domain allowlists | Sanitizer |
| **Injection attacks** | Pattern detection, HTML escaping | Sanitizer |
| **Resource abuse** | Rate limiting, timeout enforcement | RateLimiter |
| **Unauthorized access** | Policy enforcement, approval workflow | Policy |
| **Credential leakage** | Sensitive data redaction | OutputSanitizer |

---

## Performance Considerations

### Latency Budget

```
Policy evaluation:      1-5ms
Rate limit check:       0.5-1ms
Input sanitization:     0.5-2ms
Connector execution:    100-5000ms (external API)
Output sanitization:    0.5-2ms
Evidence logging:       1-3ms
──────────────────────────────────
Total overhead:         ~4-13ms
External latency:       100-5000ms
```

**Conclusion**: Policy overhead (4-13ms) is negligible compared to external API latency (100ms-5s).

### Optimization Strategies

1. **Async I/O**: All operations use `async/await`
2. **Connection pooling**: HTTP clients reuse connections
3. **Lazy evidence logging**: Non-blocking writes
4. **In-memory rate limiting**: No DB queries for limits
5. **Compiled regex**: Patterns compiled once at init

### Scalability

- **Single instance**: 100-500 req/min (rate limit bound)
- **Multiple instances**: Shared evidence DB, independent rate limiters
- **Horizontal scaling**: Add more instances with load balancer

---

## Summary

CommunicationOS provides a **secure, auditable, and extensible** gateway for external communications in AgentOS. Key architectural decisions:

1. **Centralized control**: Single service enforces all policies
2. **Defense in depth**: Multiple independent security layers
3. **Comprehensive auditing**: Every operation generates evidence
4. **Extensible design**: Easy to add new connectors and policies
5. **Performance-conscious**: Minimal overhead on external I/O

**Next Steps**:
- See [Developer Guide](CommunicationOS-Developer-Guide.md) to extend connectors
- See [User Manual](CommunicationOS-User-Manual.md) to configure policies
- See [Security Guide](../security/CommunicationOS-Security-Guide.md) for hardening
