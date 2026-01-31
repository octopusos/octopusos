# Capability Registry and Audit System

**Status**: ✅ Implemented and Tested
**Version**: 1.0
**Date**: 2026-01-28

## Overview

This document describes the unified Capability Registry and Audit System implemented for AgentOS. These systems provide centralized management for system capabilities (Code Assets, Preview, Task Materialization) and comprehensive audit logging.

## Architecture

### Components

```
agentos/core/
├── capability_registry.py  # Capability and preset management
└── audit.py               # Audit event logging and querying
```

### Key Features

1. **Capability Registry**
   - Declarative capability definitions
   - Runtime preset management
   - Smart dependency injection
   - Security policy configuration

2. **Audit System**
   - Unified event logging to task_audits table
   - Support for orphan events (not tied to tasks)
   - JSON payload for flexible metadata
   - Query interface for event retrieval

## Capability Registry

### Usage

```python
from agentos.core.capability_registry import get_capability_registry

# Get registry instance (singleton)
registry = get_capability_registry()

# List all capabilities
capabilities = registry.list_all()

# Get specific capability
preview_cap = registry.get("preview")

# Get preset
three_preset = registry.get_preset("preview", "three-webgl-umd")

# Detect required dependencies
code = "const controls = new THREE.OrbitControls(camera);"
deps = registry.detect_required_deps(three_preset, code)
# Returns: [three-core, three-orbit-controls]
```

### Registered Capabilities

#### 1. Code Asset Management
- **ID**: `code_asset`
- **Kind**: `CODE_ASSET`
- **Risk Level**: `MEDIUM`
- **Audit Events**:
  - `SNIPPET_CREATED`
  - `SNIPPET_UPDATED`
  - `SNIPPET_DELETED`
  - `SNIPPET_USED_IN_TASK`

#### 2. Preview Runtime
- **ID**: `preview`
- **Kind**: `PREVIEW`
- **Risk Level**: `MEDIUM`
- **Audit Events**:
  - `PREVIEW_SESSION_CREATED`
  - `PREVIEW_SESSION_OPENED`
  - `PREVIEW_SESSION_EXPIRED`
  - `PREVIEW_RUNTIME_SELECTED`
  - `PREVIEW_DEP_INJECTED`
