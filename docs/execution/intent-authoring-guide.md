# Execution Intent Authoring Guide (v0.9.1)

## Overview

Execution Intent is a **proposal/plan schema** that defines what an AI agent intends to do, not how to execute it. It serves as a governance artifact for review, approval, and audit.

**Core Principle**: Intent = Plan + Evidence + Constraints + Required Reviews  
**Prohibition**: No execution payload, no shell commands, no subprocess calls.

---

## Intent Structure

### Required Fields

#### 1. `id` (string)
Pattern: `^intent_[a-z0-9_]{6,64}$`

Example: `intent_add_logging_to_api`

#### 2. `type` (const)
Must be: `"execution_intent"`

#### 3. `title` (string)
5-160 characters, human-readable summary.

Example: `"Add structured logging to API endpoints"`

#### 4. `version` (string)
Semantic version: `"0.9.1"`

#### 5. `status` (enum)
- `draft` - work in progress
- `proposed` - ready for review
- `approved` - approved for execution
- `rejected` - rejected
- `superseded` - replaced by newer intent

#### 6. `created_at` (string, ISO8601)
Timestamp when intent was created.

#### 7. `lineage` (object)
```json
{
  "introduced_in": "0.9.1",
  "derived_from": [],
  "supersedes": []
}
```

#### 8. `scope` (object)
Defines what this intent will affect:

```json
{
  "project_id": "agentos",
  "repo_root": "/path/to/repo",
  "targets": {
    "files": ["agentos/api/routes.py"],
    "modules": ["agentos.api"],
    "areas": ["backend"]
  }
}
```

**Areas enum**: `frontend`, `backend`, `infra`, `docs`, `tests`, `ops`, `security`, `data`

#### 9. `objective` (object)
```json
{
  "goal": "Add structured logging to all API endpoints for better observability",
  "success_criteria": [
    "All API routes log request/response metadata",
    "Log format is JSON",
    "Performance impact < 5ms per request"
  ],
  "non_goals": [
    "Change existing log aggregation system",
    "Add distributed tracing"
  ]
}
```

#### 10. `selected_workflows` (array, min 1)
Workflows from the registry that will be used:

```json
[
  {
    "workflow_id": "feature_implementation_workflow",
    "phases": ["analysis", "design", "implementation", "validation"],
    "reason": "Standard feature workflow with testing"
  }
]
```

#### 11. `selected_agents` (array, min 1)
Agents from the registry that will participate:

```json
[
  {
    "agent_id": "code_change_agent",
    "role": "implementer",
    "responsibilities": [
      "Modify API route handlers",
      "Add logging calls",
      "Ensure error handling"
    ]
  }
]
```

#### 12. `planned_commands` (array)
Commands that will be executed (must be from registry):

```json
[
  {
    "command_id": "scan_python_files",
    "intent": "Identify all API route handlers",
    "effects": ["read"],
    "risk_level": "low",
    "evidence_refs": ["scan://python_modules/agentos.api"]
  },
  {
    "command_id": "modify_python_file",
    "intent": "Add logging import and calls",
    "effects": ["write"],
    "risk_level": "medium",
    "evidence_refs": ["scan://file/agentos/api/routes.py"]
  }
]
```

**Effects enum**: `read`, `write`, `network`, `deploy`, `security`, `data`  
**Risk levels**: `low`, `medium`, `high`, `critical`

#### 13. `interaction` (object)
Defines how AI interacts with human:

```json
{
  "mode": "semi_auto",
  "question_budget": 3,
  "question_policy": "blockers_only"
}
```

**Modes**:
- `interactive` - ask freely
- `semi_auto` - ask only important questions
- `full_auto` - no questions (requires `question_budget=0`, `question_policy=never`)

**Question policies**: `conceptual_only`, `blockers_only`, `never`

#### 14. `risk` (object)
```json
{
  "overall": "medium",
  "drivers": [
    "Modifying production API code",
    "Potential performance impact"
  ],
  "requires_review": ["release", "architecture"]
}
```

**Review types**: `security`, `data`, `release`, `architecture`, `cost`, `compliance`

#### 15. `budgets` (object)
Resource limits:

```json
{
  "max_files": 10,
  "max_commits": 2,
  "max_tokens": 100000,
  "max_cost_usd": 5.0
}
```

#### 16. `evidence_refs` (array, min 1)
References to scan results, facts, or other evidence:

