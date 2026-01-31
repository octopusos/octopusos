# Migration Guide: Single to Multi-Repo

**Migrating from Single-Repository to Multi-Repository Projects**

This guide helps you migrate existing single-repository projects to multi-repository mode.

---

## Compatibility Guarantee

**Good News**: Single-repository projects continue to work without any changes.

AgentOS v0.18+ maintains **full backward compatibility** with single-repo projects through automatic migration:

- ✅ Existing projects automatically get a "default" repository binding
- ✅ Single-repo API continues to work (with deprecation warnings)
- ✅ No code changes required for existing workflows
- ✅ Opt-in migration to multi-repo when ready

---

## Migration Paths

### Path 1: Do Nothing (Recommended for Most Users)

**When to use**: You only have single-repo projects and don't need multi-repo features.

**Action**: None. Your existing projects will continue to work as before.

**What happens**:
- Existing projects are auto-migrated to have a single "default" repo binding
- All existing functionality remains unchanged
- You can add more repos later if needed

---

### Path 2: Gradual Migration (Recommended for Multi-Repo Users)

**When to use**: You want to add more repositories to existing projects gradually.

**Steps**:

1. **Keep existing project unchanged**:
   ```bash
   # Your existing single-repo project continues to work
   agentos project repos list my-existing-project
   # Output: default (.) - Auto-migrated from single-repo
   ```

2. **Add new repositories**:
   ```bash
   # Add a second repository
   agentos project repos add my-existing-project \
     --name frontend \
     --url git@github.com:org/frontend \
     --path ./fe \
     --role code
   ```

3. **New tasks can use multi-repo mode**:
   ```bash
   # Create task with multi-repo scope
   agentos task create "Update API and frontend" \
     --project my-existing-project \
     --repo backend:full \
     --repo frontend:full
   ```

4. **Existing tasks remain single-repo**:
   - Old tasks only see the "default" repo
   - No breaking changes to existing workflows

---

### Path 3: Full Migration (Advanced)

**When to use**: You want to fully restructure an existing project.

**Steps**:

1. **Export current project metadata**:
   ```bash
   sqlite3 ~/.agentos/db.sqlite \
     "SELECT * FROM projects WHERE id='my-project'" > project-backup.sql
   ```

2. **Create new multi-repo configuration**:
   ```yaml
   # new-project.yaml
   name: my-project-v2
   description: Migrated multi-repo project

   repos:
     - name: backend
       url: git@github.com:org/backend
       path: ./backend
       role: code

     - name: frontend
       url: git@github.com:org/frontend
       path: ./frontend
       role: code
   ```

3. **Import new project**:
   ```bash
   agentos project import --from new-project.yaml
   ```

4. **Migrate tasks** (manual):
   - Review existing tasks in old project
   - Recreate tasks in new project with multi-repo scopes
   - Update task IDs in any external systems

5. **Archive old project**:
   ```bash
   # Remove old project (after verifying migration)
   sqlite3 ~/.agentos/db.sqlite \
     "DELETE FROM projects WHERE id='my-project'"
   ```

---

## Migration Checklist

Use this checklist to ensure a smooth migration:

### Pre-Migration

- [ ] Backup database: `cp ~/.agentos/db.sqlite ~/.agentos/db.sqlite.backup`
- [ ] List existing projects: `agentos project list`
- [ ] List existing tasks: `agentos task list --project my-project`
- [ ] Document current workspace layout
- [ ] Test multi-repo import in a separate workspace (`--dry-run`)

### During Migration

- [ ] Run `agentos project import --dry-run` first
- [ ] Verify no path conflicts with existing projects
- [ ] Test auth profiles: `agentos project validate --check-auth`
- [ ] Test remote URLs: `agentos project validate --check-urls`

### Post-Migration

- [ ] Verify project imported: `agentos project repos list my-project`
- [ ] Test creating new task: `agentos task create ...`
- [ ] Verify existing tasks still work
- [ ] Check audit trail: `agentos project trace my-project`
- [ ] Update documentation and team runbooks

---

## Common Migration Scenarios

### Scenario 1: Adding Documentation Repo

**Before** (single-repo):
```
my-app/
  ├── src/
  ├── docs/
  └── README.md
```

**After** (multi-repo):
```
my-app/
  ├── app/         (code repo)
  │   └── src/
  └── docs/        (docs repo, separate)
      └── api/
```

**Migration**:
```bash
# Add docs as separate repo
agentos project repos add my-app \
  --name docs \
  --url git@github.com:org/docs \
  --path ./docs \
  --role docs \
  --read-only
```

---

### Scenario 2: Splitting Monorepo

**Before** (monorepo):
```
monorepo/
  ├── frontend/
  ├── backend/
  └── shared/
```

**After** (multi-repo with subdirs):
```
monorepo/
  ├── frontend/    (mono-subdir)
  ├── backend/     (mono-subdir)
  └── shared/      (mono-subdir)
```

**Migration**:
```yaml
name: my-monorepo
repos:
  - name: frontend
    url: git@github.com:org/monorepo
    path: ./frontend
    role: mono-subdir

  - name: backend
    url: git@github.com:org/monorepo
    path: ./backend
    role: mono-subdir

  - name: shared
    url: git@github.com:org/monorepo
    path: ./shared
    role: mono-subdir
```

---

### Scenario 3: Extracting Infrastructure

**Before** (everything in one repo):
```
app/
  ├── src/
  ├── terraform/
  └── k8s/
```

**After** (separate infra repo):
```
workspace/
  ├── app/          (code)
  │   └── src/
  └── infra/        (infrastructure)
      ├── terraform/
      └── k8s/
```

**Migration**:
```bash
# Add infrastructure repo
agentos project repos add my-app \
  --name infra \
  --url git@github.com:org/infra \
  --path ./infra \
  --role infra
```

---

## Rollback Procedure

If migration fails or causes issues:

1. **Restore database backup**:
   ```bash
   cp ~/.agentos/db.sqlite.backup ~/.agentos/db.sqlite
   ```

2. **Remove new project**:
   ```bash
   sqlite3 ~/.agentos/db.sqlite \
     "DELETE FROM projects WHERE id='new-project'"
   ```

3. **Verify rollback**:
   ```bash
   agentos project list
   agentos project repos list my-project
   ```

---

## FAQ

### Q: Will my existing tasks break after migration?

**A**: No. Existing tasks will continue to use the "default" repository binding created automatically.

### Q: Do I need to migrate immediately?

**A**: No. Migration is optional. Single-repo projects continue to work indefinitely.

### Q: Can I mix single-repo and multi-repo projects?

**A**: Yes. AgentOS supports both modes simultaneously.

### Q: What happens to task IDs during migration?

**A**: Task IDs are preserved. Task metadata (repo scopes) may need updates if you restructure projects.

### Q: Can I undo a migration?

**A**: Yes, by restoring the database backup. Always backup before migration.

---

## Best Practices

1. **Start Small**: Migrate one project at a time
2. **Test First**: Use `--dry-run` to preview changes
3. **Backup Always**: Backup database before any migration
4. **Gradual Adoption**: Add repos incrementally rather than all at once
5. **Document Changes**: Update team runbooks and documentation
6. **Monitor Logs**: Check logs after migration for deprecation warnings

---

## Getting Help

If you encounter issues during migration:

- 🐛 [Report Migration Issues](https://github.com/your-org/AgentOS/issues)
- 📖 [Full Documentation](../projects/MULTI_REPO_PROJECTS.md)
- 💬 [Community Support](https://discord.gg/agentos)

---

**Migration Support**: For complex migrations, contact the AgentOS team for assistance.
