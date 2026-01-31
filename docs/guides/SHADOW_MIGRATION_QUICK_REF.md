# Shadow → Active Migration - Quick Reference

**Last Updated**: 2026-01-31

---

## Quick Start

### 1. Verify Prerequisites

```bash
agentos classifier migrate verify --shadow v2-shadow-a
```

### 2. Perform Migration

```bash
# With confirmation prompt
agentos classifier migrate to-active --shadow v2-shadow-a

# Skip confirmation (for automation)
agentos classifier migrate to-active --shadow v2-shadow-a --yes

# Dry run (preview only)
agentos classifier migrate to-active --shadow v2-shadow-a --dry-run
```

### 3. Rollback (if needed)

```bash
agentos classifier migrate rollback --reason "Performance regression"
```

---

## Prerequisites

Before migration, the following must be met:

| Prerequisite | Threshold | Check |
|--------------|-----------|-------|
| Sample Count | >= 100 | Sufficient data for confidence |
| Improvement Rate | >= 15% | Meaningful performance gain |
| Risk Level | LOW | Safe to deploy |
| Proposal Status | accepted | Human approved |

---

## Commands

### `verify`

Check if a shadow classifier meets migration prerequisites.

```bash
agentos classifier migrate verify --shadow <version-id>

# Example
agentos classifier migrate verify --shadow v2-shadow-a
```

**Output**: Prerequisite validation report with PASS/FAIL status.

---

### `to-active`

Migrate a shadow classifier to active status.

```bash
agentos classifier migrate to-active --shadow <version-id> [OPTIONS]

# Options:
#   --user TEXT            User performing migration (default: admin)
#   --skip-verification    Skip prerequisite checks (dangerous!)
#   --dry-run             Simulate migration without changes
#   --yes                 Skip confirmation prompt
```

**Examples**:

```bash
# Standard migration with confirmation
agentos classifier migrate to-active --shadow v2-shadow-a

# Dry run to preview changes
agentos classifier migrate to-active --shadow v2-shadow-a --dry-run

# Automated migration (no prompts)
agentos classifier migrate to-active --shadow v2-shadow-a --yes

# Specify user
agentos classifier migrate to-active --shadow v2-shadow-a --user alice
```

**What Happens**:
1. Creates new active version
2. Updates shadow registry config
3. Deactivates promoted shadow
4. Creates validation shadow from old active
5. Saves migration state for rollback

---

### `rollback`

Rollback the most recent migration.

```bash
agentos classifier migrate rollback [OPTIONS]

# Options:
#   --reason TEXT    Reason for rollback (default: "Manual rollback")
#   --user TEXT      User performing rollback (default: admin)
#   --yes           Skip confirmation prompt
```

**Example**:

```bash
# Standard rollback with confirmation
agentos classifier migrate rollback --reason "Performance regression"

# Automated rollback (no prompts)
agentos classifier migrate rollback --reason "Bug detected" --yes
```

**What Happens**:
1. Restores previous active version
2. Restores shadow registry config
3. Records rollback in audit history

---

## Migration Workflow

### Step-by-Step Process

```
1. Shadow Evaluation
   ├─ Shadow runs in parallel with active
   ├─ Decisions audited and compared
   └─ Metrics calculated (samples, improvement rate)

2. Proposal Generation (BrainOS)
   ├─ Analyzes shadow performance
   ├─ Creates ImprovementProposal
   └─ Assigns risk level

3. Human Review
   ├─ Review proposal in Review Queue
   ├─ Approve/reject/defer decision
   └─ Proposal status updated

4. Prerequisite Verification ← THIS TOOL
   ├─ Check sample count >= 100
   ├─ Check improvement >= 15%
   ├─ Check risk level = LOW
   └─ Check proposal = accepted

5. Migration Execution ← THIS TOOL
   ├─ Create new active version
   ├─ Update configurations
   ├─ Rotate roles (active ↔ shadow)
   └─ Create validation shadow

6. Monitoring (optional)
   └─ Validation shadow monitors new active

7. Rollback (if issues) ← THIS TOOL
   ├─ Restore previous active
   └─ Restore previous config
```

