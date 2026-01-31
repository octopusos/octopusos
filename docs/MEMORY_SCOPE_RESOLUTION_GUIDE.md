# Memory Scope Resolution Guide

**Last Updated**: 2026-01-31
**Related Task**: Task #6

---

## Overview

This guide explains how Memory scope resolution works in AgentOS, particularly for the "All Projects" scenario.

---

## Scope Hierarchy

AgentOS Memory supports the following scopes (in order of specificity):

1. **`global`** - System-wide memories (applies to all projects)
2. **`project`** - Project-specific memories
3. **`repo`** - Repository-specific memories
4. **`task`** - Task-specific memories
5. **`agent`** - Agent-specific memories

---

## Scenario Matrix

### Scenario 1: All Projects View (No Project Context)

**Context**: User is in "All Projects" view, no specific project selected
**`project_id`**: `None`

**Scopes Loaded**:
- ✅ `global` (where `project_id IS NULL`)
- ✅ `agent` (where `project_id IS NULL`)
- ❌ `project` (not loaded)
- ❌ `repo` (not loaded)
- ❌ `task` (not loaded)

**Example**:
```python
memory_context = memory_service.build_context(
    project_id=None,  # No project context
    agent_type="chat",
    confidence_threshold=0.3
)
# Returns: Global + agent memories without project_id
```

**Use Cases**:
- User nickname preferences (e.g., "胖哥")
- System-wide conventions
- Agent behavior settings

### Scenario 2: Specific Project View

**Context**: User is working within a specific project
**`project_id`**: `"proj-123"`

**Scopes Loaded**:
- ✅ `global` (where `project_id IS NULL`)
- ✅ `project` (where `project_id = "proj-123"` OR `project_id IS NULL`)
- ✅ `repo` (where `project_id = "proj-123"` OR `project_id IS NULL`)
- ✅ `agent` (where `project_id = "proj-123"` OR `project_id IS NULL`)
- ✅ `task` (if `task_id` provided)

**Example**:
```python
memory_context = memory_service.build_context(
    project_id="proj-123",  # Specific project
    agent_type="chat",
    confidence_threshold=0.3
)
# Returns: Global + project-specific + agent memories
```

**Use Cases**:
- Project-specific conventions
- Architecture decisions
- Technology stack preferences

### Scenario 3: Task Execution

**Context**: Agent is executing a specific task
**`project_id`**: `"proj-123"`
**`task_id`**: `"task-456"`

**Scopes Loaded**:
- ✅ All scopes from Scenario 2
- ✅ `task` (where `task_id = "task-456"`)

**Example**:
```python
memory_context = memory_service.build_context(
    project_id="proj-123",
    agent_type="backend-engineer",
    task_id="task-456",
    confidence_threshold=0.3
)
# Returns: Global + project + task + agent memories
```

---

## Implementation Details

### Key Files

1. **`agentos/core/chat/context_builder.py`**
   - `_load_memory_facts()` method
   - Handles None project_id case

2. **`agentos/core/memory/service.py`**
   - `build_context()` method
   - Constructs SQL queries based on scope

### Query Construction Logic

```python
# Pseudo-code for query construction
for scope in ["global", "project", "repo", "agent"]:
    query = "SELECT * FROM memory_items WHERE scope = ?"

    if scope in ["project", "repo", "agent"]:
        if project_id is not None:
            # Include both project-specific and global items
            query += " AND (project_id = ? OR project_id IS NULL)"
        else:
            # Only include items without project_id
            query += " AND project_id IS NULL"
```

---

## Memory Creation Guidelines

### Global Memories

**When to Use**: System-wide settings that apply across all projects

**Example**:
```python
{
    "scope": "global",
    "type": "user_preference",
    "content": {
        "summary": "用户喜欢被称呼为'胖哥'",
        "details": "User prefers to be called '胖哥' (Pang Ge)"
    },
    "project_id": None,  # ← Must be None
    "confidence": 0.9
}
```

### Project Memories

**When to Use**: Project-specific information

**Example**:
```python
{
    "scope": "project",
    "type": "architecture_decision",
    "content": {
        "summary": "Use SQLite for local storage",
        "details": "Decided to use SQLite for simplicity"
    },
    "project_id": "proj-123",  # ← Must match project
    "confidence": 0.85
}
```

### Agent Memories

**When to Use**: Agent behavior patterns

**Example**:
```python
{
    "scope": "agent",
    "type": "interaction_pattern",
    "content": {
        "summary": "Use friendly tone in chat",
        "details": "Chat agent should maintain conversational tone"
    },
    "project_id": None,  # Can be None (global) or project-specific
    "confidence": 0.8
}
```

---

## Troubleshooting

### Issue: Global memories not loading in "All Projects" view

**Symptoms**:
- User nickname not recognized
- System-wide preferences not applied
- Empty memory context when `project_id=None`

