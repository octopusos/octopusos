# v0.9.3 Red Lines — Intent Evaluator

## Overview

Red Lines are **non-negotiable constraints** enforced at multiple layers (Schema, Runtime, Static, Gates) to ensure the Intent Evaluator produces only governance decisions, never executable payloads.

**Status**: 🔒 FROZEN (v0.9.3)  
**Enforcement**: 3-layer protection (Schema + Runtime + Static/Gates)

---

## Red Line Summary

| ID | Description | Schema | Runtime | Static | Gate |
|----|-------------|--------|---------|--------|------|
| **RL-E1** | No Execution Payload | ✅ | ✅ | ✅ | D |
| **RL-E2** | Merged Intent Must Have Lineage | ✅ | ✅ | ✅ | J |

---

## RL-E1: Evaluator Must Not Produce Executable Payload

### Rationale

The Intent Evaluator is a **governance layer**, not an execution layer. It produces structured decisions (conflicts, merge plans, risk comparisons) but never commands, scripts, or execution instructions.

**Violations lead to**: Security risks, audit failures, bypassing review gates.

### Definition

**Prohibited**:
- Any field or value containing execution instructions
- Fields named: `execute`, `shell`, `subprocess`, `run`, `command_line`, `script`, `bash`, `python_code`
- String values containing: `subprocess.run`, `os.system`, `eval(`, `exec(`, `import subprocess`

**Allowed**:
- Governance outputs: conflicts, merge plans, risk comparisons, questions
- References to registry commands (by ID, not code)
- Evidence references (file paths, registry IDs, factpack refs)

### Enforcement

#### 1. Schema Layer

**All evaluator schemas** include:

```json
{
  "constraints": {
    "type": "object",
    "additionalProperties": false,
    "required": ["execution"],
    "properties": {
      "execution": {
        "const": "forbidden",
        "description": "RL-E1: Evaluator produces no executable payload"
      }
    }
  }
}
```

**Top-level schema**:
- `additionalProperties: false` — No unknown fields allowed
- No `execute`, `shell`, etc. in `properties` definition

**Files**:
- `intent_evaluation_result.schema.json`
- `intent_merge_plan.schema.json`
- `intent_set.schema.json`

#### 2. Runtime Layer

**Validator**: `scripts/validate_intent_evaluation.py`

```python
def validate_red_line_e1(data: dict) -> List[str]:
    """RL-E1: No execution payload."""
    errors = []
    
    # Check constraints.execution = "forbidden"
    if data.get("constraints", {}).get("execution") != "forbidden":
        errors.append("RL-E1: constraints.execution must be 'forbidden'")
    
    # Check for prohibited fields (top-level and nested)
    prohibited_fields = [
        "execute", "shell", "subprocess", "run", "command_line",
        "script", "bash", "python_code", "eval", "exec"
    ]
    
    def scan_dict(obj, path=""):
        for key, value in obj.items():
            if key in prohibited_fields:
                errors.append(f"RL-E1: Prohibited field '{key}' at {path}")
            if isinstance(value, dict):
                scan_dict(value, f"{path}.{key}")
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        scan_dict(item, f"{path}.{key}[{i}]")
    
    scan_dict(data)
    return errors
```

#### 3. Static Layer

**Gate D**: `scripts/gates/v093_gate_d_no_execution_symbols.sh`

```bash
#!/bin/bash
# v0.9.3 Gate D: No Execution Symbols

SCHEMA_DIR="agentos/schemas/evaluator"
EXAMPLES_DIR="examples/intents/evaluations"

echo "Scanning for execution symbols..."

PROHIBITED_PATTERNS=(
  "subprocess"
  "os.system"
  "eval("
  "exec("
  "import subprocess"
  "shell=True"
  "\.run\("
  "Popen"
)

for pattern in "${PROHIBITED_PATTERNS[@]}"; do
  matches=$(grep -r "$pattern" "$SCHEMA_DIR" "$EXAMPLES_DIR" || true)
  if [ -n "$matches" ]; then
    echo "❌ FAILED: Found prohibited pattern: $pattern"
    echo "$matches"
    exit 1
  fi
done

echo "✅ PASSED: No execution symbols found"
```

#### 4. Gate J (Lineage-specific check)

