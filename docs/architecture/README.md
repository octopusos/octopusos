# Architecture Documentation Index

This directory contains architectural decisions, design principles, and system blueprints for AgentOS.

⸻

## 📋 Architecture Decision Records (ADRs)

Architecture decisions that shape the long-term structure of AgentOS.

### Active ADRs

| ID | Title | Date | Status |
|----|-------|------|--------|
| [AD-001](VALIDATION_LAYERS.md#ad-001-validation-layers-responsibility-separation) | Validation Layers Responsibility Separation | 2026-01-27 | ✅ ACCEPTED |
| [ADR-V04](ADR_V04_PROJECT_AWARE_TASK_OS.md) | Project-Aware Task Operating System | 2026-01-29 | ✅ ACCEPTED |
| [ADR-V06-BOUNDARIES](ADR_EXECUTION_BOUNDARIES_FREEZE.md) | Execution Boundaries Freeze | 2026-01-30 | 🔒 FROZEN |
| [ADR-CAP-001](ADR_CAPABILITY_RUNNER.md) | Capability Runner Architecture | 2026-01-30 | ✅ ACCEPTED |

### ADR Template

When creating new ADRs, include:
- **Context**: What is the problem or decision we're facing?
- **Decision**: What is the chosen solution?
- **Rationale**: Why did we choose this over alternatives?
- **Consequences**: What are the trade-offs and implications?
- **References**: Related documents, code, or discussions

⸻

## 🏗️ Core Architecture Documents

### Validation & Verification
- **[Validation Layers](VALIDATION_LAYERS.md)** — Three-layer validation architecture (Schema / BR / DE)
  - Layer 1: Schema Validation (Structure)
  - Layer 2: Business Rules (Semantics)
  - Layer 3: Dry Executor RED LINE (Safety)
- **[Execution Boundaries Freeze](ADR_EXECUTION_BOUNDARIES_FREEZE.md)** — IRON LAW execution constraints (v0.6)
  - Boundary #1: Chat ≠ Execution
  - Boundary #2: Planning = Zero Side-Effect
  - Boundary #3: Execution Requires Frozen Spec

### Execution Model
- **[RED LINES](../executor/RED_LINES.md)** — Dry Executor safety constraints (DE1-DE6)
- **[Mode System](../mode/)** — Mode selection and pipeline execution
- **[Coordinator](../coordinator/)** — Multi-intent coordination and conflict resolution
- **[Capability Runner](ADR_CAPABILITY_RUNNER.md)** — Extension capability execution architecture (ADR-CAP-001)

### Memory & Knowledge
- **[Memory System](../memory/)** — Long-term memory and context management
- **[Project KB](../project_kb/)** — Project knowledge base and semantic search

⸻

## 📊 Architecture Diagrams

### System Overview
```
┌─────────────────────────────────────────────────┐
│              User Interface Layer                │
│  (CLI / WebUI / API)                            │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│           Task Management Layer                  │
│  (Task Controller / State Machine)              │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│          Coordination Layer                      │
│  (Intent Evaluator / Coordinator / Adjudicator) │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│           Execution Layer                        │
│  (Mode Pipeline / Dry Executor / Real Executor) │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│          Infrastructure Layer                    │
│  (Registry / Memory / KB / Locks / Gates)       │
└─────────────────────────────────────────────────┘
```

### Validation Flow
```
User Input
    ↓
┌──────────────────────┐
│ Layer 1: Schema      │ ← Structure validation
│ (SchemaValidator)    │
└──────────┬───────────┘
           │ [JSON valid?]
           ↓
┌──────────────────────┐
│ Layer 2: BR          │ ← Semantic validation
│ (OpenPlanVerifier)   │
└──────────┬───────────┘
           │ [Business logic OK?]
           ↓
┌──────────────────────┐
│ Layer 3: DE          │ ← Safety validation
│ (DryExecutorValidator)│
└──────────┬───────────┘
           │ [Safe to execute?]
           ↓
       Execution
```

⸻

## 🎯 Design Principles

### 1. Validation Layer Separation
- **Schema** validates structure
- **Business Rules** validate semantics
- **Dry Executor RED LINE** validates safety
- **These layers do NOT align** — intentional design choice

### 2. No Execution in Planning
- Dry Executor never runs code (DE1)
- All planning is side-effect free
- Execution requires explicit user approval

### 3. Evidence-Based Decisions
- Every plan node must have `evidence_refs` (DE4)
- No path fabrication allowed (DE3)
- Traceability is mandatory, not optional

### 4. Freeze-and-Verify
- Plans are frozen before execution (checksum)
- Changes require replan, not patch
- Lineage tracking for all artifacts

### 5. Progressive Disclosure
- Show summaries by default
- Details available on demand
- Complexity hidden until needed

⸻

## 📚 Related Documentation

- [Development Guide](../guides/DEVELOPMENT.md)
- [CLI Reference](../cli/)
- [API Documentation](../api/)
- [Testing Guide](../testing/)

⸻

## 🤝 Contributing to Architecture

When proposing architectural changes:

1. **Understand existing ADRs** — Don't break established decisions
2. **Document the "why"** — Rationale matters more than implementation
3. **Consider long-term impact** — Will this scale? Will future devs understand it?
4. **Get review before coding** — Architecture decisions are expensive to change

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for details.

⸻

## 📌 Version History

| Version | Date | Major Changes |
|---------|------|---------------|
| v0.3.1 | 2026-01-27 | Architecture stabilization, AD-001 formalized |
| v0.3.0 | 2026-01-25 | TUI removed, WebUI preparation |
| v0.2.x | 2026-01-* | Core system implementation |

⸻

**Last Updated**: 2026-01-27
**Maintained By**: AgentOS Core Team
