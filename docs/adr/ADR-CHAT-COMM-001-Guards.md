# ADR-CHAT-COMM-001: Chat ↔ CommunicationOS Security Guards

**Status**: Implemented
**Date**: 2026-01-30
**Authors**: AgentOS Team
**Related**: ADR-COMMUNICATION-OS-001, ADR-CHAT-001

## Context

The integration between Chat layer and CommunicationOS creates a security boundary that must be carefully managed. External communication operations (comm.*) can:

- Leak data during planning phase (before user approval)
- Claim external knowledge as internal/built-in
- Execute untrusted content from external sources
- Enable prompt injection attacks
- Bypass audit trails

Without proper guards, these risks could compromise system security, data integrity, and user trust.

## Decision

We implement **3 mandatory Guards** at the Chat layer to enforce security policies:

### 1. Phase Gate (Highest Priority)

**Purpose**: Prevent external operations during planning phase.

**Implementation**: `agentos/core/chat/guards/phase_gate.py`

**Rules**:
- Planning phase: No external communication (comm.*)
- Execution phase: All operations allowed
- Default: Block if phase unknown (fail-closed)

**Why Essential**:
- Planning should be pure computation without side effects
- Prevents accidental data leakage before user approval
- Ensures deterministic planning behavior
- Blocks timing attacks via planning-phase network calls

**Bypass Attempts to Watch For**:
1. Renaming operations to avoid "comm." prefix
   - Defense: Whitelist-based validation
2. Setting execution_phase to None or invalid values
   - Defense: Fail-closed by default
3. Wrapping comm operations in non-comm namespaces
   - Defense: Prefix-based detection
4. Race conditions in phase transitions
   - Defense: Immutable phase context

**Example**:
```python
from agentos.core.chat.guards import PhaseGate, PhaseGateError

# In comm_commands.py execute() method:
try:
    PhaseGate.check("comm.search", execution_phase)
except PhaseGateError as e:
    return {"error": str(e), "blocked": True}

# Proceed with operation...
```

---

### 2. Attribution Freeze

**Purpose**: Enforce proper attribution of external knowledge.

**Implementation**: `agentos/core/chat/guards/attribution.py`

**Rules**:
- All external data must include attribution
- Attribution format: "CommunicationOS (search/fetch) in session {session_id}"
- Chat cannot claim external knowledge as its own

**Why Essential**:
- Prevents Chat from claiming external knowledge as built-in
- Enables proper audit trails for data sources
- Supports compliance with data attribution requirements
- Allows users to distinguish internal vs external knowledge

**Bypass Attempts to Watch For**:
1. Omitting attribution metadata
   - Defense: Mandatory validation before data ingress
2. Using incorrect attribution format
   - Defense: Strict format validation
3. Forging attribution with wrong session IDs
   - Defense: Session ID must match current session
4. Post-processing to remove attribution
   - Defense: Attribution frozen at ingress point
5. Wrapping attributed content without preserving markers
   - Defense: Immutable attribution in metadata

**Example**:
```python
from agentos.core.chat.guards import AttributionGuard, AttributionViolation

# In adapter layer before returning data:
attribution = AttributionGuard.format_attribution("search", session_id)
data = {
    "results": search_results,
    "metadata": {
        "attribution": attribution
    }
}

try:
    AttributionGuard.enforce(data, session_id)
except AttributionViolation as e:
    raise ValueError(f"Attribution validation failed: {e}")

return data
```

---

### 3. Untrusted Content Fence

**Purpose**: Mark and isolate external content.

**Implementation**: `agentos/core/chat/guards/content_fence.py`

**Rules**:
- All fetched content is UNTRUSTED_EXTERNAL_CONTENT
- Can be used for: summarization, citation, reference
- Cannot be used for: execute instructions, run code, modify system
- LLM receives explicit warning

**Why Essential**:
- Prevents treating external content as trusted instructions
- Blocks prompt injection attacks via fetched content
- Establishes clear trust boundaries
- Provides explicit usage guidelines to LLM

**Bypass Attempts to Watch For**:
1. Removing UNTRUSTED_EXTERNAL_CONTENT marker
   - Defense: Immutable marker on all external content
2. Stripping warning messages
   - Defense: Warning injected into LLM prompt
3. Repackaging content without markers
   - Defense: Content wrapped in safety envelope
4. Instructing LLM to ignore warnings
   - Defense: Explicit allowed/forbidden use cases
5. Mixing trusted and untrusted content without separation
   - Defense: Source URL preserved for audit

**Example**:
```python
from agentos.core.chat.guards import ContentFence

# When fetching external content:
fetched_content = fetch_from_url(url)
wrapped = ContentFence.wrap(fetched_content, url)

# When passing to LLM:
llm_prompt = ContentFence.get_llm_prompt_injection(wrapped)
llm_response = llm.generate(llm_prompt)

# For display:
display_text = ContentFence.unwrap_for_display(wrapped)
```

---

