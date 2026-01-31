# ADR-CHAT-MODE-001: Conversation Mode Architecture

**Status**: Accepted
**Date**: 2026-01-31
**Authors**: AgentOS Architecture Team
**Supersedes**: None
**Related**: ADR-CHAT-COMM-001-Guards.md

---

## Context

### Problem Statement

AgentOS currently uses a two-layer model where task lifecycle states and execution phases are tightly coupled. As the system evolves to support richer conversational experiences, we need to separate three distinct concerns:

1. **User Experience & Output Style**: How the agent communicates and what format it uses
2. **Security & Permission Boundaries**: What capabilities the agent can access
3. **Task State Management**: Where in the workflow lifecycle a task resides

The current system conflates these concerns, leading to:
- Semantic confusion between "mode" and "phase"
- Difficulty adding new interaction styles without touching security code
- Risk of accidentally granting permissions when changing conversation styles
- Unclear boundaries between UX concerns and security enforcement

### Current State Analysis

**Existing Phase Gate System** (from ADR-CHAT-COMM-001):
- Two-phase model: `planning` and `execution`
- `planning`: Read-only, safe capabilities (web_fetch, web_search)
- `execution`: Full capabilities (bash, file operations, extensions)
- Phase transitions require explicit user approval via `/execute` command

**Limitations**:
- Phase is overloaded: controls both UX and permissions
- Adding new conversation styles requires modifying security layer
- No way to have different conversation tones within the same phase
- User confusion: "What does 'execution' mean for a chat conversation?"

---

## Decision

### Three-Layer Architecture Model

We adopt a clean separation of concerns with three independent layers:

```
┌─────────────────────────────────────────────────────┐
│  Layer 1: Conversation Mode (Semantic Layer)        │
│  Purpose: UX, tone, output format, user experience  │
│  Values: chat, discussion, plan, development, task  │
│  Controlled by: User preference, conversation context│
└─────────────────────────────────────────────────────┘
                        ↓ suggests but does NOT control
┌─────────────────────────────────────────────────────┐
│  Layer 2: Execution Phase (Permission Gate Layer)   │
│  Purpose: Security boundary, capability access       │
│  Values: planning, execution                         │
│  Controlled by: Explicit user commands (/execute)   │
└─────────────────────────────────────────────────────┘
                        ↓ enables/disables
┌─────────────────────────────────────────────────────┐
│  Layer 3: Task Lifecycle (State Machine Layer)      │
│  Purpose: Workflow state tracking                    │
│  Values: pending, active, paused, completed, etc.   │
│  Controlled by: Task engine state transitions        │
└─────────────────────────────────────────────────────┘
```

### Layer 1: Conversation Mode (Semantic Layer)

**Purpose**: Define how the agent communicates, not what it can do.

**Five Conversation Modes**:

1. **chat**: Casual, helpful assistant
   - Natural conversation flow
   - Explains reasoning
   - Asks clarifying questions
   - Default for general interactions

2. **discussion**: Analytical, exploratory dialogue
   - Deep analysis of problems
   - Multiple perspectives
   - Structured reasoning
   - Socratic questioning approach

3. **plan**: Strategic planning focus
   - High-level architecture
   - Step-by-step planning
   - Resource estimation
   - Risk assessment
   - No code generation (by convention, not enforcement)

4. **development**: Implementation focus
   - Code-centric output
   - Technical details
   - Implementation suggestions
   - Best practices

5. **task**: Goal-oriented, concise execution
   - Minimal explanation
   - Direct action
   - Progress reporting
   - Result-focused

**Key Principle**: Mode changes are UX-only transformations. They NEVER grant or revoke permissions.

### Layer 2: Execution Phase (Permission Gate Layer)

**Purpose**: Enforce security boundaries and capability access control.

**Two Phases** (unchanged from existing system):

1. **planning**:
   - Safe, read-only operations
   - Capabilities: `web_fetch`, `web_search`, `read_file`, `list_directory`
   - Cannot: Execute code, modify files, install extensions

2. **execution**:
   - Full system capabilities
   - Capabilities: All planning capabilities + `bash`, `write_file`, `extension_execute`
   - Requires explicit user approval to enter

**Phase Transition Rules**:
- Default start: `planning` phase
- Transition to `execution`: Requires `/execute` command or explicit user approval
- Transition to `planning`: Requires `/plan` command or explicit user approval
- Mode changes DO NOT trigger phase transitions

