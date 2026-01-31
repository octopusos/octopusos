# WebUI Capability Matrix

**Version**: v0.3.2
**Last Updated**: 2026-01-29
**Status**: Living Document

This document provides a comprehensive comparison of feature support between AgentOS CLI and WebUI interfaces, establishing clear boundaries for what operations can be performed through each interface.

---

## Legend

| Symbol | Meaning | Description |
|--------|---------|-------------|
| ✅ | Full WebUI Support | Feature fully implemented in WebUI with equivalent functionality |
| 🔄 | Partial WebUI Support | Feature available but with limitations (read-only, proposal-only, etc.) |
| ❌ | CLI-Only | Feature deliberately restricted to CLI for safety/security |
| 📝 | WebUI Read-Only | Data can be viewed but not modified through WebUI |
| 🚫 | WebUI Prohibited | Feature explicitly prohibited in WebUI per ADR-005 |
| 🚧 | Under Development | Feature planned but not yet implemented |

---

## 1. Task Management

### Task Lifecycle Operations

| Feature | CLI Command | WebUI Support | Notes |
|---------|-------------|---------------|-------|
| List tasks | `agentos task list` | ✅ Full | TasksView with filtering, search, pagination |
| View task details | `agentos task show <id>` | ✅ Full | TasksView detail drawer with tabs |
| Create task | `agentos task create` | 🚧 Planned | UI coming soon |
| Cancel task | `agentos task cancel <id>` | ✅ Full | With confirmation dialog |
| Delete task | `agentos task delete <id>` | ❌ CLI-Only | Permanent operation, CLI-only |
| Task history | `agentos task history <id>` | 📝 Read-Only | View timeline, no modifications |
| Task dependencies | `agentos task deps <id>` | ✅ Full | View dependencies tab in TasksView |
| Task repositories | `agentos task repos <id>` | ✅ Full | View repos & changes tab |

### Task Execution

| Feature | CLI Command | WebUI Support | Notes |
|---------|-------------|---------------|-------|
| Dry-run planning | `agentos exec plan <id>` | ✅ Full | ExecutionPlansView (Wave4-X1) |
| Execute task | `agentos exec run <id>` | 🚫 Prohibited | ADR-005: CLI-only for safety |
| Rollback task | `agentos exec rollback <id>` | 🚫 Prohibited | ADR-005: High-risk, CLI-only |
| View execution plan | `agentos exec plan <id> --show` | ✅ Full | ExecutionPlansView with impact analysis |
| Request approval | `agentos exec approve-request <id>` | ✅ Full | Generate proposal + Guardian review |

---

## 2. Governance & Supervision

### Guardian Operations

| Feature | CLI Command | WebUI Support | Notes |
|---------|-------------|---------------|-------|
| View Guardian reviews | `agentos guardian list` | ✅ Full | GovernanceDashboardView + GuardianReviewPanel |
| Review status | `agentos guardian status <id>` | ✅ Full | Guardian Reviews tab in TasksView |
| Submit for review | `agentos guardian submit <id>` | ✅ Full | With admin token + confirmation |
| Approve verdict | `agentos guardian approve <id>` | ✅ Full | Admin token + confirmation + audit |
| Reject verdict | `agentos guardian reject <id>` | ✅ Full | Admin token + confirmation + audit |
| Override block | `agentos guardian override <id>` | ❌ CLI-Only | Security requirement, CLI-only |
| Review history | `agentos guardian history <id>` | 📝 Read-Only | View historical reviews |

### Lead Agent (Risk Mining)

| Feature | CLI Command | WebUI Support | Notes |
|---------|-------------|---------------|-------|
| Run scan | `agentos lead scan` | ❌ CLI-Only | Background job, CLI-only |
| View findings | `agentos lead findings` | ✅ Full | GovernanceFindingsView |
| Finding details | `agentos lead show <id>` | ✅ Full | Finding detail view with context |
| Scan history | `agentos lead history` | ✅ Full | LeadScanHistoryView |
| Create follow-up task | `agentos lead create-task <id>` | 🚧 Planned | Generate from finding |
| Configure rules | `agentos lead config` | 📝 Read-Only | View rules, edit via CLI |