Gate J also verifies that merged intents don't smuggle execution payload via lineage metadata.

### Examples

#### ✅ Valid (Governance Only)

```json
{
  "id": "eval_result_safe_001",
  "type": "intent_evaluation_result",
  "evaluation": {
    "conflicts": [],
    "merge_plan": {
      "strategy": "merge_union",
      "operations": [
        {
          "operation": "union_commands",
          "source_intent_id": "intent_a",
          "evidence": "Commands are complementary"
        }
      ]
    }
  },
  "constraints": {
    "execution": "forbidden"
  }
}
```

#### ❌ Invalid (Execution Payload)

```json
{
  "id": "eval_result_bad_001",
  "evaluation": {
    "merge_plan": {
      "execute": "python merge_intents.py"  // PROHIBITED
    }
  },
  "constraints": {
    "execution": "forbidden"
  }
}
```

```json
{
  "id": "eval_result_bad_002",
  "evaluation": {
    "operations": [
      {
        "subprocess": {  // PROHIBITED FIELD
          "run": "git commit"
        }
      }
    ]
  }
}
```

---

## RL-E2: Merged Intent Must Have Complete Lineage

### Rationale

When the Evaluator merges or overrides intents, the resulting intent must be **fully traceable** to its sources. This ensures:
- Audit trail for governance
- Version history for rollback
- Attribution for compliance

**Violations lead to**: Lost provenance, untraceable decisions, compliance failures.

### Definition

**Required for `merge_union`**:
- `result_intent.lineage.derived_from`: Array with ≥ 1 source intent ID

**Required for `override_by_priority`**:
- `result_intent.lineage.derived_from`: Array with ≥ 1 source intent ID (typically the winning intent)
- `result_intent.lineage.supersedes`: Array with ≥ 1 superseded intent ID

**Required for both**:
- `merge_plan.lineage.derived_from`: Must match `source_intent_ids`
- `merge_plan.lineage.supersedes`: Must match if override strategy

### Enforcement

#### 1. Schema Layer

**intent_merge_plan.schema.json**:

```json
{
  "result_intent": {
    "properties": {
      "lineage": {
        "required": ["introduced_in", "derived_from", "supersedes"],
        "properties": {
          "derived_from": {
            "type": "array",
            "minItems": 1,
            "description": "RL-E2: Must include source intents"
          },
          "supersedes": {
            "type": "array",
            "description": "RL-E2: Must list superseded intents if override"
          }
        }
      }
    }
  },
  "allOf": [
    {
      "if": {
        "properties": {
          "strategy": {
            "const": "override_by_priority"
          }
        }
      },
      "then": {
        "properties": {
          "lineage": {
            "properties": {
              "supersedes": {
                "minItems": 1
              }
            }
          }
        }
      }
    }
  ]
}
```

#### 2. Runtime Layer

**Validator**: `scripts/validate_intent_evaluation.py`

```python
def validate_red_line_e2(merge_plan: dict) -> List[str]:
    """RL-E2: Merged intent must have lineage."""
    errors = []
    
    strategy = merge_plan.get("strategy")
    result_intent = merge_plan.get("result_intent", {})
    lineage = result_intent.get("lineage", {})
    
    # Check derived_from populated
    derived_from = lineage.get("derived_from", [])
    if not derived_from:
        errors.append("RL-E2: result_intent.lineage.derived_from is empty")
    
    # Check supersedes for override strategy
    if strategy == "override_by_priority":
        supersedes = lineage.get("supersedes", [])
        if not supersedes:
            errors.append("RL-E2: override strategy requires supersedes lineage")
    
    # Check merge_plan lineage matches source_intent_ids
    source_ids = set(merge_plan.get("source_intent_ids", []))
    plan_derived = set(merge_plan.get("lineage", {}).get("derived_from", []))
    if source_ids != plan_derived:
        errors.append("RL-E2: merge_plan.lineage.derived_from must match source_intent_ids")
    
    return errors
```

#### 3. Gate J

**Gate J**: `scripts/gates/v093_gate_j_lineage_enforcement.py`

