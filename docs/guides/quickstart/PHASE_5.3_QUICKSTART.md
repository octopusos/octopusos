# Phase 5.3 Quick Start Guide

## 🚀 What is Phase 5.3?

Phase 5.3 implements **automatic dependency tracking** for tasks across multiple repositories. It detects when tasks depend on each other and builds a dependency graph (DAG) to ensure proper execution order.

## 🎯 Quick Example

```python
from agentos.core.task.dependency_service import TaskDependencyService
from agentos.core.task.runner_integration import prepare_execution_env

# Initialize
dep_service = TaskDependencyService(db)
exec_env = prepare_execution_env(task)

# Auto-detect dependencies
dependencies = dep_service.detect_dependencies(task, exec_env)

# Save dependencies
for dep in dependencies:
    dep_service.create_dependency_safe(
        dep.task_id,
        dep.depends_on_task_id,
        dep.dependency_type,
        dep.reason
    )

# Build dependency graph
graph = dep_service.build_dependency_graph()
execution_order = graph.topological_sort()
print(f"Execute in order: {' -> '.join(execution_order)}")
```

## 📊 Example Output

```
Detected dependencies:
  task-frontend-002 -> task-backend-001 (requires)
    Reason: Uses artifact commit:abc123def456 from task-backend-001

  task-docs-003 -> task-frontend-002 (requires)
    Reason: Uses artifact commit:xyz789ghi012 from task-frontend-002

  task-docs-003 -> task-backend-001 (requires)
    Reason: Uses artifact commit:abc123def456 from task-backend-001

Execution order: task-backend-001 -> task-frontend-002 -> task-docs-003
```

## 🔍 How It Works

### 1. Dependency Detection Rules

**Rule 1: Artifact References** (Most Important)
- When Task B uses a commit/patch created by Task A
- Automatically creates `REQUIRES` dependency
- Example: Task B uses commit `abc123` from Task A

**Rule 2: File Reads**
- When Task B reads a file modified by Task A
- Creates `SUGGESTS` dependency (weaker)
- Example: Task B reads `src/api.py` written by Task A

**Rule 3: Artifact Directory**
- When Task B reads `.agentos/artifacts/<taskA>.json`
- Creates `REQUIRES` dependency
- Example: Task B reads artifact file from Task A

### 2. Dependency Types

| Type       | Meaning                              | Priority |
|------------|--------------------------------------|----------|
| `BLOCKS`   | Must wait for completion             | High     |
| `REQUIRES` | Needs artifacts, can start early     | Medium   |
| `SUGGESTS` | Related but not critical             | Low      |

### 3. Cycle Prevention

```python
# Safe creation with cycle check
try:
    dep_service.create_dependency_safe(
        task_id="task-b",
        depends_on_task_id="task-a",
        dependency_type=DependencyType.REQUIRES,
        reason="Task B needs output from Task A"
    )
except CircularDependencyError as e:
    print(f"Cannot create: {e}")
```

## 💻 CLI Commands

### Show Dependencies

```bash
# What does this task depend on?
agentos task dependencies show task-123

# Who depends on this task?
agentos task dependencies show task-123 --reverse

# JSON output
agentos task dependencies show task-123 --format json
```

### Export Dependency Graph

```bash
# Export to DOT format
agentos task dependencies graph -o deps.dot

# Render as PNG
dot -Tpng deps.dot -o deps.png
```

### Check for Cycles

```bash
agentos task dependencies check-cycles
```

### Query Ancestry

```bash
# Show all tasks this depends on (recursively)
agentos task dependencies ancestors task-123

# Show all tasks that depend on this (recursively)
agentos task dependencies descendants task-123
```

### Execution Order

```bash
# Show optimal execution order
agentos task dependencies topological-sort
```

### Manual Management

```bash
# Create dependency
agentos task dependencies create task-b task-a \
  --type requires \
  --reason "Task B needs Task A's output" \
  --safe  # Checks for cycles

# Delete dependency
agentos task dependencies delete task-b task-a
```

## 🧪 Run the Example

```bash
# Run complete example
python examples/dependency_detection_example.py

# Output:
# - Creates 3 tasks (backend, frontend, docs)
# - Auto-detects dependencies
# - Builds dependency graph
# - Shows execution order
# - Exports to dependency_graph.dot
```