### Decision Replay & Audit

| Feature | CLI Command | WebUI Support | Notes |
|---------|-------------|---------------|-------|
| View decision trace | `agentos replay trace <task_id>` | ✅ Full | Decision Trace tab in TasksView |
| Query decisions | `agentos replay query` | ✅ Full | Filter/search in trace viewer |
| Decision statistics | `agentos replay stats` | ✅ Full | GovernanceDashboardView metrics |
| Lag analysis | `agentos replay lag <task_id>` | ✅ Full | DecisionLagSource component |
| Replay export | `agentos replay export <task_id>` | 🔄 Partial | View/copy, no file download yet |
| Modify audit | N/A | 🚫 Prohibited | ADR-004 F-1: Immutable audit trail |

---

## 3. Intent & Content Management

### Intent Operations (Builder/Evaluator)

| Feature | CLI Command | WebUI Support | Notes |
|---------|-------------|---------------|-------|
| Build intent | `agentos builder run` | 🔄 Partial | IntentWorkbenchView: explain + diff only |
| View intent | `agentos builder show <id>` | ✅ Full | IntentWorkbenchView with versioning |
| Compare intents | `agentos evaluator diff <id1> <id2>` | ✅ Full | Side-by-side diff in workbench |
| Merge intent | `agentos evaluator merge <id>` | 📝 Proposal-Only | Generate merge proposal, no direct merge |
| Intent history | `agentos builder history <id>` | ✅ Full | View version timeline |
| Validate intent | `agentos evaluator validate <id>` | ✅ Full | Show validation results |

### Content Registry ✅ PROD-READY

| Feature | CLI Command | WebUI Support | Notes |
|---------|-------------|---------------|-------|
| List content | `agentos content list` | ✅ Full | ContentRegistryView with filters |
| View content | `agentos content show <id>` | ✅ Full | Detail view with versions |
| Upload content | `agentos content upload` | ❌ CLI-Only | File upload, CLI-only |
| Register content | `agentos content register` | ✅ Full | Admin token + confirmation + audit |
| Activate version | `agentos content activate <id>` | ✅ Full | Admin token + confirmation + audit |
| Deprecate version | `agentos content deprecate <id>` | ✅ Full | Admin token + confirmation + audit |
| Freeze version | `agentos content freeze <id>` | ✅ Full | Admin token + confirmation + audit |
| Delete content | `agentos content delete <id>` | ❌ CLI-Only | Permanent operation, CLI-only |
| Content stats | `agentos content stats` | ✅ Full | Statistics by type/status |
| Content mode | `agentos content mode` | ✅ Full | Show database mode |

**Database**: v23 schema, `content_items` table
**State Machine**: draft → active → deprecated/frozen
**Security**: Admin token + confirmation + audit logging
**Test Coverage**: 22/22 API tests passing (100%)

### Answer Packs ✅ PROD-READY

| Feature | CLI Command | WebUI Support | Notes |
|---------|-------------|---------------|-------|
| List answer packs | `agentos answers list` | ✅ Full | AnswerPacksView |
| Create pack | `agentos answers create` | ✅ Full | Form-based creation (admin token required) |
| View pack | `agentos answers show <id>` | ✅ Full | Detail view with Q&A pairs |
| Validate pack | `agentos answers validate <id>` | ✅ Full | Show validation results |
| Apply pack | `agentos answers apply <id>` | 📝 Proposal-Only | Generate application proposal |
| Link to task | `agentos answers link <id> <task_id>` | ✅ Full | Associate with task |
| Related entities | `agentos answers related <id>` | ✅ Full | Show linked tasks/intents |
| Delete pack | `agentos answers delete <id>` | ❌ CLI-Only | Permanent operation, CLI-only |

