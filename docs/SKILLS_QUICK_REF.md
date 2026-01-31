# Skills System Quick Reference

## Overview

The Skills system provides infrastructure for managing external capabilities (skills) in AgentOS. Skills are packaged units of functionality with defined permissions and resource limits.

## Architecture

```
┌─────────────────────────────────────────┐
│          Skills Management              │
├─────────────────────────────────────────┤
│  Manifest Parser  │  Registry DB        │
│  (manifest.py)    │  (registry.py)      │
├───────────────────┼─────────────────────┤
│  • YAML parsing   │  • SQLite storage   │
│  • Validation     │  • CRUD operations  │
│  • Normalization  │  • Status tracking  │
└─────────────────────────────────────────┘
         │                    │
         └────────┬───────────┘
                  │
         ~/.agentos/store/skill/db.sqlite
```

## Database Location

```
~/.agentos/store/skill/db.sqlite
```

## Skill Manifest Schema (skill.yaml)

```yaml
skill_id: example.skill          # Unique identifier (lowercase, dots/hyphens)
name: Example Skill              # Display name
version: 1.0.0                   # Semver (major.minor.patch)
author: author-name              # Author identifier
description: What this skill does

entry:
  runtime: python                # Runtime: python | nodejs | ...
  module: main.py                # Entry module file
  exports:
    - command: example.run       # Command identifier
      handler: run               # Handler function name

capabilities:
  class: io                      # pure | io | action
  tags: [example, demo]          # Classification tags

requires:
  phase: execution               # When skill can run
  permissions:
    net:
      allow_domains:             # Allowed domains (FQDNs only)
        - api.example.com
    fs:
      read: true                 # Filesystem read
      write: false               # Filesystem write
    actions:
      write_state: false         # State-changing operations

limits:
  max_runtime_ms: 5000           # Max execution time (ms)
  max_tokens: 800                # Max token usage

integrity:                       # Optional
  files:
    - main.py
    - README.md
```

## Capability Classes

| Class  | Description                     | Requires Permissions |
|--------|---------------------------------|----------------------|
| pure   | No I/O, deterministic           | None                 |
| io     | Read-only external resources    | net or fs (read)     |
| action | State-changing operations       | actions.write_state  |

## Skill Status

| Status             | Description                        |
|--------------------|------------------------------------|
| imported_disabled  | Imported but not enabled (default) |
| enabled            | Active and invokable               |
| disabled           | Temporarily disabled               |

## Trust Levels

| Level    | Description                    |
|----------|--------------------------------|
| local    | Locally imported (default)     |
| reviewed | Manually reviewed              |
| verified | Cryptographically verified     |

## Python API

### Import and Use

```python
from agentos.skills import (
    load_manifest,
    validate_manifest,
    normalize_manifest,
    SkillRegistry,
)
```

### Load and Validate Manifest

```python
# From file
manifest = load_manifest("skill.yaml")

# From bytes
yaml_bytes = b"skill_id: test.skill\n..."
manifest = load_manifest(yaml_bytes)

# Validate
is_valid, errors = validate_manifest(manifest)
if not is_valid:
    for error in errors:
        print(f"Error: {error}")
```

### Registry Operations

```python
# Initialize registry
registry = SkillRegistry()  # Uses ~/.agentos/store/skill/db.sqlite

# Insert/update skill
normalized = normalize_manifest(manifest)
registry.upsert_skill(
    skill_id=manifest.skill_id,
    manifest=normalized,
    source_type="local",        # or "github"
    source_ref="/path/to/skill",
    repo_hash="abc123",         # Content hash for deduplication
)

# Get skill
skill = registry.get_skill("my.skill")
print(skill["status"])          # imported_disabled
print(skill["manifest_json"])   # Parsed manifest dict

# List skills
all_skills = registry.list_skills()
enabled_skills = registry.list_skills(status="enabled")

# Update status
registry.set_status("my.skill", "enabled")

# Record error
registry.set_error("my.skill", "Import failed: file not found")

# Delete skill
registry.delete_skill("my.skill")
```

## Validation Rules

### Structural
- Required: skill_id, name, version, author, description
- Entry: runtime, module, at least one export
- Capabilities: class field required
- Requires: phase field required

### Type
- version: Semver format (e.g., "1.0.0")
- capabilities.class: "pure" | "io" | "action"
- allow_domains: Valid FQDNs only (no wildcards)
- limits: Positive integers