```json
[
  "scan://python_modules/agentos.api",
  "fact://current_logging_strategy",
  "doc://api_standards.md"
]
```

#### 17. `constraints` (object)
**FROZEN CONSTRAINTS** (cannot be changed):

```json
{
  "execution": "forbidden",
  "no_fabrication": true,
  "registry_only": true,
  "lock_scope": {
    "mode": "files",
    "paths": ["agentos/api/routes.py"]
  }
}
```

**Lock scope modes**: `none`, `task`, `files`

#### 18. `audit` (object)
```json
{
  "created_by": "human_operator",
  "source": "human",
  "checksum": "abc123..."
}
```

**Source enum**: `human`, `agentos`, `imported`

---

## v0.9.1 Red Lines (I1-I5)

### I1 — No Execution Payload
Intent **MUST NOT** contain any execution-related fields:
- ❌ `execute`, `run`, `shell`, `bash`, `python`, `powershell`
- ❌ `subprocess`, `command_line`, `script`

### I2 — full_auto Question Constraint
If `interaction.mode = "full_auto"`, then:
- `question_budget` MUST be `0`
- `question_policy` MUST be `"never"`

(Schema enforced via `allOf` constraint)

### I3 — High Risk Cannot Be full_auto
If `risk.overall` is `"high"` or `"critical"`, then:
- `interaction.mode` MUST be `"interactive"` or `"semi_auto"`

(Schema enforced)

### I4 — Evidence Required for All Commands
Every item in `planned_commands` MUST have:
- `evidence_refs` (array, min 1 item)

### I5 — Registry Only, No Fabrication
- `constraints.no_fabrication` MUST be `true`
- `constraints.registry_only` MUST be `true`
- All `workflow_id`, `agent_id`, `command_id` must reference registered content

---

## Validation Checklist

Before submitting an intent:

- [ ] `id` matches pattern `intent_[a-z0-9_]{6,64}`
- [ ] `type` is `"execution_intent"`
- [ ] `lineage.introduced_in` is set
- [ ] `selected_workflows` has at least 1 workflow
- [ ] `selected_agents` has at least 1 agent
- [ ] All `planned_commands` have `evidence_refs`
- [ ] `constraints.execution` is `"forbidden"`
- [ ] `constraints.no_fabrication` is `true`
- [ ] `constraints.registry_only` is `true`
- [ ] If `full_auto`, then `question_budget=0` and `question_policy=never`
- [ ] If `high`/`critical` risk, mode is NOT `full_auto`
- [ ] If any command has `write`/`deploy` effects, `requires_review` includes at least one review type
- [ ] `audit.checksum` is SHA-256 hash of canonical JSON

---

## Testing Your Intent

```bash
# Validate schema
uv run python scripts/validate_intents.py --file examples/intents/my_intent.json

# Validate all intents
uv run python scripts/validate_intents.py --input examples/intents/

# Explain intent structure
uv run python scripts/validate_intents.py --explain --file examples/intents/my_intent.json
```

---

## Common Errors

### ❌ Anti-Pattern 1: Including Execution Payload
```json
{
  "execute": "bash script.sh"  // FORBIDDEN
}
```

### ❌ Anti-Pattern 2: full_auto with Questions
```json
{
  "interaction": {
    "mode": "full_auto",
    "question_budget": 5  // INVALID, must be 0
  }
}
```

### ❌ Anti-Pattern 3: High Risk + full_auto
```json
{
  "risk": { "overall": "high" },
  "interaction": { "mode": "full_auto" }  // INVALID
}
```

### ❌ Anti-Pattern 4: Command Without Evidence
```json
{
  "planned_commands": [{
    "command_id": "do_something",
    "evidence_refs": []  // INVALID, must have >= 1
  }]
}
```

### ❌ Anti-Pattern 5: Fabricated IDs
```json
{
  "selected_workflows": [{
    "workflow_id": "my_made_up_workflow"  // Must be in registry
  }]
}
```

---

## Contribution Guidelines

1. Create intent as JSON file in `examples/intents/`
2. Run schema validation: `scripts/validate_intents.py`
3. Run all gates: `scripts/gates/v091_gate_*.{py,sh}`
4. Add entry to `docs/execution/intent-catalog.md`
5. Submit for review

---

**Version**: v0.9.1  
**Status**: FROZEN - Production Ready  
**Last Updated**: 2026-01-25
