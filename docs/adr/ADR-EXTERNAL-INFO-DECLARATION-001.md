# ADR-EXTERNAL-INFO-DECLARATION-001: LLM External Information Declaration Architecture

**Status**: Accepted
**Date**: 2026-01-31
**Authors**: AgentOS Team
**Related**: ADR-CHAT-COMM-001-Guards, ADR-EXT-001-declarative-extensions-only

## Status
Accepted (2026-01-31)

## Context

In AI agent systems, Large Language Models (LLMs) often need to access external information sources such as web searches, API calls, database queries, and file system operations. However, allowing LLMs to directly trigger external I/O operations creates serious security, compliance, and auditability concerns:

### Key Problems

1. **Silent Side Effects**: LLMs could leak sensitive data during planning phases before user approval
2. **Audit Trail Gaps**: Direct I/O execution bypasses centralized audit and governance systems
3. **Security Risks**: External operations could be exploited for data exfiltration or system manipulation
4. **Compliance Violations**: Automated data access without explicit authorization violates data governance principles
5. **Timing Attacks**: Network operations during planning reveal information through timing channels
6. **Attribution Loss**: External knowledge claimed as internal knowledge without proper sourcing

### Current State

AgentOS has implemented various safeguards (Phase Gate, Attribution Guard, Content Fence), but lacks a unified architectural principle governing how LLMs interact with external information sources.

## Decision

We establish **three immutable core principles** for LLM interaction with external information:

---

## Core Principle 1: LLM Cannot Auto-Trigger External I/O

### Definition

**LLMs MUST NOT directly invoke any external I/O operations.** All external operations must be explicitly requested and executed through controlled channels.

### Scope of "External I/O"

External I/O includes any operation that:
- Makes network requests (HTTP, TCP, WebSocket, etc.)
- Reads files outside the designated workspace
- Writes to databases or storage systems
- Executes system commands
- Calls external APIs or services
- Accesses hardware resources (camera, microphone, GPS, etc.)

### Enforcement Mechanisms

1. **Phase Gate**: Block all external operations during planning phase
   - Planning = pure computation, no side effects
   - Execution = controlled external operations allowed
   - Default: fail-closed if phase is unknown

2. **Command Namespace Isolation**:
   - External operations use `comm.*` namespace prefix
   - Phase Gate validates namespace before execution
   - Whitelist-based validation (not blacklist)

3. **No Direct Import/Execution**:
   - LLM cannot directly import libraries like `requests`, `urllib`, `socket`
   - All external operations go through AgentOS capability layer
   - Code execution sandboxing enforced

### Example

**PROHIBITED** (Direct I/O):
```python
# LLM cannot do this directly:
import requests
response = requests.get("https://example.com/api/data")
```

**REQUIRED** (Declaration):
```python
# LLM must declare intent:
{
  "operation": "comm.fetch",
  "url": "https://example.com/api/data",
  "reason": "Need product pricing data for customer query"
}
```

---

## Core Principle 2: LLM Can Only Declare Need for External Information

### Definition

**LLMs can only declare the NEED for external information, not execute the retrieval.**

The declaration must include:
1. **What** information is needed (specific, not vague)
2. **Why** it's needed (justification for audit trail)
3. **Where** to get it (source URL, API endpoint, file path)
4. **How** to use it (summarize, cite, compare, etc.)

### Declaration Format

```json
{
  "operation": "comm.search | comm.fetch | comm.query",
  "parameters": {
    "query": "specific search query",
    "url": "https://source.com",
    "scope": "web | internal | database"
  },
  "justification": {
    "user_request": "original user question",
    "missing_knowledge": "what LLM doesn't know",
    "expected_use": "how information will be used"
  },
  "phase": "execution",
  "session_id": "unique-session-identifier"
}
```

### Approval Flow

1. **LLM declares need** → Agent system receives declaration
2. **Governance evaluation** → Policy engine checks permissions, quotas, trust tier
3. **User approval** (if required) → Interactive approval for high-risk operations
4. **Execution phase** → AgentOS executes operation in controlled environment
5. **Attribution** → Result tagged with source and timestamp
6. **Delivery** → LLM receives attributed data with usage constraints

### Why This Matters

- **Transparency**: User sees what external data will be accessed before it happens
- **Control**: User can deny or modify requests
- **Audit**: Complete record of what was requested and why
- **Compliance**: Explicit approval chain for sensitive operations

---