## Integration Points

### 1. comm_commands.py (Phase Gate)

In the `execute()` method of each comm command:

```python
def execute(self, args: str, session_id: str, execution_phase: str):
    # FIRST: Check phase gate
    try:
        PhaseGate.check(f"comm.{self.command_name}", execution_phase)
    except PhaseGateError as e:
        return {
            "error": str(e),
            "blocked_by": "phase_gate",
            "phase": execution_phase
        }

    # Proceed with operation...
```

### 2. Adapter Layer (Attribution)

In the adapter that wraps CommunicationService responses:

```python
def _format_response(self, raw_response, operation: str, session_id: str):
    attribution = AttributionGuard.format_attribution(operation, session_id)

    data = {
        "results": raw_response,
        "metadata": {
            "attribution": attribution,
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id
        }
    }

    # Validate before returning
    AttributionGuard.enforce(data, session_id)
    return data
```

### 3. Fetch Handler (Content Fence)

When fetching external content:

```python
def handle_fetch(self, url: str, session_id: str):
    # Fetch content
    content = self.fetcher.fetch(url)

    # Wrap with fence
    wrapped = ContentFence.wrap(content, url)

    # Add attribution
    attribution = AttributionGuard.format_attribution("fetch", session_id)

    return {
        "content": wrapped,
        "metadata": {
            "attribution": attribution
        }
    }
```

---

## Test Requirements

All three guards must have comprehensive test coverage:

### Phase Gate Tests
- ✅ Block comm.* operations in planning phase
- ✅ Allow comm.* operations in execution phase
- ✅ Block comm.* operations in unknown phase
- ✅ Allow non-comm operations in all phases
- ✅ Non-throwing is_allowed() method
- ✅ Phase validation

### Attribution Tests
- ✅ Enforce correct attribution format
- ✅ Reject missing attribution
- ✅ Reject wrong prefix
- ✅ Reject wrong session ID
- ✅ Format helper generates valid attribution
- ✅ Format validation method
- ✅ Handle missing metadata field

### Content Fence Tests
- ✅ Wrap content with marker and warning
- ✅ Generate LLM prompt injection
- ✅ Identify wrapped content
- ✅ Unwrap for display with warnings
- ✅ Reject unwrapping invalid content
- ✅ Preserve source URL

### Integration Tests
- ✅ All three guards working together
- ✅ Planning phase blocks properly
- ✅ Missing attribution caught

**Test Results**: 22/22 tests passing

---

## Consequences

### Positive

1. **Defense in Depth**: Multiple layers of protection
2. **Fail-Closed**: Unknown states default to blocked
3. **Clear Boundaries**: Explicit trust boundaries between layers
4. **Audit Trail**: All external data properly attributed
5. **Prompt Injection Protection**: External content marked as untrusted

### Negative

1. **Performance Overhead**: Additional validation on each operation
2. **Integration Complexity**: All comm operations must check guards
3. **Error Handling**: Must handle guard exceptions properly

### Neutral

1. **Enforcement Responsibility**: Guards are enforced at Chat layer, not CommunicationOS
2. **Session Management**: Requires session_id tracking throughout call chain
3. **Phase Management**: Requires execution_phase tracking

---

## Guard Activation Checklist

When integrating a new comm operation:

- [ ] Add PhaseGate.check() at start of execute()
- [ ] Generate attribution with AttributionGuard.format_attribution()
- [ ] Validate attribution with AttributionGuard.enforce()
- [ ] Wrap external content with ContentFence.wrap()
- [ ] Inject LLM warning with ContentFence.get_llm_prompt_injection()
- [ ] Add tests for all three guards
- [ ] Document guard integration in operation docs

---

## Security Review

**Threat Model**:
1. **Data Leakage**: Phase Gate prevents planning-phase leaks
2. **Attribution Forgery**: Attribution Guard enforces format and session
3. **Prompt Injection**: Content Fence marks external content as untrusted
4. **Trust Boundary Violation**: All three guards establish clear boundaries

**Attack Vectors Mitigated**:
- Planning-phase network calls → Blocked by Phase Gate
- Claiming external knowledge as internal → Blocked by Attribution Guard
- Executing instructions from fetched content → Blocked by Content Fence
- Bypassing audit trails → Prevented by mandatory attribution

**Residual Risks**:
- Guards only protect Chat layer (CommunicationOS must have own security)
- LLM may still misuse external content despite warnings
- Session ID spoofing (mitigated by secure session management)

---

## References

- [Phase Gate Implementation](../../agentos/core/chat/guards/phase_gate.py)
- [Attribution Guard Implementation](../../agentos/core/chat/guards/attribution.py)
- [Content Fence Implementation](../../agentos/core/chat/guards/content_fence.py)
- [Guard Tests](../../tests/test_guards.py)
- [CommunicationOS ADR](./ADR-COMMUNICATION-OS-001.md)

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-30 | 1.0 | Initial implementation of all three guards |