---

## Safety Features

### 1. Prerequisite Validation

Automatic validation before migration:
- Blocks migration if requirements not met
- Clear error messages with guidance
- `--skip-verification` flag to override (dangerous)

### 2. Dry Run Mode

Preview changes without applying them:
```bash
agentos classifier migrate to-active --shadow v2-shadow-a --dry-run
```

Output shows:
- Planned version changes
- Config updates
- Role rotations
- New shadow creation

### 3. Confirmation Prompts

Interactive confirmation before changes:
```
⚠ Confirm Migration
  Shadow version: v2-shadow-a
  Proposal: BP-017
  Improvement: +20.0%
  Samples: 150

Do you want to proceed with migration? [y/N]:
```

Skip with `--yes` flag for automation.

### 4. Rollback Support

One-command restoration:
- Saved migration state
- Config backup
- Version history
- Audit trail

---

## Configuration Updates

### Shadow Classifiers Config

File: `agentos/config/shadow_classifiers.yaml`

**Before Migration**:
```yaml
shadow_classifiers:
  active_versions:
    - v2-shadow-a  # Shadow being evaluated

  versions:
    v2-shadow-a:
      enabled: true
      priority: 1
      description: "Improved keyword detection"
      risk_level: "low"
```

**After Migration**:
```yaml
shadow_classifiers:
  active_versions:
    - v1-shadow-validation  # Validation shadow (was active)

  versions:
    v2-shadow-a:
      enabled: false  # Promoted, now inactive as shadow
      promoted_at: "2026-01-31T10:15:30Z"
      promoted_to: "v2.1"
      priority: 1
      description: "Improved keyword detection"
      risk_level: "low"

    v1-shadow-validation:  # New validation shadow
      enabled: true
      priority: 10
      description: "Validation shadow from previous active v1"
      risk_level: "low"
```

---

## Database Changes

### New Table: `classifier_migration_history`

Stores migration state for rollback:

```sql
CREATE TABLE classifier_migration_history (
    migration_id TEXT PRIMARY KEY,
    active_version TEXT NOT NULL,
    shadow_version TEXT NOT NULL,
    config_backup TEXT NOT NULL,
    timestamp TEXT NOT NULL
);
```

### Updated Tables

- `classifier_versions`: New version created with metadata
- `improvement_proposals`: Marked as implemented
- `version_rollback_history`: Rollback events recorded

---

## Integration with Other Tasks

| Task | Component | Usage in Migration |
|------|-----------|-------------------|
| #2 | Shadow Registry | Manage active shadows |
| #5 | Decision Comparator | Gather metrics |
| #7 | ImprovementProposal | Validation source |
| #9 | Review Queue | Proposal lookup |
| #10 | Version Manager | Create new version |

---

## Error Handling

### Common Errors

**"Prerequisites not met"**
```
Error: Migration prerequisites not met for v2-shadow-a.
Run 'agentos classifier migrate verify --shadow v2-shadow-a' for details.
```

**Solution**: Run verify command, fix failing prerequisites, retry.

---

**"No approved proposal found"**
```
Error: No accepted proposal found for v2-shadow-a.
A proposal is required for migration.
```

**Solution**: Review and approve proposal in Review Queue first.

---

**"No migration history found"**
```
Error: No migration history found. Nothing to rollback.
```

**Solution**: Only run rollback after a successful migration.

---

**"No active version found"**
```
Error: No active classifier version found
```

**Solution**: Ensure classifier version system is initialized (v1 should exist).

---

## Automation Example

### CI/CD Pipeline Integration

