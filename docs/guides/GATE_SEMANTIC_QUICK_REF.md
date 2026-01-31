# Gate: No Semantic in Search - Quick Reference

## TL;DR

**Gate prevents semantic analysis fields in search/fetch phases. Only metadata allowed.**

## One-Liner

```bash
python3 scripts/gates/gate_no_semantic_in_search.py
```

---

## Forbidden Fields

| Field | Why Forbidden | Use Instead |
|-------|---------------|-------------|
| `summary` | Semantic interpretation | `snippet` (raw text) |
| `why_it_matters` | Importance judgment | Priority enum |
| `analysis` | Content interpretation | (Move to brief) |
| `impact` | Impact assessment | (Move to brief) |
| `assessment` | Quality judgment | (Move to brief) |
| `importance` | Importance rating | (Move to brief) |
| `implication` | Consequence analysis | (Move to brief) |

---

## Phase Rules

```
┌─────────────┬─────────────────────┬──────────────────┐
│ Phase       │ Allowed             │ Forbidden        │
├─────────────┼─────────────────────┼──────────────────┤
│ SEARCH      │ title, url, snippet │ summary, etc.    │
│ FETCH       │ text, links, images │ summary, etc.    │
│ BRIEF       │ ALL (semantic OK)   │ None             │
└─────────────┴─────────────────────┴──────────────────┘
```

---

## Quick Examples

### ✅ CORRECT

```python
# Search result
{
    "title": "Policy Doc",
    "url": "https://example.gov/policy.pdf",
    "snippet": "Updated 2025...",  # Raw text
    "priority_score": 85,
    "reasons": [PriorityReason.GOV_DOMAIN]  # Enum
}
```

### ❌ WRONG

```python
# Search result
{
    "title": "Policy Doc",
    "summary": "Important changes...",  # FORBIDDEN
    "why_it_matters": "Critical...",    # FORBIDDEN
}
```

---

## Files Checked

1. `agentos/core/communication/connectors/web_search.py`
2. `agentos/core/communication/priority/priority_scoring.py`
3. `agentos/core/chat/comm_commands.py` (search/fetch only)

---

## Brief Phase Exempt

These functions CAN use semantic fields:
- `_format_brief()`
- `_generate_importance()`
- `_fetch_and_verify()` (and nested)
- Any function with "brief" in name

---

## Common Issues

### Issue: "Gate fails on my code"
**Solution**: Check if you're using forbidden fields outside brief phase

### Issue: "False positive in brief function"
**Solution**: Function may not be whitelisted - check patterns

### Issue: "Need to add semantic field"
**Solution**: Move it to brief phase or use metadata-based scoring

---

## Priority Reason Rules

✅ **Allowed**: `reasons=[PriorityReason.GOV_DOMAIN]`
❌ **Forbidden**: `reason="High authority source"`

---

## Testing

```bash
# Run gate
python3 scripts/gates/gate_no_semantic_in_search.py

# Run tests
pytest tests/unit/gates/test_gate_no_semantic_in_search.py -v

# Run all gates
bash scripts/gates/run_all_gates.sh
```

---

## Key Principle

**Search results are CANDIDATE SOURCES, not truth.**

---

## Documentation

- Full README: `scripts/gates/README_SEMANTIC_GATE.md`
- Completion Report: `GATE_SEMANTIC_SEARCH_COMPLETION.md`
- Tests: `tests/unit/gates/test_gate_no_semantic_in_search.py`

---

## Exit Codes

- **0**: Pass - No violations
- **1**: Fail - Violations found

---

## Quick Fix

Replace this:
```python
"summary": "Text here"  # FORBIDDEN
```

With this:
```python
"snippet": raw_snippet  # ALLOWED
```

---

**Version**: 1.0
**Last Updated**: 2026-01-31
