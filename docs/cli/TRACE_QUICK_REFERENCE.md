# CLI Trace Commands Quick Reference

## Commands

### Project Trace

```bash
# View all repositories and recent tasks
agentos project trace <project_id>

# Options
--format table|json|tree    # Output format (default: table)
--limit <n>                 # Max tasks per repository (default: 5)
```

### Task Trace

```bash
# View task cross-repository activities
agentos task repo-trace <task_id>

# Alternative access
agentos task dependencies trace <task_id>

# Options
--format table|json|tree    # Output format (default: table)
--detailed                  # Show file lists and full reasons
```

## Output Formats

| Format | Use Case | Example |
|--------|----------|---------|
| `table` | Human-readable terminal output | `agentos project trace my-app` |
| `json` | Scripting and automation | `agentos project trace my-app --format json \| jq` |
| `tree` | Dependency visualization | `agentos task repo-trace task-123 --format tree` |

## Common Patterns

### Quick Project Overview
```bash
agentos project trace my-app
```

### Investigate Task Changes
```bash
agentos task repo-trace task-123 --detailed
```

### Export for Analysis
```bash
# Project trace
agentos project trace my-app --format json > project.json

# Task trace
agentos task repo-trace task-123 --format json > task.json
```

### Extract Specific Data with jq
```bash
# Get repository names
agentos project trace my-app --format json | jq '.repositories[].name'

# Get changed files for a task
agentos task repo-trace task-123 --format json | jq '.repositories[].changes.files[]'

# Count total files changed
agentos task repo-trace task-123 --format json | jq '[.repositories[].changes.file_count] | add'

# List dependent tasks
agentos task repo-trace task-123 --format json | jq '.dependencies.depended_by[].task_id'
```

### CI/CD Integration
```bash
#!/bin/bash
TASK_ID="task-123"
STATUS=$(agentos task repo-trace $TASK_ID --format json | jq -r '.task.status')

if [ "$STATUS" = "completed" ]; then
  echo "✓ Task completed"
  agentos task repo-trace $TASK_ID --format json | jq '.repositories[].changes'
else
  echo "✗ Task not completed: $STATUS"
  exit 1
fi
```

## Tips

- Use `--limit 10` for large projects with many tasks
- Use `--format json` for scripting and automation
- Use `--detailed` to see individual file changes
- Use `--format tree` to visualize dependency relationships
- Pipe JSON output to `jq` for powerful filtering and extraction

## Related Commands

```bash
agentos project list                     # List all projects
agentos project import-repos             # Import repositories
agentos task list                        # List all tasks
agentos task dependencies show <task_id> # Show dependencies
agentos task dependencies graph          # Export dependency graph
```

## Documentation

- Full guide: [CROSS_REPO_TRACING.md](./CROSS_REPO_TRACING.md)
- Examples: [../examples/cli_trace_usage.sh](../../examples/cli_trace_usage.sh)
- Multi-repo guide: [../MULTI_REPO_GUIDE.md](../MULTI_REPO_GUIDE.md)