### Layer 3: Task Lifecycle (State Machine Layer)

**Purpose**: Track workflow state (unchanged from existing implementation).

**States**: `pending`, `active`, `blocked`, `paused`, `completed`, `failed`, `cancelled`

**Independence**: Task lifecycle states are orthogonal to both mode and phase.

---

## Architectural Principles

### Principle 1: Semantic Independence
```
Mode changes are pure UX transformations.
Changing mode MUST NOT alter security boundaries.
```

### Principle 2: Explicit Permission Control
```
Only explicit user commands can change execution phase.
No automatic phase transitions based on mode or context.
```

### Principle 3: Loose Coupling
```
Each layer has a single responsibility.
Layers communicate via well-defined interfaces.
Changes in one layer do not cascade to others.
```

### Principle 4: Defense in Depth
```
Mode provides UX hints, but phase enforces security.
Even if mode suggests "development", planning phase prevents execution.
```

---

## Security Model

### Hard Rules: Mode Cannot Bypass Phase Gates

**Rule 1: Mode is Advisory Only**
```python
# CORRECT: Mode suggests phase, user approves
if conversation_mode == "development":
    suggested_phase = "execution"
    ui.show_suggestion("Development mode works best in execution phase. /execute to switch?")
    # Wait for user approval - DO NOT auto-switch

# INCORRECT: Mode auto-switches phase
if conversation_mode == "development":
    execution_phase = "execution"  # SECURITY VIOLATION
```

**Rule 2: Phase Gates Are Immutable Per Mode**
```python
# Phase enforcement is mode-agnostic
def can_execute_capability(capability: str, phase: str) -> bool:
    if phase == "planning":
        return capability in SAFE_CAPABILITIES
    elif phase == "execution":
        return capability in ALL_CAPABILITIES
    # Mode is NOT a parameter here
```

**Rule 3: No Implicit Privilege Escalation**
```python
# CORRECT: Explicit phase check before execution
if execution_phase != "execution":
    raise PermissionError("Cannot execute bash in planning phase")
agent.execute_bash(command)

# INCORRECT: Mode-based bypass
if conversation_mode == "task":
    agent.execute_bash(command)  # NO PHASE CHECK - VIOLATION
```

### Permission Isolation Testing

All implementations MUST pass these tests:

```python
def test_mode_cannot_bypass_phase():
    """Changing mode in planning phase MUST NOT grant execution capabilities"""
    engine.set_phase("planning")
    engine.set_mode("development")

    # Must still be in planning phase
    assert engine.phase == "planning"

    # Must not be able to execute bash
    with pytest.raises(PermissionError):
        engine.execute_capability("bash", "ls")

def test_mode_change_preserves_phase():
    """Mode changes must preserve current phase"""
    engine.set_phase("execution")
    original_phase = engine.phase

    engine.set_mode("chat")
    assert engine.phase == original_phase

    engine.set_mode("discussion")
    assert engine.phase == original_phase

def test_phase_transition_requires_explicit_command():
    """Only explicit commands can change phase"""
    engine.set_mode("development")  # Might suggest execution phase

    # Phase must not auto-switch
    assert engine.phase == "planning"

    # Only explicit command changes phase
    engine.execute_command("/execute")
    assert engine.phase == "execution"
```

---

## Consequences

### Positive

1. **Separation of Concerns**: UX, security, and workflow state are independent
2. **Extensibility**: New conversation modes can be added without touching security code
3. **User Clarity**: Clear mental model: mode = how, phase = what, lifecycle = where
4. **Security**: No accidental privilege escalation via mode changes
5. **Flexibility**: Same phase can support multiple conversation styles

### Negative

1. **Complexity**: Three layers instead of two
2. **User Education**: Users must understand mode vs phase distinction
3. **Migration**: Existing code may assume mode controls permissions
4. **UI Overhead**: Need to display both mode and phase to users

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Developers conflate mode and phase | High | Comprehensive documentation, code review checklist |
| Users confused by three-layer model | Medium | Clear UI indicators, contextual help |
| Legacy code bypasses phase gates | High | Mandatory security tests, static analysis |
| Performance overhead | Low | Layers are lightweight, minimal runtime cost |

---

## Implementation Guidance

### Mode-Phase Interaction Pattern