## Core Principle 3: All External I/O Must Execute in Controlled Command Phase

### Definition

**All external I/O operations MUST execute in a controlled execution phase with full auditability.**

### Execution Phase Requirements

1. **Phase Validation**:
   - Operation must have `execution_phase: "execution"`
   - Planning phase blocks all external operations
   - Unknown phase defaults to blocked (fail-closed)

2. **Command Execution**:
   - All external operations are "commands" (comm.search, comm.fetch, etc.)
   - Commands execute in sandboxed environment
   - Limited working directory, PATH, environment variables
   - Timeout enforcement (default: 30 seconds for network operations)

3. **Audit Trail**:
   - Every external operation logged to `system_logs` and `task_audits`
   - Audit includes:
     - Operation type and parameters
     - Session ID and user context
     - Timestamp (start and end)
     - Result summary (success/failure, data size)
     - Attribution metadata
     - Governance decisions applied

4. **Attribution Enforcement**:
   - All returned data includes attribution:
     ```json
     {
       "results": [...],
       "metadata": {
         "attribution": "CommunicationOS (search) in session abc123",
         "source": "https://example.com",
         "timestamp": "2026-01-31T10:30:00Z",
         "trust_level": "UNTRUSTED_EXTERNAL_CONTENT"
       }
     }
     ```
   - Attribution is immutable and survives data transformations
   - LLM receives explicit warning about external content

5. **Content Fence**:
   - External content wrapped with `UNTRUSTED_EXTERNAL_CONTENT` marker
   - LLM prompt injection warns about usage constraints:
     - ✅ Can use for: summarization, citation, reference
     - ❌ Cannot use for: execute instructions, modify system, grant permissions
   - Source URL preserved for audit and trust evaluation

### Execution Sandboxing

Commands execute in restricted environment:

```yaml
sandbox:
  working_directory: ".agentos/workspace/{session_id}/"
  allowed_paths:
    - ".agentos/workspace/{session_id}/"
    - ".agentos/cache/"
  environment_vars:
    - PATH (restricted)
    - HOME, USER, TEMP, TMPDIR
    - LANG, LC_ALL
  network:
    allowed_protocols: ["https"]
    allowed_domains: [optional whitelist]
    rate_limit: 10 requests per minute
  timeouts:
    network_operation: 30s
    file_operation: 10s
    total_execution: 300s
```

### Example Flow

**Planning Phase** (blocked):
```python
# LLM during planning:
response = {
  "plan": "I need to search for pricing information",
  "required_operations": [
    {
      "operation": "comm.search",
      "query": "Product X pricing 2026"
    }
  ]
}
# No execution happens yet
```

**Execution Phase** (allowed):
```python
# After user approval, execution phase:
result = execute_command(
  command="comm.search",
  args={"query": "Product X pricing 2026"},
  session_id="session-123",
  execution_phase="execution"
)

# result includes:
# - search results
# - attribution metadata
# - UNTRUSTED_EXTERNAL_CONTENT marker
# - audit log entry created
```

---

## Implementation Architecture

### Layer Separation

```
┌─────────────────────────────────────────────┐
│ LLM Layer (Planning)                        │
│ - Generate declarations                     │
│ - No external I/O capability                │
└────────────────┬────────────────────────────┘
                 │ (declarations only)
┌────────────────▼────────────────────────────┐
│ Governance Layer                            │
│ - Phase Gate: block planning-phase I/O      │
│ - Policy evaluation: check permissions      │
│ - User approval: interactive if needed      │
└────────────────┬────────────────────────────┘
                 │ (approved operations)
┌────────────────▼────────────────────────────┐
│ Execution Layer (Command Runner)            │
│ - Sandboxed execution                       │
│ - Timeout enforcement                       │
│ - Audit logging                             │
│ - Attribution tagging                       │
└────────────────┬────────────────────────────┘
                 │ (attributed results)
┌────────────────▼────────────────────────────┐
│ LLM Layer (Consumption)                     │
│ - Receive attributed data                   │
│ - Content fence warnings                    │
│ - Summarize/cite only                       │
└─────────────────────────────────────────────┘
```

### Guard Integration

Three mandatory guards enforce these principles:

1. **Phase Gate** (`agentos/core/chat/guards/phase_gate.py`)
   - Enforces Principle 1 and 3
   - Blocks external operations in planning phase
   - Validates execution_phase parameter