```bash
#!/bin/bash
# migrate_classifier.sh - Automated migration script

SHADOW_VERSION="v2-shadow-a"

# Step 1: Verify prerequisites
echo "Verifying prerequisites..."
if ! agentos classifier migrate verify --shadow "$SHADOW_VERSION"; then
    echo "Prerequisites not met. Aborting migration."
    exit 1
fi

# Step 2: Perform migration (skip confirmation)
echo "Performing migration..."
agentos classifier migrate to-active \
    --shadow "$SHADOW_VERSION" \
    --user "ci-bot" \
    --yes

if [ $? -eq 0 ]; then
    echo "Migration successful: $SHADOW_VERSION → active"

    # Optional: Run smoke tests
    echo "Running smoke tests..."
    ./run_smoke_tests.sh

    if [ $? -ne 0 ]; then
        echo "Smoke tests failed. Rolling back..."
        agentos classifier migrate rollback \
            --reason "Smoke tests failed" \
            --user "ci-bot" \
            --yes
        exit 1
    fi

    echo "Migration complete and validated"
else
    echo "Migration failed"
    exit 1
fi
```

---

## Troubleshooting

### Issue: Migration fails mid-operation

**Symptoms**: Error during migration, unclear state

**Solution**: Database transactions ensure atomicity. If migration fails:
1. No changes are applied (transaction rolled back)
2. Retry migration after fixing issue
3. Check logs for specific error

---

### Issue: Need to undo migration

**Symptoms**: New active version has issues

**Solution**: Use rollback command:
```bash
agentos classifier migrate rollback --reason "Performance regression"
```

This restores:
- Previous active version
- Previous shadow config
- Records rollback in history

---

### Issue: Want to migrate but prerequisites not met

**Symptoms**: Verify shows failures

**Solution**:
1. **If low samples**: Wait for more data collection
2. **If low improvement**: Shadow may not be better, reconsider
3. **If high risk**: Review proposal, additional validation needed
4. **If no proposal**: Generate and approve proposal first

**Dangerous override** (not recommended):
```bash
agentos classifier migrate to-active \
    --shadow v2-shadow-a \
    --skip-verification \
    --yes
```

---

## Best Practices

### 1. Always Verify First

```bash
agentos classifier migrate verify --shadow v2-shadow-a
```

Don't skip this step. It prevents unsafe migrations.

### 2. Use Dry Run

```bash
agentos classifier migrate to-active --shadow v2-shadow-a --dry-run
```

Preview changes before applying them.

### 3. Monitor After Migration

- Check validation shadow for regression
- Monitor active performance metrics
- Keep rollback option ready

### 4. Document Migrations

```bash
# Good
agentos classifier migrate to-active \
    --shadow v2-shadow-a \
    --user "alice" \
    --yes  # Documented in script

# With clear proposal notes in Review Queue
```

### 5. Test Rollback Process

Periodically test rollback in non-production:
```bash
# Test migration
agentos classifier migrate to-active --shadow test-shadow --yes

# Test rollback
agentos classifier migrate rollback --reason "Testing rollback" --yes
```

---

## CLI Help

```bash
# Main help
agentos classifier migrate --help

# Command-specific help
agentos classifier migrate verify --help
agentos classifier migrate to-active --help
agentos classifier migrate rollback --help
```

---

## File Locations

- **CLI Tool**: `agentos/cli/classifier_migrate.py`
- **Config Helpers**: `agentos/config/loader.py`
- **Shadow Config**: `agentos/config/shadow_classifiers.yaml`
- **Database**: `~/.agentos/registry.db` (or configured path)

---

## Related Documentation

- **Version Manager**: Task #10 documentation
- **Shadow Registry**: Task #2 documentation
- **ImprovementProposal**: Task #7 documentation
- **Review Queue**: Task #9 documentation
- **Decision Comparator**: Task #5 documentation

---

**Questions?** See full acceptance report: `SHADOW_MIGRATION_ACCEPTANCE_REPORT.md`
