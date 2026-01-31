# v0.4 CLI Quickstart

Quick reference for v0.4 Project-Aware Task OS CLI commands.

## Installation

The CLI is available after installing AgentOS:

```bash
pip install agentos
```

## Verify Installation

```bash
agentos --version
agentos project-v31 --help
```

## 5-Minute Quickstart

### 1. Create a Project

```bash
# Create project
PROJECT_ID=$(agentos project-v31 create "My First Project" \
  --desc "Learning v0.4 Project-Aware Task OS" \
  --tags tutorial \
  --quiet)

echo "Created project: $PROJECT_ID"
```

### 2. Add a Repository

```bash
# Add your code repository
REPO_ID=$(agentos repo-v31 add \
  --project $PROJECT_ID \
  --name my-app \
  --path /path/to/your/code \
  --quiet)

echo "Added repo: $REPO_ID"
```

### 3. Create a Task

```bash
# Create a task
TASK_ID=$(agentos task-v31 create \
  --project $PROJECT_ID \
  --title "Add user login" \
  --intent "Implement JWT authentication" \
  --ac "Tests pass" \
  --ac "Code reviewed" \
  --quiet)

echo "Created task: $TASK_ID"
```

### 4. Prepare Task for Execution

```bash
# Freeze the spec
agentos task-v31 freeze $TASK_ID

# Bind to repo
agentos task-v31 bind $TASK_ID \
  --project $PROJECT_ID \
  --repo $REPO_ID \
  --workdir src/auth

# Mark as ready
agentos task-v31 ready $TASK_ID

# View task details
agentos task-v31 show $TASK_ID
```

## Common Commands

### List Projects
```bash
agentos project-v31 list
agentos project-v31 list --tags backend
```

### List Repositories
```bash
agentos repo-v31 list
agentos repo-v31 list --project $PROJECT_ID
```

### List Tasks
```bash
agentos task-v31 list
agentos task-v31 list --project $PROJECT_ID
agentos task-v31 list --status ready
```

### Show Details
```bash
agentos project-v31 show $PROJECT_ID
agentos repo-v31 show $REPO_ID
agentos task-v31 show $TASK_ID
```

## JSON Output

All commands support `--json` for scripting:

```bash
# Get project list as JSON
agentos project-v31 list --json | jq '.[] | .name'

# Get task status
agentos task-v31 show $TASK_ID --json | jq '.status'
```

## Full Documentation

See [V31_CLI_GUIDE.md](V31_CLI_GUIDE.md) for complete documentation.

## Next Steps

1. Read the [CLI Guide](V31_CLI_GUIDE.md) for detailed usage
2. Check out [API Reference](../api/V31_API_REFERENCE.md) for programmatic access
3. Review [ADR v0.4](../architecture/ADR_V04_PROJECT_AWARE_TASK_OS.md) for design rationale

---

**Version**: v0.4.0
**Last Updated**: 2026-01-29