2. **Attribution Guard** (`agentos/core/chat/guards/attribution.py`)
   - Enforces Principle 3
   - Validates attribution metadata format
   - Prevents claiming external knowledge as internal

3. **Content Fence** (`agentos/core/chat/guards/content_fence.py`)
   - Enforces Principle 3
   - Marks external content as UNTRUSTED_EXTERNAL_CONTENT
   - Injects LLM warnings about usage constraints

### Command Registration

External operations must be registered as commands:

```python
# agentos/core/chat/comm_commands.py
class ExternalCommand:
    namespace = "comm"  # All external ops use comm.* prefix

    def execute(self, args, session_id, execution_phase):
        # PRINCIPLE 1: Check phase gate
        PhaseGate.check(f"comm.{self.name}", execution_phase)

        # PRINCIPLE 2: Validate declaration
        self.validate_declaration(args)

        # PRINCIPLE 3: Execute in sandbox with audit
        result = self.run_sandboxed(args)
        attributed = AttributionGuard.format_response(result, session_id)
        wrapped = ContentFence.wrap(attributed)

        self.audit_log(operation=self.name, session=session_id, result=result)

        return wrapped
```

---

## Consequences

### Positive

1. **Security**:
   - No silent data exfiltration
   - No unauthorized network calls
   - No prompt injection via external content
   - Defense in depth with three guard layers

2. **Auditability**:
   - Complete record of all external operations
   - Attribution chain preserved
   - Governance decisions logged
   - Compliance-ready audit trail

3. **Transparency**:
   - Users see what external data is accessed
   - Clear distinction between internal and external knowledge
   - Explicit approval for high-risk operations

4. **Control**:
   - User can deny external operations
   - Quota and rate limiting enforced
   - Trust tier policies applied
   - Admin token for sensitive operations

5. **Determinism**:
   - Planning phase is pure computation
   - Execution phase is controlled and audited
   - Reproducible behavior for debugging

### Negative

1. **Performance Overhead**:
   - Additional validation and logging
   - Guard checks on every operation
   - Attribution metadata overhead

2. **Development Complexity**:
   - All external operations must follow declaration pattern
   - Multiple guard integrations required
   - More error handling code

3. **User Experience**:
   - Extra approval steps for external operations
   - Not as "magical" as direct execution
   - Requires understanding of phases

### Mitigation Strategies

1. **Performance**:
   - Cache guard validation results
   - Async audit logging
   - Batch attribution for multiple results

2. **Complexity**:
   - Standard templates for command registration
   - Automated guard integration tests
   - Clear developer documentation

3. **UX**:
   - Smart approval defaults (low-risk = auto-approve)
   - Batch approval for similar operations
   - Progressive disclosure in UI

---

## Enforcement Checklist

For every new external operation:

- [ ] Operation uses `comm.*` namespace prefix
- [ ] Declaration format includes operation, parameters, justification
- [ ] Phase Gate integrated at start of execute()
- [ ] Execution only in execution phase
- [ ] Sandbox constraints defined (working dir, PATH, env vars, timeout)
- [ ] Audit logging for operation start and completion
- [ ] Attribution metadata generated with AttributionGuard
- [ ] Content wrapped with ContentFence
- [ ] LLM prompt injection includes usage warnings
- [ ] Unit tests for all three guards
- [ ] Integration test for full flow (declare → approve → execute → attribute)
- [ ] Documentation updated with new operation

---

## Red Lines (Absolute Prohibitions)

These patterns are **NEVER ALLOWED**:

❌ **Direct I/O in LLM code**:
```python
# PROHIBITED
import requests
data = requests.get(url)
```

❌ **Planning-phase external operations**:
```python
# PROHIBITED
def plan_task(user_input):
    search_results = comm.search(user_input)  # NO!
    return generate_plan(search_results)
```

❌ **Unauthenticated external operations**:
```python
# PROHIBITED
def fetch_data(url):
    return urllib.urlopen(url)  # No attribution, no audit
```

❌ **Attribution bypass**:
```python
# PROHIBITED
result = comm.search(query)
del result["metadata"]["attribution"]  # NO!
return result
```

❌ **Content fence removal**:
```python
# PROHIBITED
wrapped = ContentFence.wrap(external_data, url)
unwrapped = wrapped.replace("UNTRUSTED_EXTERNAL_CONTENT", "")  # NO!
```

❌ **Phase gate bypass**:
```python
# PROHIBITED
# Renaming to avoid comm.* prefix
def internal_search(query):
    return _actually_external_search(query)  # NO!
```