### Semantic
1. **Action requires permission**: If `capabilities.class=action`, must have `permissions.actions.write_state=true`
2. **Net requires domains**: If `permissions.net` declared, `allow_domains` cannot be empty
3. **Integrity requires files**: If `integrity` declared, `files` cannot be empty

## Common Patterns

### Import Local Skill

```python
# Load and validate
manifest = load_manifest("/path/to/skill/skill.yaml")
is_valid, errors = validate_manifest(manifest)

if not is_valid:
    raise ValueError(f"Invalid manifest: {errors}")

# Store in registry
registry = SkillRegistry()
normalized = normalize_manifest(manifest)
registry.upsert_skill(
    skill_id=manifest.skill_id,
    manifest=normalized,
    source_type="local",
    source_ref="/path/to/skill",
    repo_hash=compute_hash("/path/to/skill"),
)
```

### Enable Skill

```python
registry = SkillRegistry()

# Check if skill exists
skill = registry.get_skill("my.skill")
if not skill:
    raise ValueError("Skill not found")

# Enable
registry.set_status("my.skill", "enabled")
```

### Check if Skill Can Run

```python
registry = SkillRegistry()
skill = registry.get_skill("my.skill")

# Check status
if skill["status"] != "enabled":
    raise RuntimeError("Skill is not enabled")

# Check permissions
manifest = skill["manifest_json"]
permissions = manifest["requires"]["permissions"]

# Example: Check net permission
if "net" in permissions:
    allowed = permissions["net"]["allow_domains"]
    if target_domain not in allowed:
        raise PermissionError(f"Domain {target_domain} not allowed")
```

### List Skills by Status

```python
registry = SkillRegistry()

# All enabled skills
enabled = registry.list_skills(status="enabled")
for skill in enabled:
    print(f"{skill['skill_id']}: {skill['name']}")

# All imported but not enabled
imported = registry.list_skills(status="imported_disabled")
```

## Error Handling

```python
from agentos.skills import load_manifest, validate_manifest

try:
    manifest = load_manifest("skill.yaml")
except FileNotFoundError:
    print("Manifest file not found")
except ValueError as e:
    print(f"Invalid YAML: {e}")

try:
    is_valid, errors = validate_manifest(manifest)
    if not is_valid:
        for error in errors:
            print(f"Validation error: {error}")
except Exception as e:
    print(f"Validation failed: {e}")
```

## Database Schema

```sql
-- Skills table
CREATE TABLE skills (
    skill_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    status TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    manifest_json TEXT NOT NULL,
    repo_hash TEXT NOT NULL,
    trust_level TEXT DEFAULT 'local',
    created_at INTEGER NOT NULL,    -- epoch ms
    updated_at INTEGER NOT NULL,    -- epoch ms
    last_error TEXT
);

-- Indexes
CREATE INDEX idx_skills_status ON skills(status);
CREATE INDEX idx_skills_source ON skills(source_type);
```

## CLI Integration (Coming in PR-0201-2026-2)

```bash
# Import local skill
agentos skill import /path/to/skill

# Import from GitHub
agentos skill import github:user/repo@main:skills/skill-name

# List skills
agentos skill list
agentos skill list --status enabled

# Enable/disable
agentos skill enable my.skill
agentos skill disable my.skill

# Delete
agentos skill delete my.skill
```

## WebUI Integration (Coming in PR-0201-2026-6)

```
/skills                  - List all skills
/skills/:skill_id        - Skill details
/skills/:skill_id/enable - Enable skill (POST)
```

## Testing

```bash
# Run all skills tests
pytest tests/unit/skills/

# Run specific test file
pytest tests/unit/skills/test_manifest.py
pytest tests/unit/skills/test_registry.py

# Run with coverage
pytest tests/unit/skills/ --cov=agentos.skills
```

## Dependencies

- **PyYAML**: Manifest parsing
- **sqlite3**: Standard library (no install)
- **agentos.core.storage.paths**: Component database path

## Related Documentation

- [Implementation Report](../PR_0201_2026_1_IMPLEMENTATION_REPORT.md)
- [ADR-011: Time Contract](./adr/ADR-011-time-timestamp-contract.md)
- [Storage Paths](../agentos/core/storage/paths.py)

## Support

For issues or questions:
1. Check test files for usage examples
2. Review implementation report for architecture details
3. See manifest.py and registry.py docstrings

---

**Last Updated:** 2026-02-01
**Status:** Production-ready (PR-0201-2026-1)
