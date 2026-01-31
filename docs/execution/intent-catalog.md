# Execution Intent Catalog (v0.9.1)

## Overview

This catalog lists all example Execution Intents included in AgentOS v0.9.1. Each intent demonstrates a specific risk profile and interaction mode.

---

## Example Intents

### 1. intent_example_low_risk

**ID**: `intent_example_low_risk`  
**Title**: Add documentation comments to utility functions  
**Risk**: `low`  
**Mode**: `semi_auto`  
**Status**: `draft`

**Objective**: Add docstrings to utility functions in `agentos/utils/` module for better code documentation.

**Selected Workflows**:
- `documentation_workflow` (phases: analysis, implementation, review)

**Selected Agents**:
- `documentation_agent` (role: documenter)

**Planned Commands**:
- `scan_python_files` (read) - Identify undocumented functions
- `modify_python_file` (write) - Add docstrings

**Interaction**:
- Mode: `semi_auto`
- Question Budget: 2
- Question Policy: `blockers_only`

**Budgets**:
- Max Files: 15
- Max Commits: 1
- Max Tokens: 50000
- Max Cost: $2.00

**Review Requirements**: None (low risk)

**File**: `examples/intents/intent_example_low_risk.json`

---

### 2. intent_example_high_risk_interactive

**ID**: `intent_example_high_risk_interactive`  
**Title**: Migrate database schema to add user roles table  
**Risk**: `high`  
**Mode**: `interactive`  
**Status**: `proposed`

**Objective**: Add new `user_roles` table with foreign key to `users` table, including migration scripts.

**Selected Workflows**:
- `database_migration_workflow` (phases: design, implementation, validation, review)

**Selected Agents**:
- `database_architect` (role: schema designer)
- `migration_specialist` (role: migration executor)

**Planned Commands**:
- `scan_database_schema` (read) - Analyze current schema
- `generate_migration_script` (write) - Create migration SQL
- `validate_migration` (read) - Check migration safety

**Interaction**:
- Mode: `interactive` (HIGH RISK requires human approval)
- Question Budget: 10
- Question Policy: `conceptual_only`

**Budgets**:
- Max Files: 5
- Max Commits: 2
- Max Tokens: 150000
- Max Cost: $10.00

**Review Requirements**: `data`, `architecture`, `security`

**File**: `examples/intents/intent_example_high_risk_interactive.json`

---

### 3. intent_example_full_auto_readonly

**ID**: `intent_example_full_auto_readonly`  
**Title**: Scan codebase for security vulnerabilities  
**Risk**: `low`  
**Mode**: `full_auto`  
**Status**: `approved`

**Objective**: Run security scan tools across the codebase and generate vulnerability report.

**Selected Workflows**:
- `security_scan_workflow` (phases: setup, analysis)

**Selected Agents**:
- `security_scanner` (role: vulnerability analyzer)

**Planned Commands**:
- `scan_security_patterns` (read) - Detect common vulnerabilities
- `scan_dependencies` (read) - Check for known CVEs
- `generate_report` (read) - Compile findings

**Interaction**:
- Mode: `full_auto` (read-only, no human interaction)
- Question Budget: 0 (REQUIRED for full_auto)
- Question Policy: `never` (REQUIRED for full_auto)

**Budgets**:
- Max Files: 500 (full repo scan)
- Max Commits: 0 (no changes)
- Max Tokens: 200000
- Max Cost: $3.00

**Review Requirements**: None (read-only operation)

**File**: `examples/intents/intent_example_full_auto_readonly.json`

---

## Intent Risk Matrix

| Intent | Risk | Mode | Commands | Write Operations | Review Required |
|--------|------|------|----------|------------------|-----------------|
| low_risk | low | semi_auto | 2 | 1 (docstrings) | No |
| high_risk_interactive | high | interactive | 3 | 1 (migration) | Yes (3 types) |
| full_auto_readonly | low | full_auto | 3 | 0 | No |

---

## Interaction Mode Decision Tree

```
Is risk HIGH or CRITICAL?
  ├─ Yes → MUST use interactive or semi_auto
  └─ No → Can use any mode

Is operation READ-ONLY?
  ├─ Yes → Can use full_auto (if risk=low)
  └─ No → Must assess risk

Does operation modify critical data/infra?
  ├─ Yes → MUST use interactive
  └─ No → Can use semi_auto or interactive
```

---

## Evidence Reference Patterns

All intents must reference evidence. Common patterns:

- `scan://python_modules/<module_path>` - Python module scan
- `scan://file/<file_path>` - Single file scan
- `scan://security/<scan_type>` - Security scan results
- `scan://database/<schema_name>` - Database schema scan
- `fact://<fact_key>` - Registered fact
- `doc://<doc_path>` - Documentation reference

---

## Constraint Invariants (FROZEN)

All intents MUST satisfy these invariants:

1. **I1**: `constraints.execution = "forbidden"`
2. **I2**: `full_auto` ⇒ `question_budget=0` ∧ `question_policy=never`
3. **I3**: `risk ∈ {high, critical}` ⇒ `mode ≠ full_auto`
4. **I4**: `∀ cmd ∈ planned_commands: |cmd.evidence_refs| ≥ 1`
5. **I5**: `constraints.no_fabrication = true` ∧ `constraints.registry_only = true`

---

## Usage in SDLC Phases

### Analysis Phase
- Intents define what to investigate
- Evidence gathering (scan commands)
- Risk assessment
- Example: `intent_example_full_auto_readonly`

### Design Phase
- Intents propose implementation approach
- Workflow/agent selection
- Budget estimation
- Example: `intent_example_high_risk_interactive`

### Implementation Phase
- Intents specify change scope
- Command sequence planning
- Lock scope definition
- Example: `intent_example_low_risk`

### Review Phase
- Intents await approval
- Review requirements validation
- Risk re-assessment
- Status: `proposed` → `approved`/`rejected`

---

## Next Steps (Out of Scope for v0.9.1)

Future versions will add:

- **v0.9.2**: Coordinator to execute approved intents
- **v0.9.3**: Intent runtime evaluator
- **v0.9.4**: Intent conflict detection
- **v0.9.5**: Intent versioning and rollback

---

**Version**: v0.9.1  
**Status**: FROZEN - Production Ready  
**Last Updated**: 2026-01-25