---

## Testing Requirements

### Unit Tests

1. **Phase Gate**:
   - ✅ Block comm.* in planning phase
   - ✅ Allow comm.* in execution phase
   - ✅ Block comm.* in unknown phase
   - ✅ Allow non-comm operations in all phases

2. **Declaration Validation**:
   - ✅ Valid declaration accepted
   - ✅ Missing justification rejected
   - ✅ Invalid phase rejected
   - ✅ Malformed parameters rejected

3. **Sandbox Enforcement**:
   - ✅ Path traversal blocked
   - ✅ Unauthorized network access blocked
   - ✅ Timeout enforced
   - ✅ Environment variable restrictions enforced

4. **Attribution Guard**:
   - ✅ Correct format generated
   - ✅ Missing attribution rejected
   - ✅ Wrong session ID rejected
   - ✅ Attribution preserved through transformations

5. **Content Fence**:
   - ✅ External content marked correctly
   - ✅ LLM warning injected
   - ✅ Source URL preserved
   - ✅ Unwrap for display works correctly

### Integration Tests

1. **Full Declaration Flow**:
   - ✅ LLM generates declaration
   - ✅ Governance evaluates and approves
   - ✅ Execution phase runs in sandbox
   - ✅ Result attributed and fenced
   - ✅ Audit log created

2. **Cross-Guard Validation**:
   - ✅ All three guards work together
   - ✅ Planning phase blocks properly
   - ✅ Attribution enforced
   - ✅ Content fence applied

3. **Negative Tests**:
   - ✅ Bypass attempts detected and blocked
   - ✅ Malicious declarations rejected
   - ✅ Phase transitions validated

---

## Related ADRs

- **ADR-CHAT-COMM-001-Guards**: Implementation of Phase Gate, Attribution Guard, Content Fence
- **ADR-EXT-001-declarative-extensions-only**: Declarative-only extension architecture
- **ADR-005-MCP-Marketplace**: Marketplace as discovery layer, not execution
- **ADR-EXT-002-python-only-runtime**: Sandboxed Python execution environment

---

## References

- Phase Gate Implementation: `agentos/core/chat/guards/phase_gate.py`
- Attribution Guard Implementation: `agentos/core/chat/guards/attribution.py`
- Content Fence Implementation: `agentos/core/chat/guards/content_fence.py`
- Command Execution: `agentos/core/chat/comm_commands.py`
- Sandbox Configuration: `agentos/core/capabilities/capability_models.py`
- Audit System: `agentos/core/logging/store.py`
- Test Suite: `tests/test_guards.py`

---

## Security Review

**Threat Model Addressed**:

1. **Data Exfiltration**: Blocked by Phase Gate (no planning-phase I/O)
2. **Unauthorized Access**: Blocked by sandbox constraints and governance
3. **Prompt Injection**: Mitigated by Content Fence (UNTRUSTED_EXTERNAL_CONTENT)
4. **Attribution Forgery**: Prevented by Attribution Guard validation
5. **Audit Bypass**: Mandatory audit logging for all operations
6. **Trust Boundary Violation**: Clear separation via guards

**Attack Vectors Mitigated**:

- ✅ Silent network calls during planning → Blocked by Phase Gate
- ✅ Claiming external data as internal → Blocked by Attribution Guard
- ✅ Executing instructions from fetched content → Blocked by Content Fence
- ✅ Path traversal in file operations → Blocked by sandbox
- ✅ Unlimited network requests → Rate limited
- ✅ Long-running operations → Timeout enforced

**Residual Risks**:

- LLM may still misuse external content despite warnings (requires prompt engineering)
- Session ID spoofing (mitigated by secure session management)
- Timing attacks via execution timing (partially mitigated by constant-time operations)

---

## Approval

- **Proposed**: 2026-01-31
- **Accepted**: 2026-01-31
- **Authors**: AgentOS Team
- **Reviewers**: Security Team, Architecture Team

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-31 | 1.0 | Initial ADR establishing three core principles |

---

**Summary**: This ADR establishes three immutable principles for LLM interaction with external information: (1) LLMs cannot auto-trigger external I/O, (2) LLMs can only declare the need for external information, and (3) all external I/O must execute in a controlled command phase with full auditability. These principles are enforced through Phase Gate, Attribution Guard, and Content Fence, creating a secure, transparent, and auditable architecture for external information access.