- **Presets**: See [Runtime Presets](#runtime-presets)

#### 3. Task Materialization
- **ID**: `task_materialization`
- **Kind**: `TASK_MATERIALIZATION`
- **Risk Level**: `HIGH`
- **Audit Events**:
  - `TASK_MATERIALIZED_FROM_SNIPPET`

### Runtime Presets

#### P0 Presets (Fully Implemented)

##### 1. html-basic
Pure HTML/CSS/JS environment with no external dependencies.

```python
preset = registry.get_preset("preview", "html-basic")
# No dependencies
# Minimal security restrictions
```

##### 2. three-webgl-umd (P0 Priority)
Three.js r169 with WebGL support and smart dependency injection.

**Core Dependencies** (always loaded):
- `three-core`: Three.js main library

**Optional Dependencies** (auto-injected based on code):
- `three-fontloader`: Loaded when code contains "FontLoader"
- `three-orbit-controls`: Loaded when code contains "OrbitControls"
- `three-gltf-loader`: Loaded when code contains "GLTFLoader"
- `three-text-geometry`: Loaded when code contains "TextGeometry"

**Example**:
```python
preset = registry.get_preset("preview", "three-webgl-umd")

# Basic Three.js code
code1 = "const scene = new THREE.Scene();"
deps1 = registry.detect_required_deps(preset, code1)
# Returns: [three-core]

# Code with OrbitControls
code2 = "const controls = new THREE.OrbitControls(camera);"
deps2 = registry.detect_required_deps(preset, code2)
# Returns: [three-core, three-orbit-controls]
```

##### 3. chartjs-umd
Chart.js library for data visualization.

```python
preset = registry.get_preset("preview", "chartjs-umd")
# Dependencies: [chartjs-core]
```

##### 4. d3-umd
D3.js library for data-driven visualizations.

```python
preset = registry.get_preset("preview", "d3-umd")
# Dependencies: [d3-core]
```

### Security Policies

Each preset includes:
- **Sandbox Policy**: iframe sandbox attributes
- **CSP Rules**: Content Security Policy
- **Allowed Origins**: For external CDN resources

Example from three-webgl-umd:
```python
sandbox_policy = {
    "allow": ["scripts", "same-origin"],
    "csp": "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; ..."
}
```

## Audit System

### Usage

```python
from agentos.core.audit import (
    log_audit_event,
    get_audit_events,
    SNIPPET_CREATED,
    PREVIEW_SESSION_CREATED,
    TASK_MATERIALIZED_FROM_SNIPPET,
)

# Log snippet creation (orphan event - no task_id)
log_audit_event(
    event_type=SNIPPET_CREATED,
    snippet_id="snippet-123",
    metadata={
        "language": "javascript",
        "size": 150,
        "source": "chat"
    }
)

# Log preview session with task
log_audit_event(
    event_type=PREVIEW_SESSION_CREATED,
    task_id="task-456",
    preview_id="preview-789",
    metadata={
        "preset": "three-webgl-umd",
        "deps_injected": ["three-core", "three-orbit-controls"]
    }
)

# Query events
events = get_audit_events(snippet_id="snippet-123")
for event in events:
    print(f"{event['event_type']}: {event['payload']}")
```

### Event Types

#### Snippet Events
- `SNIPPET_CREATED` - New snippet created
- `SNIPPET_UPDATED` - Snippet metadata updated
- `SNIPPET_DELETED` - Snippet deleted
- `SNIPPET_USED_IN_TASK` - Snippet used in task execution

#### Preview Events
- `PREVIEW_SESSION_CREATED` - New preview session created
- `PREVIEW_SESSION_OPENED` - User opened preview
- `PREVIEW_SESSION_EXPIRED` - Session expired (TTL)
- `PREVIEW_RUNTIME_SELECTED` - Runtime preset selected
- `PREVIEW_DEP_INJECTED` - Dependency auto-injected

#### Task Events
- `TASK_MATERIALIZED_FROM_SNIPPET` - Task created from snippet

### Database Schema

Integrates with existing `task_audits` table:

```sql
CREATE TABLE task_audits (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,  -- Uses ORPHAN for events without task
    level TEXT DEFAULT 'info',  -- info|warn|error
    event_type TEXT NOT NULL,
    payload TEXT,  -- JSON: {snippet_id, preview_id, ...metadata}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
);
```

### Orphan Events

Events not tied to a specific task use a special `ORPHAN` task:
- Automatically created on first orphan event
- Task ID: `ORPHAN`
- Status: `orphan`
- Title: "Orphan Events Container"

This maintains referential integrity while allowing flexible event logging.

### Query Interface

```python
# Query by snippet
events = get_audit_events(snippet_id="snippet-123")

# Query by preview session
events = get_audit_events(preview_id="preview-789")

# Query by task
events = get_audit_events(task_id="task-456")

# Query by event type
events = get_audit_events(event_type=SNIPPET_CREATED)

# Query by level
events = get_audit_events(level="error")

# Convenience functions
from agentos.core.audit import (
    get_snippet_audit_trail,
    get_preview_audit_trail,
    get_task_audits,
)

snippet_trail = get_snippet_audit_trail("snippet-123")
preview_trail = get_preview_audit_trail("preview-789")
task_audits = get_task_audits("task-456")
```

## Testing

### Test Coverage

All functionality is verified by `test_capability_registry_audit.py`:

1. ✅ Capability Registry
   - Registration and querying
   - Capability metadata
   - Audit event definitions

2. ✅ Runtime Presets
   - All 4 P0 presets defined
   - Dependency structures
   - Security policies

3. ✅ Dependency Detection
   - Core dependencies always loaded
   - Optional dependencies auto-injected
   - Pattern matching works correctly

4. ✅ Audit System
   - Event logging to database
   - Orphan task creation
   - Event querying
   - Payload serialization

### Running Tests

```bash
python3 test_capability_registry_audit.py
```

Expected output:
```
============================================================
✅ ALL TESTS PASSED
============================================================

Verification Summary:
✅ Capability Registry can register and query
✅ Four P0 presets defined (html-basic, three-webgl-umd, chartjs-umd, d3-umd)
✅ detect_required_deps works for three-webgl-umd
✅ Audit functions can write to task_audits table

Ready for integration! 🎉
```

## Integration Guidelines

### For Preview API

```python
from agentos.core.capability_registry import get_capability_registry
from agentos.core.audit import log_audit_event, PREVIEW_SESSION_CREATED

# Get preset and detect dependencies
registry = get_capability_registry()
preset = registry.get_preset("preview", "three-webgl-umd")
deps = registry.detect_required_deps(preset, user_code)

# Create preview session
session_id = create_session(html, preset, deps)

# Log audit event
log_audit_event(
    event_type=PREVIEW_SESSION_CREATED,
    preview_id=session_id,
    metadata={
        "preset": preset.id,
        "deps_injected": [d.id for d in deps]
    }
)
```

### For Snippets API

```python
from agentos.core.audit import (
    log_audit_event,
    SNIPPET_CREATED,
    SNIPPET_USED_IN_TASK,
)

# On snippet creation
log_audit_event(
    event_type=SNIPPET_CREATED,
    snippet_id=snippet_id,
    metadata={
        "language": language,
        "source": "chat",
        "size": len(code)
    }
)

# When snippet used in task
log_audit_event(
    event_type=SNIPPET_USED_IN_TASK,
    task_id=task_id,
    snippet_id=snippet_id,
    metadata={"auto_run": True}
)
```

### For Task Materialization

```python
from agentos.core.audit import (
    log_audit_event,
    TASK_MATERIALIZED_FROM_SNIPPET,
)

# When creating task from snippet
log_audit_event(
    event_type=TASK_MATERIALIZED_FROM_SNIPPET,
    task_id=new_task_id,
    snippet_id=snippet_id,
    metadata={
        "auto_run": auto_run,
        "preset": preset_id
    }
)
```

## Future Extensions

### Adding New Capabilities

```python
from agentos.core.capability_registry import (
    Capability,
    CapabilityKind,
    RiskLevel,
)

# Define custom capability kind
class CapabilityKind(Enum):
    # ... existing kinds
    MY_NEW_FEATURE = "my_new_feature"

# Register capability
registry.register(Capability(
    capability_id="my_feature",
    kind=CapabilityKind.MY_NEW_FEATURE,
    name="My Feature",
    description="Does something awesome",
    risk_level=RiskLevel.MEDIUM,
    requires_admin_token=False,
    audit_events=["MY_FEATURE_USED"],
))
```

### Adding New Presets

```python
from agentos.core.capability_registry import (
    RuntimePreset,
    RuntimeDependency,
)

# Create custom preset
my_preset = RuntimePreset(
    id="my-library-preset",
    name="My Library",
    description="Custom visualization library",
    dependencies=[
        RuntimeDependency(
            id="my-lib-core",
            url="https://cdn.example.com/my-lib.js",
            type="script",
            order=0,
        ),
    ],
    sandbox_policy={"allow": ["scripts"]},
    auto_inject_rules={},
)

# Add to capability
capability = registry.get("preview")
capability.presets.append(my_preset)
```

### Adding New Audit Events

```python
# In audit.py
MY_NEW_EVENT = "MY_NEW_EVENT"

# Add to valid events
VALID_EVENT_TYPES = {
    # ... existing events
    MY_NEW_EVENT,
}

# Use it
log_audit_event(
    event_type=MY_NEW_EVENT,
    metadata={"foo": "bar"}
)
```

## Best Practices

1. **Always log capability operations**: Use audit events for traceability
2. **Use type-safe event constants**: Import from `audit.py`
3. **Include rich metadata**: Add context for debugging and analysis
4. **Query by specific fields**: Use filters to find relevant events
5. **Handle orphan events**: Not all events need a task_id
6. **Validate presets**: Check dependency URLs and security policies
7. **Test dependency detection**: Verify auto-injection rules work

## Performance Considerations

1. **Registry is a singleton**: Only instantiated once
2. **Presets are immutable**: Safe to cache
3. **Audit writes are synchronous**: Consider batching for high volume
4. **JSON queries use SQLite functions**: Requires SQLite 3.38+
5. **FTS is available**: Use for text search on event payloads (future)

## Security Notes

1. **CSP rules are enforced**: Define strict policies for presets
2. **Sandbox attributes**: Limit iframe capabilities
3. **SRI hashes**: Add integrity checks for CDN resources (future)
4. **Admin tokens**: High-risk capabilities can require admin
5. **Audit trail**: All operations are logged for accountability

## Troubleshooting

### Common Issues

**Issue**: Foreign key constraint failed when logging audit event
- **Cause**: task_id doesn't exist in tasks table
- **Solution**: Use `task_id=None` for orphan events or create task first

**Issue**: Dependency not auto-injected
- **Cause**: Pattern not found in code
- **Solution**: Check `auto_inject_rules` and code content

**Issue**: Preset not found
- **Cause**: Invalid preset_id or capability_id
- **Solution**: Use `registry.list_all()` to see available options

## References

- Task Audits Schema: `agentos/store/schema_v06.sql`
- Snippets API: `agentos/webui/api/snippets.py`
- Preview API: `agentos/webui/api/preview.py`
- Task Models: `agentos/core/task/models.py`

## Changelog

### v1.0 (2026-01-28)
- ✅ Initial implementation
- ✅ Capability Registry with 3 capabilities
- ✅ Four P0 runtime presets
- ✅ Smart dependency detection
- ✅ Audit system with orphan event support
- ✅ Comprehensive test suite
- ✅ Full documentation