**Database**: v23 schema, `answer_packs` + `answer_pack_links`
**Workflow**: Create → Validate → Apply Proposal → Guardian Review
**Link Tracking**: Relationships with tasks/intents
**Test Coverage**: 36/36 core tests passing (100%)

---

## 4. Projects & Multi-Repository

### Project Management

| Feature | CLI Command | WebUI Support | Notes |
|---------|-------------|---------------|-------|
| List projects | `agentos project list` | ✅ Full | ProjectsView with cards |
| View project | `agentos project show <name>` | ✅ Full | Project detail with repos |
| Create project | `agentos project create` | ❌ CLI-Only | Complex config, CLI-only |
| Import project | `agentos project import <path>` | ❌ CLI-Only | File-based, CLI-only |
| Edit project | `agentos project edit <name>` | 📝 Read-Only | View config, edit via CLI |
| Delete project | `agentos project delete <name>` | ❌ CLI-Only | Permanent operation, CLI-only |
| Project validation | `agentos project validate <name>` | ✅ Full | Show validation status |

### Repository Operations

| Feature | CLI Command | WebUI Support | Notes |
|---------|-------------|---------------|-------|
| List repos | `agentos project repos <name>` | ✅ Full | ProjectsView repos section |
| Add repo | `agentos project add-repo` | ❌ CLI-Only | Git operations, CLI-only |
| Remove repo | `agentos project remove-repo` | ❌ CLI-Only | Destructive operation, CLI-only |
| Check permissions | `agentos project check-perms` | ✅ Full | Permission indicators in UI |
| View changes | `agentos project diff <repo>` | ✅ Full | TasksView repos tab |
| Cross-repo trace | `agentos project trace <task_id>` | ✅ Full | Multi-repo dependency graph |

---

## 5. Knowledge & Context

### Knowledge Base

| Feature | CLI Command | WebUI Support | Notes |
|---------|-------------|---------------|-------|
| Query knowledge | `agentos knowledge query` | ✅ Full | KnowledgePlaygroundView |
| View sources | `agentos knowledge sources` | ✅ Full | KnowledgeSourcesView |
| Add source | `agentos knowledge add` | ❌ CLI-Only | File operations, CLI-only |
| Remove source | `agentos knowledge remove` | ❌ CLI-Only | Permanent operation, CLI-only |
| Index jobs | `agentos knowledge jobs` | ✅ Full | KnowledgeJobsView |
| Health check | `agentos knowledge health` | ✅ Full | KnowledgeHealthView |

### Context Management

| Feature | CLI Command | WebUI Support | Notes |
|---------|-------------|---------------|-------|
| View context | `agentos context show` | ✅ Full | ContextView with status |
| Context status | `agentos context status` | ✅ Full | Real-time status pills |
| Clear context | `agentos context clear` | 🔄 Partial | With confirmation dialog |
| Context history | `agentos context history` | 📝 Read-Only | View historical context |

---

## 6. Authentication & Configuration

### Authentication Profiles ✅ PROD-READY (Read-Only)

| Feature | CLI Command | WebUI Support | Notes |
|---------|-------------|---------------|-------|
| List profiles | `agentos auth list` | ✅ Read-Only | AuthReadOnlyCard component, credential masking |
| View profile | `agentos auth show <name>` | ✅ Read-Only | View details, sanitized output |
| Add profile | `agentos auth add` | ❌ CLI-Only | Security requirement, CLI-only |
| Edit profile | `agentos auth edit <name>` | ❌ CLI-Only | Security requirement, CLI-only |
| Delete profile | `agentos auth delete <name>` | ❌ CLI-Only | Security requirement, CLI-only |
| Test profile | `agentos auth test <name>` | ✅ Full | Test connection button |
| Validate profile | `agentos auth validate <name>` | ✅ Full | Connection validation |