```python
class ConversationEngine:
    def __init__(self):
        self.mode: ConversationMode = "chat"
        self.phase: ExecutionPhase = "planning"
        self.lifecycle_state: TaskState = "pending"

    def set_mode(self, new_mode: ConversationMode):
        """Change conversation mode (UX only)"""
        old_mode = self.mode
        self.mode = new_mode

        # Suggest phase change if beneficial
        suggested_phase = self._suggest_phase_for_mode(new_mode)
        if suggested_phase != self.phase:
            self._notify_phase_suggestion(suggested_phase)

        # CRITICAL: Do NOT change phase automatically
        # Phase must remain unchanged until user approves

    def set_phase(self, new_phase: ExecutionPhase, approved: bool = False):
        """Change execution phase (requires approval)"""
        if not approved:
            raise SecurityError("Phase transition requires explicit user approval")

        self.phase = new_phase
        self._audit_log.record_phase_transition(new_phase)

    def execute_capability(self, capability: str, *args):
        """Execute capability with phase gate enforcement"""
        # Phase check is independent of mode
        if not self._is_capability_allowed(capability, self.phase):
            raise PermissionError(
                f"Capability '{capability}' not allowed in {self.phase} phase"
            )

        return self._invoke_capability(capability, *args)

    def _is_capability_allowed(self, capability: str, phase: ExecutionPhase) -> bool:
        """Phase gates are mode-agnostic"""
        if phase == "planning":
            return capability in ["web_fetch", "web_search", "read_file", "list_directory"]
        elif phase == "execution":
            return True  # All capabilities allowed
        return False

    def _suggest_phase_for_mode(self, mode: ConversationMode) -> ExecutionPhase:
        """Suggest optimal phase for mode (advisory only)"""
        mode_phase_hints = {
            "chat": None,  # No preference
            "discussion": "planning",  # Usually analytical
            "plan": "planning",  # Planning doesn't need execution
            "development": "execution",  # Coding needs file access
            "task": "execution",  # Tasks often need actions
        }
        return mode_phase_hints.get(mode)
```

---

## Examples: Mode Usage Scenarios

### Example 1: chat Mode (General Assistant)

**Scenario**: User asks "What's the best way to implement caching?"

**Mode**: `chat`
**Phase**: `planning` (default)
**Behavior**:
- Friendly, conversational tone
- Explains multiple approaches (in-memory, Redis, filesystem)
- Asks clarifying questions ("What's your scale?")
- Provides code examples as markdown
- Suggests `/execute` if user wants to implement

**Phase Stays Planning**: No automatic code execution.

---

### Example 2: discussion Mode (Architecture Exploration)

**Scenario**: User asks "Should we use microservices or monolith?"

**Mode**: `discussion`
**Phase**: `planning`
**Behavior**:
- Analytical, multi-perspective analysis
- Explores tradeoffs systematically
- Questions assumptions ("What's your team size?")
- Structured reasoning (pros/cons lists)
- No implementation details

**Phase Stays Planning**: Pure analysis, no code changes.

---

### Example 3: plan Mode (Strategic Planning)

**Scenario**: User requests "Plan the migration to AgentOS 2.0"

**Mode**: `plan`
**Phase**: `planning`
**Behavior**:
- High-level milestones
- Step-by-step breakdown
- Risk assessment
- Resource estimation
- No code generation (by convention)

**Phase Stays Planning**: Planning doesn't require execution capabilities.

---

### Example 4: development Mode (Implementation)

**Scenario**: User requests "Implement the new caching layer"

**Mode**: `development`
**Phase Suggestion**: `execution` (suggested to user)
**If User Approves /execute**:
- Code-centric output
- Writes files directly
- Runs tests
- Commits changes
- Technical, concise explanations

**Key Point**: Mode switched to `development` immediately, but phase only switched to `execution` after user approval.

---

### Example 5: task Mode (Goal Execution)

**Scenario**: User assigns "Fix the failing tests in test_auth.py"

**Mode**: `task`
**Phase Suggestion**: `execution` (suggested to user)
**If User Approves /execute**:
- Minimal explanation
- Directly modifies code
- Runs tests
- Reports: "Fixed. 3 tests now passing."
- No philosophical discussion

**Key Point**: Concise UX, but still respects phase gates.

---

## Integration with Existing Systems

### Phase Gate System (ADR-CHAT-COMM-001)

**No Breaking Changes**:
- Existing two-phase model (`planning`, `execution`) remains unchanged
- Phase gates continue to enforce capability access control
- `/execute` and `/plan` commands work identically

**Enhancement**:
- Mode provides richer UX within each phase
- Phase gates are now explicitly documented as mode-independent

