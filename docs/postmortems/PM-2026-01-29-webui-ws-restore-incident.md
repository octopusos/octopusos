# Postmortem: WebUI WebSocket Manager Restoration Incident

**Date**: 2026-01-29
**Severity**: P1 (Critical User-Facing Feature Loss)
**Status**: Resolved
**Author**: Claude Sonnet 4.5 + Human Operator

---

## Executive Summary

On 2026-01-29 at ~12:15 AEDT, a destructive `git reset --hard origin/master` operation was executed on the master branch, resulting in the loss of previously implemented WebSocket Manager code in `agentos/webui/static/js/main.js`. The incident was caused by a combination of working directly on the master branch, lack of pre-operation backups, and inadequate safety checks. The code was successfully restored on a feature branch (`fix/ws-core-recovery-0129`) with enhanced safety protocols.

**Impact**:
- WebSocket Manager (~230 lines) was lost from `main.js`
- Features lost: reconnection logic, heartbeat mechanism, Safari bfcache handling, lifecycle hooks
- User impact: Safari users would experience zombie connections; Windows users would experience silent disconnections
- Recovery time: ~2 hours (from detection to full restoration + documentation)

**Root Cause**: Destructive git operation on master branch without backup or branch isolation.

---

## Timeline (AEDT)

| Time     | Event |
|----------|-------|
| 12:15:05 | User creates branch `fix/windows-compatibility` from master |
| 12:15:27 | User switches back to master |
| 12:15:31 | **INCIDENT**: `git reset --hard origin/master` executed on master branch |
| 12:15:31 | WebSocket Manager code lost from `main.js` |
| ~13:48   | User notices issue (main.js has 5235 lines but no WS Manager) |
| 14:11    | Recovery initiated: created `fix/ws-core-recovery-0129` branch |
| 14:11    | Safety backups created in `/tmp/*.0129` |
| 14:11-14:30 | Code restoration: added WS Manager + lifecycle hooks + log buffer |
| 14:30    | Syntax validation passed |
| 14:35    | Committed and pushed to feature branch |
| 14:45    | Postmortem written |

**Detection Delay**: ~1.5 hours (from incident to detection)
**Recovery Time**: ~20 minutes (from detection to code restoration)
**Total Impact Duration**: ~2 hours

---

## Root Cause Analysis

### Direct Cause
Execution of `git reset --hard origin/master` on the master branch without:
1. Checking working directory status
2. Creating a safety backup
3. Working on a feature branch
4. Verifying the reset target contained the expected code

### Contributing Factors

1. **Working on Master Branch**
   - Critical WebSocket changes were being made directly on master
   - No branch isolation for experimental or risky operations
   - Violated standard Git workflow best practices

2. **Lack of Pre-Operation Backups**
   - No safety backup created before destructive git operation
   - No automated backup mechanism for critical files
   - No pre-commit hooks to warn about destructive operations

3. **Tool Chain Misleading**
   - Git command appeared "safe" (just syncing with origin)
   - No warning prompt for destructive operations
   - User unfamiliar with `--hard` flag implications

4. **Missing Safety Guards**
   - No git alias for "safe reset" operations
   - No mandatory branch policy for feature work
   - No CI/CD checks to prevent force operations on master

---

## Why Did This Happen?

1. **"Quick Fix" Mentality**
   - User was trying to "quickly" fix Windows compatibility issues
   - Prioritized speed over safety
   - Skipped branch creation step

2. **Inadequate Training**
   - Insufficient understanding of git reset --hard implications
   - Lack of awareness of branch-based development workflow
   - No knowledge of git reflog recovery techniques

3. **Process Gaps**
   - No documented procedure for "safe git operations"
   - No code review for direct master commits
   - No automated testing to catch missing features

---

## Prohibited Operations Checklist

To prevent recurrence, the following operations are **PROHIBITED** without explicit safety measures:

### Never Do On Master Branch

- [ ] `git reset --hard` (use feature branch)
- [ ] `git checkout -- <file>` (use `git restore --source`)
- [ ] `git restore <file>` without backup
- [ ] `git clean -f` without dry-run
- [ ] `git branch -D` for feature branches with unmerged work
- [ ] `git push --force` (except with `--force-with-lease` after review)

### Always Required Before Destructive Operations

- [ ] Create feature branch: `git checkout -b fix/feature-name`
- [ ] Create safety backup: `cp file.ext /tmp/file.ext.backup`
- [ ] Verify working directory: `git status`
- [ ] Check diff before reset: `git diff HEAD origin/master`
- [ ] Push branch to remote: `git push -u origin branch-name`

### When Recovery Needed

- [ ] Check reflog first: `git reflog -n 30`
- [ ] Create rescue branch: `git checkout -b rescue/incident-date`
- [ ] Document incident before recovery

---

## Preventive Measures

### Immediate Actions (Completed)

1. ✅ Created `safe-restore.sh` script (see Appendix A)
2. ✅ Established branch policy: all feature work on feature branches
3. ✅ Added backup protocol to recovery runbook
4. ✅ Documented prohibited operations checklist

### Short-Term Actions (Next Sprint)

1. Add git aliases for safe operations:
   ```bash
   git config alias.safe-reset '!f() { git stash && git reset "$@"; }; f'
   git config alias.safe-restore '!f() { cp "$1" "$1.backup" && git restore "$1"; }; f'
   ```

