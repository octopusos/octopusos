# Architecture Decision Records (ADR)

This directory contains Architecture Decision Records for AgentOS. ADRs document significant architectural decisions made during the development of the system.

## What is an ADR?

An ADR (Architecture Decision Record) is a document that captures an important architectural decision made along with its context and consequences. ADRs help teams understand:

- **Why** a decision was made
- **What** alternatives were considered
- **When** the decision was made
- **Who** was involved
- **What** the consequences are

## ADR Index

### Core System Architecture

| ID | Title | Status | Date | Semantic Freeze |
|----|-------|--------|------|-----------------|
| [ADR-004](ADR-004-governance-semantic-freeze.md) | Governance Semantic Freeze | Accepted | 2026-01-28 | N/A |
| [ADR-004](ADR-004-memoryos-split.md) | MemoryOS Split | Accepted | 2026-01-25 | No |
| [ADR-007](ADR-007-Database-Write-Serialization.md) | Database Write Serialization | Accepted | 2026-01-29 | Yes |
| [ADR-010](ADR-010-No-Premature-Parallelization.md) | No Premature Parallelization | Accepted | 2026-01-29 | Yes |

### Chat & Communication

| ID | Title | Status | Date | Semantic Freeze |
|----|-------|--------|------|-----------------|
| [ADR-CHAT-003](ADR-CHAT-003-InfoNeed-Classification.md) | InfoNeed Classification | Accepted | 2026-01-31 | Yes |
| [ADR-CHAT-COMM-001](ADR-CHAT-COMM-001-Guards.md) | Communication Guards | Accepted | 2026-01-30 | Yes |
| [ADR-CHAT-MODE-001](ADR-CHAT-MODE-001-Conversation-Mode-Architecture.md) | Conversation Mode Architecture | Accepted | 2026-01-31 | Yes |
| [ADR-COMM-002](ADR-COMM-002-Search-Fetch-Brief-Pipeline.md) | Search Fetch Brief Pipeline | Accepted | 2026-01-31 | Yes |

### Extensions & Integrations

| ID | Title | Status | Date | Semantic Freeze |
|----|-------|--------|------|-----------------|
| [ADR-005](ADR-005-MCP-Marketplace.md) | MCP Marketplace | Accepted | 2026-01-31 | No |
| [ADR-005](ADR-005-webui-control-surface.md) | WebUI Control Surface | Accepted | 2026-01-29 | Yes |
| [ADR-EXT-001](ADR-EXT-001-declarative-extensions-only.md) | Declarative Extensions Only | Accepted | 2026-01-30 | Yes |
| [ADR-EXT-001](ADR-EXT-001-ENFORCEMENT.md) | Extension Enforcement | Accepted | 2026-01-30 | Yes |
| [ADR-EXT-002](ADR-EXT-002-python-only-runtime.md) | Python Only Runtime | Accepted | 2026-01-30 | Yes |
| [ADR-EXTERNAL-INFO-DECLARATION-001](ADR-EXTERNAL-INFO-DECLARATION-001.md) | External Info Declaration | Accepted | 2026-01-31 | Yes |

### Data & Evidence

| ID | Title | Status | Date | Semantic Freeze |
|----|-------|--------|------|-----------------|
| [ADR-008](ADR-008-Evidence-Types-Semantics.md) | Evidence Types Semantics | Accepted | 2026-01-29 | Yes |
| [ADR-009](ADR-009-Narrative-Positioning-Four-Pillars.md) | Narrative Positioning Four Pillars | Accepted | 2026-01-29 | Yes |

### Time & Timestamps

| ID | Title | Status | Date | Semantic Freeze |
|----|-------|--------|------|-----------------|
| [ADR-011](ADR-011-time-timestamp-contract.md) | Time & Timestamp Contract | Accepted | 2026-01-31 | **YES** |

### Legacy & Learning

| ID | Title | Status | Date | Semantic Freeze |
|----|-------|--------|------|-----------------|
| [ADR-005](ADR-005-self-heal-learning.md) | Self Heal Learning | Accepted | 2026-01-25 | No |
| [ADR-006](ADR-006-policy-evolution-safety.md) | Policy Evolution Safety | Accepted | 2026-01-25 | No |

### Other

| ID | Title | Status | Date | Semantic Freeze |
|----|-------|--------|------|-----------------|
| [ADR-BRAINOS-V01](ADR_BRAINOS_V01_COGNITIVE_ENTITY.md) | BrainOS V01 Cognitive Entity | Accepted | 2026-01-30 | No |
| [ADR-P2-SUBGRAPH](ADR_P2_SUBGRAPH_VISUAL_SEMANTICS.md) | P2 Subgraph Visual Semantics | Accepted | 2026-01-30 | No |

## ADR Statuses

- **Proposed**: Under discussion
- **Accepted**: Decision made and approved
- **Implemented**: Decision implemented in code
- **Deprecated**: No longer applies
- **Superseded**: Replaced by another ADR

## Semantic Freeze

Some ADRs are marked as **Semantic Freeze** - these define system-wide contracts that require team consensus to change. Any modifications to Semantic Freeze ADRs must:

1. Be documented as a new ADR revision
2. Gain team consensus
3. Consider impact on all downstream systems
4. Update all affected documentation

## Creating a New ADR

1. Copy the ADR template (if available)
2. Determine the next available ADR number
3. Fill in all required sections:
   - Status
   - Context (why is this decision needed?)
   - Decision (what was decided?)
   - Consequences (positive and negative)
4. Submit for review
5. Update this index after approval

## Questions?

If you have questions about any ADR or the ADR process, please contact the AgentOS architecture team.

---

**Last Updated**: 2026-01-31