### Task Lifecycle

**No Changes Required**:
- Task states (`pending`, `active`, `completed`, etc.) are orthogonal
- A task in `active` state can be in any mode and any phase
- Example: Active task, development mode, planning phase (reading code before implementing)

### Guards System

**Relationship**:
- Guards operate at the capability layer (below phase gates)
- Mode and phase are inputs to guard evaluation
- Guards may reference phase but MUST NOT be bypassed by mode

```python
class CapabilityGuard:
    def evaluate(self, capability: str, phase: ExecutionPhase, mode: ConversationMode):
        # Phase is authoritative for permissions
        if phase == "planning" and capability == "bash":
            return GuardResult(allowed=False, reason="bash not allowed in planning phase")

        # Mode can inform logging/audit but NOT permissions
        if mode == "development":
            self.audit_log.info(f"Development mode requesting {capability}")

        return GuardResult(allowed=True)
```

---

## Testing Requirements

### Mandatory Test Coverage

All implementations MUST include:

1. **Permission Isolation Tests** (see Security Model section)
2. **Mode Transition Tests**: Verify mode changes don't affect phase
3. **Phase Transition Tests**: Verify phase changes require approval
4. **Cross-Layer Independence Tests**: Change one layer, others unchanged
5. **Integration Tests**: Real scenarios with mode + phase combinations

### Test Coverage Checklist

- [ ] Mode change in planning phase cannot execute bash
- [ ] Mode change in execution phase preserves execution capabilities
- [ ] Phase change from planning to execution requires `/execute` command
- [ ] Phase change from execution to planning requires `/plan` command
- [ ] Mode suggestions appear but don't auto-switch phase
- [ ] All five modes work correctly in planning phase
- [ ] All five modes work correctly in execution phase
- [ ] Task lifecycle transitions are independent of mode and phase
- [ ] Guard evaluations respect phase regardless of mode
- [ ] Audit logs capture mode and phase separately

---

## Migration Path

### Phase 1: Add Mode Layer (Non-Breaking)
1. Introduce `ConversationMode` enum
2. Add `mode` field to conversation engine (default: `chat`)
3. Implement mode-specific formatters/prompts
4. No changes to phase logic

### Phase 2: Clarify Phase Independence
1. Audit all code that checks `phase`
2. Remove any mode-based permission logic
3. Add explicit phase checks before capability execution
4. Add security tests

### Phase 3: Update UI
1. Display both mode and phase indicators
2. Add mode selector (chat/discussion/plan/development/task)
3. Show phase suggestions when mode changes
4. Clarify that phase requires explicit command

### Phase 4: Documentation & Training
1. Update user guides
2. Add examples for each mode
3. Document mode-phase-lifecycle relationships
4. Create migration guide for extension developers

---

## Future Considerations

### Potential Extensions

1. **Custom Modes**: Allow users/extensions to define new conversation modes
2. **Mode Chaining**: "Start in discussion, then switch to development"
3. **Context-Aware Mode Suggestions**: AI suggests mode based on user intent
4. **Mode Profiles**: Save preferred mode+phase combinations per project
5. **Fine-Grained Phases**: Add `review` phase (read+write, but no execute)

### Open Questions

1. Should mode be per-conversation or per-message?
2. Should we support multiple modes in a single conversation?
3. How do modes interact with multi-agent scenarios?
4. Should extensions be able to define custom modes?

---

## References

- ADR-CHAT-COMM-001-Guards.md: Guard system architecture
- Phase Gate Implementation: `agentos/core/chat/guards/`
- Capability Registry: `agentos/core/capabilities/registry.py`
- Task Lifecycle: `agentos/core/task/lifecycle.py`

---

## Appendix: Decision Matrix

| Concern | Controlled By | Examples | Can Auto-Switch? |
|---------|---------------|----------|------------------|
| Output format | Mode | Verbose vs concise | Yes (UX change) |
| Conversation tone | Mode | Casual vs formal | Yes (UX change) |
| Capability access | Phase | Bash allowed? | No (security) |
| Permission boundary | Phase | File write allowed? | No (security) |
| Workflow position | Lifecycle | Task is active? | Yes (state machine) |
| Task completion | Lifecycle | Task done? | Yes (state machine) |

**Golden Rule**: If it affects **what the agent can do**, it's controlled by **phase** and requires explicit approval. If it affects **how the agent communicates**, it's controlled by **mode** and can change freely.

---

**End of ADR-CHAT-MODE-001**
