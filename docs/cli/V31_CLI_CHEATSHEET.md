# v0.4 CLI Cheatsheet

Quick reference card for v0.4 Project-Aware Task OS CLI commands.

---

## Project Commands

```bash
# List projects
agentos project-v31 list [--tags TAG] [--limit N] [--json]

# Create project
agentos project-v31 create NAME [--desc TEXT] [--tags TAG1,TAG2] [--quiet]

# Show project
agentos project-v31 show PROJECT_ID [--json]

# Delete project
agentos project-v31 delete PROJECT_ID [--force] [--yes]
```

---

## Repository Commands

```bash
# Add repository
agentos repo-v31 add \
  --project PROJECT_ID \
  --name NAME \
  --path /absolute/path \
  [--vcs git] \
  [--remote URL] \
  [--branch main] \
  [--quiet]

# List repositories
agentos repo-v31 list [--project PROJECT_ID] [--json]

# Show repository
agentos repo-v31 show REPO_ID [--json]

# Scan Git repo
agentos repo-v31 scan REPO_ID [--json]
```

---

## Task Commands

```bash
# Create task
agentos task-v31 create \
  --project PROJECT_ID \
  --title "Task title" \
  [--intent "Description"] \
  [--ac "Criteria 1"] \
  [--ac "Criteria 2"] \
  [--repo REPO_ID] \
  [--workdir src/path] \
  [--quiet]

# Freeze spec (DRAFT → PLANNED)
agentos task-v31 freeze TASK_ID [--json]

# Bind to project/repo
agentos task-v31 bind TASK_ID \
  --project PROJECT_ID \
  [--repo REPO_ID] \
  [--workdir src/path] \
  [--json]

# Mark ready (PLANNED → READY)
agentos task-v31 ready TASK_ID [--json]

# List tasks
agentos task-v31 list \
  [--project PROJECT_ID] \
  [--status STATUS] \
  [--limit N] \
  [--json]

# Show task
agentos task-v31 show TASK_ID [--json]
```

---

## Common Options

| Option | Description |
|--------|-------------|
| `--json` | Output as JSON for scripting |
| `--quiet` | Only output ID (for piping) |
| `--help` | Show command help |
| `--limit N` | Limit results (default: varies) |
| `--tags TAG1,TAG2` | Filter by tags (OR logic) |
| `--force` | Skip safety checks |
| `--yes` | Skip confirmations |

---

## Complete Workflow

```bash
# 1. Create project
PROJECT_ID=$(agentos project-v31 create "MyApp" --tags backend --quiet)

# 2. Add repo
REPO_ID=$(agentos repo-v31 add --project $PROJECT_ID --name app --path ~/code/app --quiet)

# 3. Create task
TASK_ID=$(agentos task-v31 create --project $PROJECT_ID --title "Feature X" --ac "Tests pass" --quiet)

# 4. Freeze + bind + ready
agentos task-v31 freeze $TASK_ID
agentos task-v31 bind $TASK_ID --project $PROJECT_ID --repo $REPO_ID --workdir src
agentos task-v31 ready $TASK_ID

# 5. View task
agentos task-v31 show $TASK_ID
```

---

## JSON Piping Examples

```bash
# Get all project names
agentos project-v31 list --json | jq '.[] | .name'

# Get ready tasks
agentos task-v31 list --status ready --json | jq '.[] | .task_id'

# Get project tags
agentos project-v31 show $PROJECT_ID --json | jq '.tags[]'

# Count repos in project
agentos repo-v31 list --project $PROJECT_ID --json | jq 'length'
```

---

## Task State Flow

```
DRAFT → freeze → PLANNED → bind+ready → READY → (execution)
```

**Commands**:
1. `task-v31 create` → DRAFT
2. `task-v31 freeze` → PLANNED
3. `task-v31 bind` → (no state change)
4. `task-v31 ready` → READY

---

## Common Patterns

### Create Complete Setup
```bash
P=$(agentos project-v31 create "App" --quiet)
R=$(agentos repo-v31 add --project $P --name repo --path ~/code --quiet)
T=$(agentos task-v31 create --project $P --title "Task" --quiet)
agentos task-v31 freeze $T && \
agentos task-v31 bind $T --project $P --repo $R && \
agentos task-v31 ready $T
```

### List All Ready Tasks
```bash
agentos task-v31 list --status ready
```

### Find Project by Tag
```bash
agentos project-v31 list --tags backend --json | jq '.[] | select(.tags | contains(["api"]))'
```

### Delete Everything (Careful!)
```bash
agentos project-v31 list --json | jq -r '.[] | .project_id' | \
  xargs -I {} agentos project-v31 delete {} --yes --force
```

---

## Error Handling

Common errors and solutions:

| Error | Solution |
|-------|----------|
| `PROJECT_NOT_FOUND` | Verify project ID |
| `PROJECT_NAME_CONFLICT` | Use unique name |
| `SPEC_NOT_FROZEN` | Run `freeze` first |
| `BINDING_INCOMPLETE` | Run `bind` before `ready` |
| `INVALID_PATH` | Use absolute path |
| `REPO_NOT_IN_PROJECT` | Verify repo belongs to project |

---

## Quick Help

```bash
# General help
agentos --help

# Command group help
agentos project-v31 --help
agentos repo-v31 --help
agentos task-v31 --help

# Specific command help
agentos task-v31 create --help
```

---

## Status Values

**Task Statuses**:
- `draft` - Initial state
- `planned` - Spec frozen
- `ready` - Ready for execution
- `executing` - Running
- `succeeded` - Completed successfully
- `failed` - Completed with errors

---

## Version Info

```bash
agentos --version
```

---

**Version**: v0.4.0
**Last Updated**: 2026-01-29

Full documentation: [V31_CLI_GUIDE.md](V31_CLI_GUIDE.md)