2. Add pre-commit hook to warn on master:
   ```bash
   #!/bin/bash
   branch=$(git symbolic-ref --short HEAD)
   if [[ "$branch" == "master" ]]; then
     echo "WARNING: Committing to master branch!"
     read -p "Are you sure? (y/N): " confirm
     [[ "$confirm" != "y" ]] && exit 1
   fi
   ```

3. Add CI check to prevent force-push to master

### Long-Term Actions (Next Quarter)

1. Implement automated daily backups of critical frontend files
2. Add branch protection rules on GitHub:
   - Require pull request reviews
   - Require status checks to pass
   - Prevent force-push on master
3. Create Git workflow training materials
4. Add monitoring for "dangerous git operations"

---

## Impact Assessment

### Files Affected

- `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/static/js/main.js`
  - Before: 5235 lines (with WS Manager)
  - After reset: 5235 lines (without WS Manager)
  - After recovery: 5519 lines (restored + enhanced)

### Code Lost (Then Restored)

- **WebSocket Manager** (~230 lines)
  - Reconnection logic with exponential backoff
  - Heartbeat mechanism (30s ping, 60s pong timeout)
  - Safari bfcache handling
  - Visibility/focus lifecycle hooks

- **Log Ring Buffer** (~55 lines)
  - Diagnostics capture for [WS] logs
  - 200-entry circular buffer

- **Helper Functions**
  - `wsDebug()` - debug connection state
  - `wsReconnect()` - manual reconnect trigger
  - `wsGetLogs(n)` - retrieve diagnostics

### Other Impacts

- ✅ No other agent changes lost (verified via git diff)
- ✅ Delivery files intact (index.html, ws-acceptance-test.js, docs)
- ✅ No production deployment affected (feature not yet merged)

---

## Lessons Learned

### What Went Well

1. **Fast Detection**: Issue noticed within 1.5 hours
2. **Clear Recovery Path**: Feature branch strategy allowed clean recovery
3. **Good Documentation**: Had design docs to reference during re-implementation
4. **No Production Impact**: Changes were on development branch

### What Could Be Improved

1. **Branch Discipline**: Should never work directly on master
2. **Safety Checks**: Need automated warnings for destructive operations
3. **Backup Habits**: Should create backups before any git reset
4. **Testing**: Should run acceptance tests before and after git operations

### Action Items

1. **Immediate**: All team members review prohibited operations checklist
2. **This Sprint**: Implement git aliases and pre-commit hooks
3. **Next Sprint**: Add branch protection rules on GitHub
4. **Ongoing**: Regular training on Git best practices

---

## Appendix A: Safe Restore Script

Create `/usr/local/bin/safe-restore.sh`:

```bash
#!/bin/bash
# safe-restore.sh - Safely restore file from git with backup

set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: safe-restore.sh <file>"
  exit 1
fi

FILE="$1"
BACKUP_DIR="/tmp/git-backups"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Check if file exists
if [ -f "$FILE" ]; then
  # Create backup
  BACKUP_PATH="$BACKUP_DIR/$(basename "$FILE").$TIMESTAMP.backup"
  cp -v "$FILE" "$BACKUP_PATH"
  echo "✅ Backup created: $BACKUP_PATH"
else
  echo "⚠️  File not found: $FILE"
fi

# Perform restore
echo "Restoring $FILE from git..."
git restore "$FILE"

echo "✅ Restore complete. Backup available at: $BACKUP_PATH"
```

Make executable:
```bash
chmod +x /usr/local/bin/safe-restore.sh
```

Usage:
```bash
safe-restore.sh agentos/webui/static/js/main.js
```

---

## Appendix B: Git Aliases for Safety

Add to `~/.gitconfig`:

```ini
[alias]
  # Safe reset: stash changes before reset
  safe-reset = "!f() { \
    echo 'Creating safety stash...'; \
    git stash push -m 'Safety stash before reset'; \
    git reset \"$@\"; \
    echo 'Reset complete. Restore with: git stash pop'; \
  }; f"

  # Safe restore: backup before restore
  safe-restore = "!f() { \
    for file in \"$@\"; do \
      if [ -f \"$file\" ]; then \
        cp \"$file\" \"$file.backup-$(date +%s)\"; \
        echo \"Backed up: $file\"; \
      fi; \
    done; \
    git restore \"$@\"; \
  }; f"

  # Safe checkout: warn before checkout
  safe-checkout = "!f() { \
    git status --short; \
    read -p 'Checkout $1? Uncommitted changes will be lost! (y/N): ' confirm; \
    [[ \"$confirm\" == \"y\" ]] && git checkout \"$@\" || echo 'Cancelled'; \
  }; f"
```

---

## Appendix C: Verification Checklist

After recovery, verify:

- [ ] Syntax check passes: `node -c main.js`
- [ ] Key functions exist: `grep -c "const WS = {" main.js`
- [ ] Lifecycle hooks present: `grep -c "setupWebSocketLifecycle" main.js`
- [ ] Line count restored: `wc -l main.js` (should be ~5519)
- [ ] Feature branch pushed: `git branch -r | grep fix/ws-core-recovery`
- [ ] Commit message includes co-author attribution
- [ ] Postmortem documented

---

## Sign-off

**Incident Commander**: Claude Sonnet 4.5
**Human Operator**: pangge
**Reviewed By**: (Pending)
**Date**: 2026-01-29

**Incident Status**: ✅ Resolved
**Postmortem Status**: ✅ Complete
**Follow-up Actions**: 🔄 In Progress
