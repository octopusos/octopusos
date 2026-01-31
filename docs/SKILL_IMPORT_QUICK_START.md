# Skill Import Quick Start Guide

Quick reference for importing skills into AgentOS.

---

## Installation

Ensure you have AgentOS installed:
```bash
pip install agentos
```

---

## Import a Skill

### From Local Directory

```bash
agentos skill import /path/to/skill
```

**Example**:
```bash
$ agentos skill import ~/skills/my-skill
📁 Importing from local path: ~/skills/my-skill
✅ Successfully imported skill: my.skill
   Status: imported_disabled
```

### From GitHub (PR-3)

```bash
agentos skill import github:owner/repo
agentos skill import github:owner/repo#branch
agentos skill import github:owner/repo#tag:subdir
```

---

## List Skills

```bash
# List all skills
agentos skill list

# Filter by status
agentos skill list --status enabled
agentos skill list --status disabled
agentos skill list --status imported_disabled
```

**Output**:
```
Status               Skill ID                       Version         Description
----------------------------------------------------------------------------------------------------
⊗ imported_disabled example.hello                  0.1.0           A simple test skill
✓ enabled           my.skill                       1.2.0           My awesome skill
○ disabled          old.skill                      0.5.0           Deprecated skill
```

**Status Icons**:
- ✓ = enabled
- ○ = disabled
- ⊗ = imported_disabled (new)

---

## View Skill Details

```bash
agentos skill info <skill_id>
```

**Example**:
```bash
$ agentos skill info example.hello
============================================================
Skill: example.hello
============================================================
Version:      0.1.0
Status:       imported_disabled
Repo Hash:    6a7329ba...
...
```

---

## Enable/Disable Skills (Requires Admin Token)

```bash
# Enable skill
export AGENTOS_ADMIN_TOKEN='your-token'
agentos skill enable <skill_id>

# Disable skill
agentos skill disable <skill_id>
```

---

## Skill Directory Structure

A valid skill must have this structure:

```
my-skill/
  skill.yaml          # Required: Manifest
  skill.py            # Required: Implementation
  README.md           # Optional: Documentation
  requirements.txt    # Optional: Dependencies
```

### Minimal skill.yaml

```yaml
skill_id: my.skill
name: My Skill
version: 1.0.0
author: your-name
description: What this skill does

entry:
  runtime: python
  module: skill.py
  exports:
    - command: mycommand
      handler: run

capabilities:
  class: pure  # or io, action

requires:
  phase: execution
  permissions: {}

limits:
  max_runtime_ms: 5000
  max_tokens: 800
```

---

## Common Errors

### Error: "No skill manifest found"

**Cause**: Missing `skill.yaml` in directory

**Fix**: Create `skill.yaml` in the skill directory

### Error: "Manifest validation failed"

**Cause**: Invalid or incomplete manifest

**Fix**: Check required fields:
- `skill_id`, `name`, `version`, `author`, `description`
- `entry`, `capabilities`, `requires`

### Error: "Skill path does not exist"

**Cause**: Invalid path

**Fix**: Use absolute path or verify directory exists

---

## FAQ

### Q: Will importing a skill execute its code?

**A**: No. Import only reads and validates the manifest. Code is NEVER executed during import.

### Q: What happens if I import the same skill twice?

**A**: The skill is updated. Status is preserved if it was enabled.

### Q: How do I update a skill?

**A**: Re-import from the updated directory. The skill will be updated in the registry.

### Q: Where are imported skills stored?

**A**: Registry: `~/.agentos/store/skill/db.sqlite`

### Q: Can I import from a ZIP file?

**A**: Not yet (planned for future release). Extract the ZIP first.

---

## Security Notes

### Import Safety

✅ Import is READ-ONLY:
- No Python code is executed
- No files are modified
- No network calls are made

### Default Status

All imported skills start with status `imported_disabled`:
- Cannot be used until explicitly enabled
- Requires admin token to enable
- Prevents accidental execution

---

## Next Steps

1. Import your skill: `agentos skill import /path`
2. Review details: `agentos skill info <skill_id>`
3. Enable it: `agentos skill enable <skill_id> --token <token>`
4. Use it in your agent workflows!

---

## Need Help?

- Documentation: `docs/PR-0201-2026-2-IMPLEMENTATION-REPORT.md`
- Tests: `tests/unit/skills/importer/test_local_importer.py`
- Examples: `tests/fixtures/skills/hello_skill/`

---

**Version**: v0.2.0 (PR-0201-2026-2)
**Last Updated**: 2026-02-01
