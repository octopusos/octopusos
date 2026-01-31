# Multi-Repository Troubleshooting Guide

**Common Issues and Solutions**

Quick reference for diagnosing and fixing multi-repository project issues.

---

## Table of Contents

- [Import Issues](#import-issues)
- [Authentication Issues](#authentication-issues)
- [Workspace Issues](#workspace-issues)
- [Task Execution Issues](#task-execution-issues)
- [Performance Issues](#performance-issues)
- [Dependency Issues](#dependency-issues)

---

## Import Issues

### Issue: "Auth profile not found"

**Error**:
```
❌ Repo 'backend' references non-existent auth profile 'github-ssh'.
   Run 'agentos auth add' to create it.
```

**Cause**: Referenced auth profile doesn't exist.

**Solution**:
```bash
# Create SSH key profile
agentos auth add --name github-ssh --type ssh_key --key-path ~/.ssh/id_rsa

# Or create PAT profile
agentos auth add --name github-pat --type pat --token ghp_abc123...

# Retry import
agentos project import --from my-app.yaml
```

---

### Issue: "Path conflict detected"

**Error**:
```
❌ Workspace path conflicts detected:
   • repos 'backend' and 'api' both use path './be'
```

**Cause**: Multiple repos using the same workspace path.

**Solution**: Update config with unique paths:
```yaml
repos:
  - name: backend
    path: ./backend  # Changed

  - name: api
    path: ./api      # Changed
```

---

### Issue: "Dirty repository"

**Error**:
```
❌ Repository has uncommitted changes. Commit or stash before import.
```

**Cause**: Existing repo at workspace path has uncommitted changes.

**Solutions**:

1. **Commit changes**:
   ```bash
   cd ./backend
   git add .
   git commit -m "Save work before import"
   ```

2. **Use --force** (DESTRUCTIVE):
   ```bash
   agentos project import --from my-app.yaml --force
   ```

3. **Clean workspace**:
   ```bash
   agentos project workspace clean my-app --dry-run
   ```

---

### Issue: "Project already exists"

**Error**:
```
❌ Project 'my-app' already exists
```

**Solutions**:

1. **Add repos to existing project**:
   ```bash
   agentos project repos add my-app --name new-repo ...
   ```

2. **Use different project name**:
   ```yaml
   name: my-app-v2
   ```

3. **Remove existing project** (CAUTION):
   ```bash
   # Backup first!
   cp ~/.agentos/db.sqlite ~/.agentos/db.sqlite.backup

   # Remove project
   sqlite3 ~/.agentos/db.sqlite \
     "DELETE FROM projects WHERE id='my-app';"
   ```

---

## Authentication Issues

### Issue: "Permission denied (publickey)"

**Error**:
```
❌ backend: Read access denied
   Permission denied (publickey).
```

**Cause**: SSH key not configured or not authorized.

**Solutions**:

1. **Test SSH connection**:
   ```bash
   ssh -T git@github.com
   # Should see: "Hi username! You've successfully authenticated..."
   ```

2. **Check SSH key**:
   ```bash
   ssh-add -l  # List loaded keys
   ssh-add ~/.ssh/id_rsa  # Add key if missing
   ```

3. **Update auth profile**:
   ```bash
   agentos auth add --name github-ssh \
     --type ssh_key \
     --key-path ~/.ssh/correct_key
   ```

4. **Verify key on GitHub**:
   - Go to GitHub Settings → SSH Keys
   - Check if your public key is added

---

### Issue: "Token expired"

**Error**:
```
❌ frontend: Authentication failed
   Token has expired
```

**Cause**: PAT (Personal Access Token) has expired.

**Solution**:
```bash
# Generate new token on GitHub/GitLab
# Then update auth profile
agentos auth add --name github-pat \
  --type pat \
  --token ghp_NEW_TOKEN_HERE
```

---

### Issue: "Insufficient permissions"

**Error**:
```
⚠️ backend: Read-only access (write requested but not available)
```

**Cause**: Auth profile has read-only access but repo is marked writable.

**Solutions**:

1. **Grant write access** (GitHub):
   - Go to repo Settings → Collaborators
   - Add user with Write permission

2. **Use deploy key with write access**:
   ```bash
   # Generate new key with write permission
   ssh-keygen -t ed25519 -C "deploy-key-write"
   
   # Add to GitHub as deploy key (check "Allow write access")
   ```

3. **Mark repo as read-only**:
   ```bash
   agentos project repos update my-app backend --read-only
   ```

---

## Workspace Issues

### Issue: "Workspace path does not exist"

**Error**:
```
⚠️ Repository path does not exist: /workspace/projects/my-app/be
```

**Cause**: Workspace directories not created yet.

**Solutions**:

1. **Clone repositories**:
   ```bash
   # Manual clone
   cd /workspace/projects/my-app
   git clone git@github.com:org/backend be
   ```

2. **Use workspace init** (if implemented):
   ```bash
   agentos project workspace init my-app
   ```

---

### Issue: "Path outside workspace"

**Error**:
```
❌ Security violation: Attempted to access path outside workspace
   Path: /etc/passwd
```

**Cause**: Task trying to access files outside allowed workspace.

**Solution**: This is a security feature. Review task code and ensure it only accesses project files.

---

### Issue: "Nested repository conflict"

**Error**:
```
❌ Nested repository detected: ./backend contains ./backend/frontend
```

**Cause**: One repo's workspace is inside another repo's workspace.

**Solution**: Use sibling paths:
```yaml
repos:
  - name: backend
    path: ./backend

  - name: frontend
    path: ./frontend  # Sibling, not nested
```

---

## Task Execution Issues

### Issue: "Write to read-only repo blocked"

**Error**:
```
❌ Write operation blocked: Repository 'docs' is read-only
```

**Cause**: Task attempting to write to read-only repo.

**Solutions**:

1. **Check repo scope**:
   ```bash
   agentos project repos list my-app
   # Verify which repos are writable
   ```

2. **Update repo to writable**:
   ```bash
   agentos project repos update my-app docs --writable
   ```

3. **Fix task scope** (if intentional read-only):
   - Update task to only read from docs repo

---

### Issue: "Path filter violation"

**Error**:
```
❌ Path filter violation: File 'config/secrets.yaml' outside allowed paths
   Allowed: ["src/**", "tests/**"]
```

**Cause**: Task trying to modify files outside path filters.

**Solutions**:

1. **Check current filters**:
   ```bash
   sqlite3 ~/.agentos/db.sqlite \
     "SELECT path_filters FROM task_repo_scope WHERE task_id='...'"
   ```

2. **Update path filters** (if legitimate need):
   ```bash
   # Update task repo scope to include config/
   # (requires manual database update or task recreation)
   ```

3. **Move files to allowed paths**:
   ```bash
   git mv config/secrets.yaml src/config/secrets.yaml
   ```

---

### Issue: "Dependency cycle detected"

**Error**:
```
❌ Circular dependency detected: Task A → Task B → Task C → Task A
```

**Cause**: Tasks have circular dependencies.

**Solution**:
```bash
# Remove problematic dependency
sqlite3 ~/.agentos/db.sqlite \
  "DELETE FROM task_dependency WHERE task_id='task_A' AND depends_on_task_id='task_C'"

# Verify dependency graph
agentos task deps task_A --tree
```

---

## Performance Issues

### Issue: "Import takes too long"

**Symptom**: `agentos project import` hangs or takes minutes.

**Causes & Solutions**:

1. **Large repositories**:
   ```bash
   # Use shallow clone (if supported)
   git clone --depth 1 git@github.com:org/large-repo
   ```

2. **Network issues**:
   ```bash
   # Skip URL validation
   agentos project import --from my-app.yaml --skip-validation
   
   # Validate later
   agentos project validate my-app --check-urls
   ```

3. **Too many repos**:
   - Consider splitting into multiple projects
   - Recommended: 3-5 repos per project

---

### Issue: "Slow repo scope queries"

**Symptom**: `agentos project trace` is slow.

**Solutions**:

1. **Check database indexes**:
   ```bash
   sqlite3 ~/.agentos/db.sqlite "PRAGMA index_list('task_repo_scope');"
   ```

2. **Vacuum database**:
   ```bash
   sqlite3 ~/.agentos/db.sqlite "VACUUM;"
   ```

3. **Use pagination**:
   ```bash
   agentos project trace my-app --limit 50 --offset 0
   ```

---

### Issue: "Git operations timeout"

**Error**:
```
❌ Git command timed out after 30 seconds
```

**Solutions**:

1. **Increase timeout** (if supported):
   ```bash
   export AGENTOS_GIT_TIMEOUT=60
   ```

2. **Check network**:
   ```bash
   git ls-remote git@github.com:org/backend
   ```

3. **Use local clones**:
   ```bash
   # Clone manually first
   git clone --local /path/to/existing/repo ./backend
   ```

---

## Dependency Issues

### Issue: "Dependency not found"

**Error**:
```
❌ Dependency task not found: task_abc123
```

**Cause**: Referenced task doesn't exist or was deleted.

**Solution**:
```bash
# Remove broken dependency
sqlite3 ~/.agentos/db.sqlite \
  "DELETE FROM task_dependency WHERE depends_on_task_id='task_abc123'"
```

---

### Issue: "Circular import detected"

**Error**:
```
❌ Frontend imports backend, but backend imports frontend (cycle)
```

**Cause**: Circular dependency between repositories.

**Solutions**:

1. **Refactor code**: Extract shared code to a third repo
2. **Use interfaces**: Define clear API boundaries
3. **Accept cycle**: Some cycles are legitimate (mark as "weak" dependency)

---

## Diagnostic Commands

### Health Check

```bash
# Full project validation
agentos project validate my-app --all

# Check workspace
agentos project workspace check my-app

# List all repos
agentos project repos list my-app --verbose

# Trace activity
agentos project trace my-app
```

### Database Inspection

```bash
# Check project repos
sqlite3 ~/.agentos/db.sqlite \
  "SELECT * FROM project_repos WHERE project_id='my-app';"

# Check task repo scopes
sqlite3 ~/.agentos/db.sqlite \
  "SELECT * FROM task_repo_scope WHERE task_id='...';"

# Check dependencies
sqlite3 ~/.agentos/db.sqlite \
  "SELECT * FROM task_dependency WHERE task_id='...';"
```

### Logs

```bash
# Check logs (if logging configured)
tail -f ~/.agentos/logs/agentos.log

# Enable debug logging
export AGENTOS_LOG_LEVEL=DEBUG
agentos project import --from my-app.yaml
```

---

## Emergency Recovery

### Full Reset (NUCLEAR OPTION)

```bash
# 1. Backup
cp ~/.agentos/db.sqlite ~/.agentos/db.sqlite.backup

# 2. Remove all multi-repo data
sqlite3 ~/.agentos/db.sqlite << SQL
DELETE FROM project_repos;
DELETE FROM task_repo_scope;
DELETE FROM task_dependency;
DELETE FROM task_artifact_ref;
SQL

# 3. Re-import projects
agentos project import --from my-app.yaml
```

### Rollback to Single-Repo

```bash
# Restore pre-migration backup
mv ~/.agentos/db.sqlite ~/.agentos/db.sqlite.multi-repo
cp ~/.agentos/db.sqlite.backup ~/.agentos/db.sqlite
```

---

## Getting Help

### Before Asking for Help

1. Run diagnostics: `agentos project validate my-app --all`
2. Check logs: `tail ~/.agentos/logs/agentos.log`
3. Try `--dry-run` first
4. Search existing issues: [GitHub Issues](https://github.com/your-org/AgentOS/issues)

### Reporting Bugs

Include:
- AgentOS version: `agentos --version`
- Python version: `python --version`
- OS: `uname -a`
- Project config: `cat my-app.yaml`
- Error output: Copy full error message
- Database schema: `sqlite3 ~/.agentos/db.sqlite ".schema project_repos"`

### Support Channels

- 🐛 [Report Issues](https://github.com/your-org/AgentOS/issues)
- 💬 [Community Discord](https://discord.gg/agentos)
- 📖 [Full Documentation](../projects/MULTI_REPO_PROJECTS.md)

---

**Last Updated**: 2026-01-28