**Design Decision**: Write operations remain CLI-only for security (credential handling, key storage).
**Security**: Credential masking for all sensitive fields (passwords, tokens, SSH keys)
**Test Coverage**: Read operations fully tested and functional

### Configuration

| Feature | CLI Command | WebUI Support | Notes |
|---------|-------------|---------------|-------|
| View config | `agentos config show` | ✅ Full | ConfigView with tabs |
| Edit config | `agentos config edit` | 🔄 Partial | Some settings editable, others CLI-only |
| Lead rules | `agentos config lead-rules` | 📝 Read-Only | View rules, edit via CLI |
| Governance policies | `agentos config policies` | 📝 Read-Only | View policies, edit via CLI |
| Export config | `agentos config export` | ✅ Full | Copy to clipboard |
| Import config | `agentos config import` | ❌ CLI-Only | File-based, CLI-only |

---

## 7. Sessions & Chat

### Session Management

| Feature | CLI Command | WebUI Support | Notes |
|---------|-------------|---------------|-------|
| List sessions | `agentos session list` | ✅ Full | SessionsView (PR-3) |
| View session | `agentos session show <id>` | ✅ Full | Chat view with history |
| Create session | `agentos session create` | ✅ Full | New chat button |
| Rename session | `agentos session rename <id>` | ✅ Full | Inline edit in UI |
| Delete session | `agentos session delete <id>` | ✅ Full | With confirmation dialog |
| Session export | `agentos session export <id>` | 🚧 Planned | Coming soon |

### Chat Operations

| Feature | CLI Command | WebUI Support | Notes |
|---------|-------------|---------------|-------|
| Send message | Interactive CLI | ✅ Full | Primary interface |
| View history | `agentos session history <id>` | ✅ Full | Chat view timeline |
| Search messages | `agentos session search` | ✅ Full | Search bar in chat |
| Code snippets | N/A | ✅ Full | Syntax highlighting, copy button |
| HTML preview | N/A | ✅ Full | Sandboxed iframe preview |

---

## 8. Observability

### Events & Logs

| Feature | CLI Command | WebUI Support | Notes |
|---------|-------------|---------------|-------|
| View events | `agentos events list` | ✅ Full | EventsView with filtering |
| Event details | `agentos events show <id>` | ✅ Full | Event detail modal |
| Filter events | `agentos events list --type <type>` | ✅ Full | FilterBar component |
| View logs | `agentos logs tail` | ✅ Full | LogsView with real-time updates |
| Log search | `agentos logs search` | ✅ Full | Search/filter in UI |
| Export logs | `agentos logs export` | 🚧 Planned | Coming soon |

### History & Audit

| Feature | CLI Command | WebUI Support | Notes |
|---------|-------------|---------------|-------|
| View history | `agentos history` | ✅ Full | HistoryView |
| Audit trail | `agentos audit list` | ✅ Full | Audit tab in TasksView |
| Filter audit | `agentos audit list --task <id>` | ✅ Full | Filter by task/session |
| Audit export | `agentos audit export` | 🔄 Partial | View/copy, no file download yet |

---

## 9. System & Runtime

### System Information

| Feature | CLI Command | WebUI Support | Notes |
|---------|-------------|---------------|-------|
| View runtime | `agentos system info` | ✅ Full | RuntimeView |
| Health check | `agentos health` | ✅ Full | Health badge in header |
| System stats | `agentos system stats` | ✅ Full | GovernanceDashboardView |
| Support info | `agentos support` | ✅ Full | SupportView |

### Provider Management

| Feature | CLI Command | WebUI Support | Notes |
|---------|-------------|---------------|-------|
| List providers | `agentos provider list` | ✅ Full | ProvidersView |
| Configure provider | `agentos provider config <name>` | ✅ Full | Provider config form |
| Test provider | `agentos provider test <name>` | ✅ Full | Test connection button |
| Provider status | `agentos provider status` | ✅ Full | Real-time status indicators |