```python
def check_lineage_enforcement():
    """Gate J: All merged intents have complete lineage."""
    merge_plans = glob("examples/intents/evaluations/merge_plan_*.json")
    
    for plan_path in merge_plans:
        with open(plan_path) as f:
            plan = json.load(f)
        
        strategy = plan["strategy"]
        result_intent = plan["result_intent"]
        lineage = result_intent["lineage"]
        
        # Check derived_from
        if not lineage.get("derived_from"):
            print(f"❌ {plan_path}: Missing derived_from")
            return False
        
        # Check supersedes for override
        if strategy == "override_by_priority":
            if not lineage.get("supersedes"):
                print(f"❌ {plan_path}: Missing supersedes for override")
                return False
    
    print("✅ All merged intents have complete lineage")
    return True
```

### Examples

#### ✅ Valid (merge_union)

```json
{
  "strategy": "merge_union",
  "source_intent_ids": ["intent_a", "intent_b"],
  "result_intent": {
    "id": "intent_merged_ab",
    "lineage": {
      "introduced_in": "0.9.3",
      "derived_from": ["intent_a", "intent_b"],  // REQUIRED
      "supersedes": []
    }
  },
  "lineage": {
    "derived_from": ["intent_a", "intent_b"],
    "supersedes": []
  }
}
```

#### ✅ Valid (override_by_priority)

```json
{
  "strategy": "override_by_priority",
  "source_intent_ids": ["intent_high", "intent_low"],
  "result_intent": {
    "id": "intent_high",
    "lineage": {
      "introduced_in": "0.9.3",
      "derived_from": ["intent_high"],
      "supersedes": ["intent_low"]  // REQUIRED for override
    }
  },
  "lineage": {
    "derived_from": ["intent_high"],
    "supersedes": ["intent_low"]
  }
}
```

#### ❌ Invalid (Missing derived_from)

```json
{
  "strategy": "merge_union",
  "result_intent": {
    "lineage": {
      "introduced_in": "0.9.3",
      "derived_from": [],  // INVALID: empty
      "supersedes": []
    }
  }
}
```

#### ❌ Invalid (Override without supersedes)

```json
{
  "strategy": "override_by_priority",
  "result_intent": {
    "lineage": {
      "introduced_in": "0.9.3",
      "derived_from": ["intent_high"],
      "supersedes": []  // INVALID: missing supersedes for override
    }
  }
}
```

---

## Inherited Red Lines (v0.9.1)

The Evaluator **inputs** (Execution Intents) must already satisfy v0.9.1 red lines:

| ID | Description | Status |
|----|-------------|--------|
| **I1** | No Execution Payload in Intent | ✅ Enforced by v0.9.1 |
| **I2** | full_auto ⇒ question_budget=0 | ✅ Enforced by v0.9.1 |
| **I3** | High Risk ≠ full_auto | ✅ Enforced by v0.9.1 |
| **I4** | All Commands Have Evidence | ✅ Enforced by v0.9.1 |
| **I5** | Registry Only, No Fabrication | ✅ Enforced by v0.9.1 |

**The Evaluator assumes inputs are valid.** If an intent violates I1-I5, the Evaluator should reject it during `IntentSetLoader.load()`.

---

## Red Line Verification Commands

```bash
# Validate a single evaluation result
uv run python scripts/validate_intent_evaluation.py --red-lines <eval_result.json>

# Run Gate D (static scan)
bash scripts/gates/v093_gate_d_no_execution_symbols.sh

# Run Gate J (lineage enforcement)
uv run python scripts/gates/v093_gate_j_lineage_enforcement.py

# Run all red line checks
for gate in scripts/gates/v093_gate_{d,j}*.{py,sh}; do
  echo "Running $gate..."
  if [[ "$gate" == *.sh ]]; then
    bash "$gate" || exit 1
  else
    uv run python "$gate" || exit 1
  fi
done
```

---

## Red Line Evolution Policy

**v0.9.3 Red Lines are FROZEN.**

Changes require:
1. Major version bump (v0.10.x)
2. Migration plan for existing evaluations
3. Backward compatibility layer
4. Full gate suite re-validation

**Allowed without version bump**:
- Clarifications in documentation
- Additional examples
- Improved error messages
- Gate implementation optimizations (if behavior unchanged)

---

**Version**: 0.9.3  
**Status**: 🔒 FROZEN  
**Last Updated**: 2026-01-25  
**Maintained by**: AgentOS Core Team