**Solution**:
- Verify memories have `scope="global"` and `project_id IS NULL`
- Check `confidence_threshold` (must be >= memory's confidence)
- Review logs for "No project_id, falling back to global + agent scope memories"

**Fixed in Task #6**: Hard short-circuit that blocked all memory loading

### Issue: Project memories leaking between projects

**Symptoms**:
- Memories from Project A appearing in Project B
- Incorrect project context in responses

**Solution**:
- Verify `project_id` is correctly set in memory items
- Check query logic ensures proper filtering
- Review `memory_context.metadata.filters_applied`

### Issue: Memory budget exceeded

**Symptoms**:
- Not all memories loading
- `budget_stats.trimmed = true`

**Solution**:
- Increase `budget.max_memories` or `budget.max_tokens`
- Review memory priority scores (scope × confidence)
- Consider consolidating memories

---

## Observability

### Logging

Enable INFO-level logging to see scope resolution details:

```python
import logging
logging.getLogger("agentos.core.chat.context_builder").setLevel(logging.INFO)
logging.getLogger("agentos.core.memory.service").setLevel(logging.INFO)
```

**Expected Log Output**:
```
INFO: Loaded 2 memory facts (project_id=None/global, scopes={'global': 1, 'agent': 1})
```

### Metrics

Monitor these metrics to track memory usage:

- `memory_context.summary.total_memories` - Total memories loaded
- `memory_context.summary.by_scope` - Breakdown by scope
- `memory_context.metadata.budget.trimmed` - Whether budget limit was hit
- `memory_context.metadata.budget.removed_count` - Number of memories trimmed

---

## API Reference

### `MemoryService.build_context()`

```python
def build_context(
    self,
    project_id: Optional[str],      # Can be None for global-only
    agent_type: str,                # Agent type identifier
    task_id: Optional[str] = None,  # Optional task context
    confidence_threshold: float = 0.3,  # Minimum confidence
    budget: Optional[ContextBudget] = None  # Memory budget
) -> dict:
    """Build MemoryPack context for agent execution."""
```

**Returns**: MemoryPack dict with structure:
```python
{
    "schema_version": "1.0.0",
    "project_id": project_id,
    "agent_type": agent_type,
    "memories": [...],  # List of memory items
    "summary": {
        "total_memories": int,
        "by_type": {...},
        "by_scope": {...}  # Scope breakdown
    },
    "metadata": {
        "confidence_threshold": float,
        "filters_applied": [...],
        "budget": {...}
    }
}
```

### `ContextBuilder._load_memory_facts()`

```python
def _load_memory_facts(self, session_id: str) -> List[Dict[str, Any]]:
    """
    Load pinned facts from Memory.

    Supports three scenarios:
    1. With explicit project_id: Load global + project + agent scope
    2. project_id is None: Load only global + agent scope
    3. "All Projects": Special handling, load all visible memories
    """
```

---

## Best Practices

1. **Use Global Scope Sparingly**
   - Only for truly system-wide settings
   - Keep global memories concise

2. **Always Set project_id for Project Memories**
   - Ensures proper isolation
   - Prevents cross-contamination

3. **Monitor Budget Utilization**
   - Check `budget_stats.trimmed` flag
   - Review removed memory count

4. **Leverage Confidence Scores**
   - Higher confidence = higher priority
   - Update confidence based on usage

5. **Test Scope Resolution**
   - Verify memories load in correct contexts
   - Test both with and without project_id

---

## Testing

### Unit Tests

See: `/Users/pangge/PycharmProjects/AgentOS/tests/unit/core/chat/test_context_builder_scope.py`

**Key Test Cases**:
- `test_load_memory_without_project_id()` - All Projects scenario
- `test_load_memory_with_project_id()` - Project-specific scenario
- `test_load_memory_filters_other_projects()` - Data isolation
- `test_memory_service_build_context_with_none_project_id()` - Service layer

### Manual Testing

```bash
# Test global memory in All Projects view
python3 -m agentos.cli.memory list --scope global

# Test project memory
python3 -m agentos.cli.memory list --scope project --project-id proj-123

# Build context
python3 -m agentos.cli.memory build-context --project-id proj-123 --agent-type chat
```

---

## Change Log

### 2026-01-31 - Task #6 Fix
- ✅ Removed hard short-circuit in `context_builder.py`
- ✅ Updated `MemoryService.build_context()` to accept `Optional[str]`
- ✅ Fixed query logic for None project_id
- ✅ Added comprehensive test coverage
- ✅ Enhanced logging with scope information

---

## Related Documentation

- [Memory Architecture](./MEMORY_ARCHITECTURE.md)
- [Task #6 Fix Report](../TASK6_MEMORY_SCOPE_FIX_REPORT.md)
- [Memory Service API](../api/memory_service.md)

---

**Questions?** Contact the Memory team or file an issue.