---

## 10. Agent Operations

### Skills & Memory

| Feature | CLI Command | WebUI Support | Notes |
|---------|-------------|---------------|-------|
| List skills | `agentos skill list` | ✅ Full | SkillsView |
| View skill | `agentos skill show <name>` | ✅ Full | Skill detail modal |
| Enable skill | `agentos skill enable <name>` | ✅ Full | Toggle in UI |
| Disable skill | `agentos skill disable <name>` | ✅ Full | Toggle in UI |
| View memory | `agentos memory show` | ✅ Full | MemoryView |
| Clear memory | `agentos memory clear` | 🔄 Partial | With confirmation dialog |

### Snippets

| Feature | CLI Command | WebUI Support | Notes |
|---------|-------------|---------------|-------|
| List snippets | `agentos snippet list` | ✅ Full | SnippetsView |
| Create snippet | `agentos snippet create` | ✅ Full | Form-based creation |
| Edit snippet | `agentos snippet edit <id>` | ✅ Full | Inline editor |
| Delete snippet | `agentos snippet delete <id>` | ✅ Full | With confirmation dialog |
| Use snippet | `agentos snippet use <id>` | ✅ Full | Insert into chat |

---

## Design Principles (per ADR-005)

### WebUI Can Do (✅):
1. **Observe & Monitor**: Display all data, metrics, and status
2. **Interpret & Explain**: Show diffs, traces, and impact analysis
3. **Approve & Govern**: Review and approve proposals with Guardian integration
4. **Generate Proposals**: Create proposals that require Guardian review
5. **Manage with Safety**: Execute operations with admin token + confirmation + audit

### WebUI Cannot Do (❌/🚫):
1. **Direct Execution**: No `exec run`, `exec rollback`, `exec replay` execution
2. **Auto-Remediation**: No auto-fix buttons for findings or errors
3. **Bypass Governance**: No skip-review or override buttons
4. **Modify Audit**: No editing of immutable audit trail
5. **Auth Management**: No create/edit/delete authentication profiles

---

## Frequently Asked Questions

### Q: Why can't I execute tasks from the WebUI?
**A**: Per ADR-005, task execution is CLI-only for safety. Execution requires deliberate action with full terminal audit trail. WebUI can generate execution proposals that go through Guardian review.

### Q: Why are auth profiles read-only in WebUI?
**A**: Authentication credentials are sensitive. Creation and editing require CLI's explicit confirmation flow and are protected by ADR-005 security requirements.

### Q: Can I rollback a task from WebUI?
**A**: No. Rollback is a high-risk operation that must be executed via CLI with explicit confirmation. WebUI can display rollback candidates and provide CLI commands.

### Q: How do I merge an intent if WebUI only shows "Proposal-Only"?
**A**:
1. Use IntentWorkbenchView to build and compare intents
2. Click "Submit Merge Proposal" to generate a proposal
3. Proposal enters Guardian review workflow
4. Once approved, use CLI: `agentos evaluator merge <id>`

### Q: What's the difference between "Full" and "Partial" support?
**A**:
- **Full**: Complete feature parity with CLI (read + write)
- **Partial**: Limited functionality (read-only, proposal-generation, or simplified UI)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v0.3.2 | 2026-01-29 | Initial matrix based on ADR-005 |
| v0.3.1 | 2026-01-28 | Governance semantic freeze (ADR-004) |
| v0.3.0 | 2026-01-26 | WebUI control surface stabilization |

---

## Related Documents
- [ADR-005: WebUI as Control Surface](./adr/ADR-005-webui-control-surface.md) - Architectural decision
- [ADR-004: Governance Semantic Freeze](./adr/ADR-004-governance-semantic-freeze.md) - Semantic constraints
- [WebUI Architecture](./webui/ARCHITECTURE.md) - Technical implementation
- [CLI Reference](./cli/COMMAND_REFERENCE.md) - Complete CLI command list