## 📈 Visual Example

```
Scenario: Building a feature across 3 repos

┌─────────────────────────────────────────────────────────┐
│ Task A: Add user auth API (backend repo)                │
│ - Creates commit abc123                                 │
│ - Writes src/api/auth.py                                │
└─────────────────────────────────────────────────────────┘
                    │
                    │ REQUIRES (uses commit abc123)
                    ▼
┌─────────────────────────────────────────────────────────┐
│ Task B: Integrate auth in UI (frontend repo)            │
│ - References commit abc123                              │
│ - Reads backend files                                   │
│ - Creates commit xyz789                                 │
└─────────────────────────────────────────────────────────┘
                    │
                    │ REQUIRES (uses commit xyz789)
                    ▼
┌─────────────────────────────────────────────────────────┐
│ Task C: Document auth flow (docs repo)                  │
│ - References commits abc123, xyz789                     │
│ - Depends on both A and B                               │
└─────────────────────────────────────────────────────────┘

Execution Order: A → B → C
```

## 🎯 Integration with TaskRunner

Add to your task execution pipeline:

```python
def execute_task(task: Task):
    # 1. Execute task
    result = run_task_logic(task)

    # 2. Auto-detect dependencies
    dep_service = TaskDependencyService(db)
    exec_env = prepare_execution_env(task)
    deps = dep_service.detect_dependencies(task, exec_env)

    # 3. Save dependencies
    for dep in deps:
        try:
            dep_service.create_dependency_safe(
                dep.task_id,
                dep.depends_on_task_id,
                dep.dependency_type,
                dep.reason,
                created_by="auto_detect"
            )
        except CircularDependencyError:
            logger.warning("Skipped circular dependency")

    return result
```

## 📝 Database Schema

Dependencies are stored in the `task_dependency` table:

```sql
CREATE TABLE task_dependency (
    dependency_id INTEGER PRIMARY KEY,
    task_id TEXT NOT NULL,              -- Dependent task
    depends_on_task_id TEXT NOT NULL,   -- Dependency task
    dependency_type TEXT NOT NULL,      -- blocks | requires | suggests
    reason TEXT,                        -- Why this dependency exists
    created_at TIMESTAMP,
    created_by TEXT,                    -- user | auto_detect | system
    metadata TEXT,                      -- JSON extras

    UNIQUE(task_id, depends_on_task_id, dependency_type),
    CHECK (task_id != depends_on_task_id)
);
```

## 🧪 Testing

```bash
# Unit tests
pytest tests/unit/task/test_dependency_service.py -v

# Integration tests
pytest tests/integration/task/test_dependency_workflow.py -v

# Run example
python examples/dependency_detection_example.py
```

## 📚 Full Documentation

See `/agentos/core/task/DEPENDENCY_SERVICE_README.md` for:
- Detailed API reference
- Advanced usage examples
- Performance tuning
- Error handling guide
- Architecture details

## ⚡ Key Features

✅ **Automatic Detection**: No manual dependency specification needed
✅ **Cycle Prevention**: Prevents circular dependencies
✅ **Cross-Repo Support**: Works across multiple repositories
✅ **Multiple Detection Rules**: Artifact refs, file reads, directory scanning
✅ **DAG Operations**: Topological sort, ancestor/descendant queries
✅ **GraphViz Export**: Visual dependency graphs
✅ **CLI Interface**: Complete command-line tools
✅ **Type Safety**: Enum-based dependency types
✅ **Deduplication**: Keeps strongest dependency type
✅ **Error Handling**: Clear error messages

## 🎯 Use Cases

1. **Execution Ordering**: Ensure tasks run in correct order
2. **Dependency Tracking**: Understand task relationships
3. **Impact Analysis**: Find all tasks affected by a change
4. **Scheduling**: Optimize parallel task execution
5. **Debugging**: Trace why tasks depend on each other
6. **Visualization**: Generate dependency graphs

## 🔗 Related Phases

- **Phase 5.1**: Runner support for cross-repository workspace selection
- **Phase 5.2**: Cross-repository audit trail
- **Phase 6.1**: CLI visualization tools
- **Phase 6.2**: WebUI dependency visualization

---

**Ready to use!** Start with the example and explore the CLI commands.
