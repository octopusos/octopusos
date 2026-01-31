# Conversation Mode & Execution Phase - Architecture

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Chat Session                                │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                     Metadata (JSON)                        │  │
│  │                                                             │  │
│  │  ┌──────────────────────┐   ┌──────────────────────┐     │  │
│  │  │  conversation_mode   │   │  execution_phase     │     │  │
│  │  │                      │   │                      │     │  │
│  │  │  UI/UX Context       │   │  Security Context    │     │  │
│  │  │  ┌────────────────┐  │   │  ┌────────────────┐  │     │  │
│  │  │  │ chat           │  │   │  │ planning       │  │     │  │
│  │  │  │ discussion     │  │   │  │ execution      │  │     │  │
│  │  │  │ plan           │  │   │  └────────────────┘  │     │  │
│  │  │  │ development    │  │   │                      │     │  │
│  │  │  │ task           │  │   │  Controls:           │     │  │
│  │  │  └────────────────┘  │   │  • comm.* ops       │     │  │
│  │  │                      │   │  • External access   │     │  │
│  │  │  Affects:            │   │  • PhaseGate         │     │  │
│  │  │  • UI layout         │   │                      │     │  │
│  │  │  • Suggestions       │   │  Audited:            │     │  │
│  │  │  • Shortcuts         │   │  ✅ All changes      │     │  │
│  │  │                      │   │                      │     │  │
│  │  │  Audited:            │   │                      │     │  │
│  │  │  ❌ No audit         │   │                      │     │  │
│  │  └──────────────────────┘   └──────────────────────┘     │  │
│  │                                                             │  │
│  │  ⚠️  INDEPENDENT: Changes do not affect each other         │  │
│  │                                                             │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Component Interactions

```
┌─────────────────┐
│   User Action   │
└────────┬────────┘
         │
         v
┌────────────────────────────────────────────────────────┐
│                  ChatService                           │
│                                                         │
│  ┌─────────────────────┐  ┌────────────────────────┐  │
│  │ update_             │  │ update_execution_      │  │
│  │ conversation_mode() │  │ phase()                │  │
│  └──────────┬──────────┘  └──────────┬─────────────┘  │
│             │                        │                 │
│             v                        v                 │
│  ┌─────────────────────┐  ┌────────────────────────┐  │
│  │ Validate Mode       │  │ Validate Phase         │  │
│  │ (ConversationMode)  │  │ (planning/execution)   │  │
│  └──────────┬──────────┘  └──────────┬─────────────┘  │
│             │                        │                 │
│             v                        v                 │
│  ┌─────────────────────┐  ┌────────────────────────┐  │
│  │ Update Metadata     │  │ Update Metadata        │  │
│  └──────────┬──────────┘  └──────────┬─────────────┘  │
│             │                        │                 │
│             v                        v                 │
│  ┌─────────────────────┐  ┌────────────────────────┐  │
│  │ Log Info            │  │ Emit Audit Event       │  │
│  │ (No audit)          │  │ (with actor & reason)  │  │
│  └─────────────────────┘  └──────────┬─────────────┘  │
│                                      │                 │
└──────────────────────────────────────┼─────────────────┘
                                       │
                                       v
                         ┌──────────────────────────┐
                         │   Audit System           │
                         │   (audit.py)             │
                         │                          │
                         │   • task_audits table    │
                         │   • Structured logging   │
                         │   • Security compliance  │
                         └──────────────────────────┘
```

## Data Flow

### Conversation Mode Update Flow

```
User Request
    │
    v
update_conversation_mode(session_id, "development")
    │
    ├─→ Validate mode (ConversationMode enum)
    │   └─→ ValueError if invalid
    │
    ├─→ Update metadata["conversation_mode"]
    │
    ├─→ Log info message
    │
    └─→ Return (no audit)

execution_phase remains unchanged ✅
```

### Execution Phase Update Flow

```
User Request
    │
    v
update_execution_phase(session_id, "execution", actor="user", reason="...")
    │
    ├─→ Validate phase (planning/execution)
    │   └─→ ValueError if invalid
    │
    ├─→ Get current phase (for audit)
    │
    ├─→ Update metadata["execution_phase"]
    │
    ├─→ Emit audit event
    │   ├─→ event_type: "execution_phase_changed"
    │   ├─→ old_phase & new_phase
    │   ├─→ actor & reason
    │   └─→ timestamp
    │
    └─→ Log info message

conversation_mode remains unchanged ✅
```

## Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Security Layers                          │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Layer 1: Execution Phase Control                      │ │
│  │                                                          │ │
│  │  execution_phase                                         │ │
│  │      │                                                   │ │
│  │      ├─→ "planning"  → PhaseGate blocks comm.*          │ │
│  │      └─→ "execution" → PhaseGate allows comm.*          │ │
│  └────────────────────────────────────────────────────────┘ │
│                         │                                    │
│                         v                                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Layer 2: Phase Gate Enforcement                       │ │
│  │                                                          │ │
│  │  PhaseGate.check(operation, execution_phase)            │ │
│  │      │                                                   │ │
│  │      ├─→ If operation starts with "comm."               │ │
│  │      │   AND phase != "execution"                       │ │
│  │      │   → Raise PhaseGateError                         │ │
│  │      └─→ Otherwise allow                                │ │
│  └────────────────────────────────────────────────────────┘ │
│                         │                                    │
│                         v                                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Layer 3: Audit Logging                                │ │
│  │                                                          │ │
│  │  All phase changes logged:                              │ │
│  │  • Who changed it (actor)                               │ │
│  │  • Why (reason)                                         │ │
│  │  • When (timestamp)                                     │ │
│  │  • What (old_phase → new_phase)                         │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘

conversation_mode: NOT part of security model
```

## State Machine

### Conversation Mode States

```
      ┌──────────────────────────────────────────┐
      │         Any Mode Can Transition          │
      │         To Any Other Mode                │
      └──────────────────────────────────────────┘

┌──────────┐   ┌──────────────┐   ┌──────────┐
│   chat   │←→ │  discussion  │←→ │   plan   │
└──────────┘   └──────────────┘   └──────────┘
     ↕                ↕                  ↕
┌──────────────┐                  ┌──────────┐
│ development  │←────────────────→│   task   │
└──────────────┘                  └──────────┘

All transitions valid
No restrictions
No audit required
```

### Execution Phase States

```
            ┌──────────────────────────────────┐
            │   Requires Explicit Action       │
            │   + Actor + Reason                │
            │   = Audit Event                  │
            └──────────────────────────────────┘

┌──────────────┐                    ┌──────────────┐
│   planning   │ ───────────────→   │  execution   │
│  (default)   │  Enable comm.*     │  (explicit)  │
│              │                     │              │
│ • Safe mode  │ ←───────────────   │ • Full ops   │
│ • No comm.*  │  Disable comm.*    │ • Allow all  │
└──────────────┘                    └──────────────┘

Both transitions audited
```

## Independence Verification

```
┌─────────────────────────────────────────────────────────────┐
│                    Independence Matrix                       │
│                                                              │
│  ┌────────────────────┬─────────────────────────────────┐  │
│  │ Conversation Mode  │    Execution Phase              │  │
│  ├────────────────────┼─────────────────────────────────┤  │
│  │ chat               │ planning  ✅                     │  │
│  │ chat               │ execution ✅                     │  │
│  │ discussion         │ planning  ✅                     │  │
│  │ discussion         │ execution ✅                     │  │
│  │ plan               │ planning  ✅                     │  │
│  │ plan               │ execution ✅                     │  │
│  │ development        │ planning  ✅                     │  │
│  │ development        │ execution ✅                     │  │
│  │ task               │ planning  ✅                     │  │
│  │ task               │ execution ✅                     │  │
│  └────────────────────┴─────────────────────────────────┘  │
│                                                              │
│  All 10 combinations are valid and independent               │
└─────────────────────────────────────────────────────────────┘
```

## Example Scenarios

### Scenario 1: Safe Development
```
Session Start
    │
    v
conversation_mode: "development"  (UI for coding)
execution_phase: "planning"       (No external ops)
    │
    v
User codes without distractions
PhaseGate blocks comm.* operations
```

### Scenario 2: Research with Search
```
Session Start
    │
    v
conversation_mode: "discussion"   (UI for brainstorming)
execution_phase: "execution"      (Allow comm.search)
    │
    v
User can search web
PhaseGate allows comm.* operations
Audit log tracks phase
```

### Scenario 3: Dynamic Workflow
```
Start: mode=chat, phase=planning
    │
    v
User: "Search for papers"
    │
    v
System: update_execution_phase("execution", actor="user", reason="search")
Audit: planning → execution
    │
    v
Perform search
    │
    v
System: update_execution_phase("planning", actor="system", reason="done")
Audit: execution → planning
    │
    v
mode still "chat" (unchanged)
```

## Design Principles

1. **Separation of Concerns**
   - Mode: UI/UX layer
   - Phase: Security layer
   - No coupling between layers

2. **Fail-Safe Defaults**
   - Mode: "chat" (neutral)
   - Phase: "planning" (safe)
   - Always start in safe state

3. **Explicit Operations**
   - No automatic transitions
   - User must consciously choose
   - System suggests but doesn't enforce

4. **Audit Everything Security**
   - Phase changes always audited
   - Who, what, when, why tracked
   - Mode changes not audited (UI only)

5. **Independent Evolution**
   - Mode can add new values
   - Phase remains binary
   - Changes don't affect each other

## Related Documentation

- [Implementation](../../agentos/core/chat/service.py)
- [Models](../../agentos/core/chat/models.py)
- [Tests](../../tests/unit/core/chat/test_conversation_mode.py)
- [Phase Gate](../chat/guards/phase_gate.py)
- [Audit System](../../agentos/core/capabilities/audit.py)
