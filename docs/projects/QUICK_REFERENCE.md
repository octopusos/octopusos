# Multi-Repository Quick Reference Card

**AgentOS Multi-Repo Cheat Sheet**

---

## Quick Start (3 Steps)

```bash
# 1. Configure auth
agentos auth add --name github-ssh --type ssh_key --key-path ~/.ssh/id_rsa

# 2. Create config
cat > my-app.yaml <<YAML
name: my-app
repos:
  - name: backend
    url: git@github.com:org/backend
    path: ./be
    role: code
    auth_profile: github-ssh
YAML

# 3. Import
agentos project import --from my-app.yaml
```

---

## Essential Commands

```bash
# Import project
agentos project import --from config.yaml

# List repos
agentos project repos list PROJECT_ID

# Add repo
agentos project repos add PROJECT_ID --name NAME --url URL --path PATH

# Validate
agentos project validate PROJECT_ID --all

# Trace activity
agentos project trace PROJECT_ID

# Check workspace
agentos project workspace check PROJECT_ID
```

---

## Config File Template

```yaml
name: PROJECT_NAME
description: PROJECT_DESCRIPTION

repos:
  - name: REPO_NAME
    url: GIT_URL                 # Optional
    path: ./RELATIVE_PATH        # Default: .
    role: code                   # code | docs | infra | mono-subdir
    writable: true               # true | false
    branch: main                 # Default: main
    auth_profile: PROFILE_NAME   # Optional
```

---

## Repository Roles

| Role | Use Case |
|------|----------|
| `code` | Source code (default) |
| `docs` | Documentation |
| `infra` | Infrastructure configs |
| `mono-subdir` | Monorepo subdirectory |

---

## Task Repo Scopes

| Scope | Access Level |
|-------|--------------|
| `FULL` | Read + Write (if repo.is_writable) |
| `READ_ONLY` | Read only |
| `PATHS` | Limited to specific paths |

---

## Common Patterns

### Frontend + Backend

```yaml
repos:
  - name: backend
    url: git@github.com:org/backend
    path: ./backend
  - name: frontend
    url: git@github.com:org/frontend
    path: ./frontend
```

### Code + Docs

```yaml
repos:
  - name: app
    path: ./app
    role: code
  - name: docs
    path: ./docs
    role: docs
    writable: false  # Read-only
```

### Monorepo

```yaml
repos:
  - name: ui
    url: git@github.com:org/mono
    path: ./packages/ui
    role: mono-subdir
  - name: api
    url: git@github.com:org/mono
    path: ./packages/api
    role: mono-subdir
```

---

## Troubleshooting

### Auth Issues

```bash
# Test SSH
ssh -T git@github.com

# List keys
ssh-add -l

# Add auth profile
agentos auth add --name NAME --type ssh_key --key-path PATH
```

### Import Issues

```bash
# Dry-run first
agentos project import --from config.yaml --dry-run

# Skip validation (if needed)
agentos project import --from config.yaml --skip-validation

# Force overwrite (DANGEROUS)
agentos project import --from config.yaml --force
```

### Workspace Issues

```bash
# Check workspace
agentos project workspace check PROJECT_ID

# Clean workspace (preview)
agentos project workspace clean PROJECT_ID --dry-run

# Clean workspace (execute)
agentos project workspace clean PROJECT_ID --yes
```

---

## Key Files

| File | Purpose |
|------|---------|
| `docs/projects/MULTI_REPO_PROJECTS.md` | Architecture guide |
| `docs/cli/PROJECT_IMPORT.md` | CLI reference |
| `docs/migration/SINGLE_TO_MULTI_REPO.md` | Migration guide |
| `docs/troubleshooting/MULTI_REPO.md` | Troubleshooting |
| `examples/multi-repo/` | Working examples |

---

## Useful Flags

| Flag | Purpose |
|------|---------|
| `--dry-run` | Preview without changes |
| `--yes`, `-y` | Skip confirmations |
| `--force` | Overwrite existing (DANGEROUS) |
| `--skip-validation` | Skip validation checks |
| `--require-write` | Require write permissions |
| `--verbose`, `-v` | Detailed output |

---

## Database Queries (Advanced)

```bash
# List all repos
sqlite3 ~/.agentos/db.sqlite \
  "SELECT * FROM project_repos WHERE project_id='PROJECT_ID';"

# List task repo scopes
sqlite3 ~/.agentos/db.sqlite \
  "SELECT * FROM task_repo_scope WHERE task_id='TASK_ID';"

# List dependencies
sqlite3 ~/.agentos/db.sqlite \
  "SELECT * FROM task_dependency WHERE task_id='TASK_ID';"
```

---

## Quick Reference Links

- 📖 [Full Architecture](./MULTI_REPO_PROJECTS.md)
- 🛠️ [CLI Guide](../cli/PROJECT_IMPORT.md)
- 🚀 [Quick Start Example](../../examples/multi-repo/01_minimal/)
- 🔧 [Troubleshooting](../troubleshooting/MULTI_REPO.md)

---

**Print this card and keep it handy!**
