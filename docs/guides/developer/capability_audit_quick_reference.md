# Capability Registry & Audit System - Quick Reference

Quick reference guide for developers integrating with the Capability Registry and Audit System.

## Installation

No installation needed - these are core modules. Just import:

```python
from agentos.core import get_capability_registry, log_audit_event
```

## Common Operations

### 1. Get a Runtime Preset

```python
from agentos.core import get_capability_registry

registry = get_capability_registry()
preset = registry.get_preset("preview", "three-webgl-umd")
```

### 2. Detect Required Dependencies

```python
user_code = "const controls = new THREE.OrbitControls(camera);"
deps = registry.detect_required_deps(preset, user_code)
# Returns: [three-core, three-orbit-controls]
```

### 3. Log an Audit Event

```python
from agentos.core import log_audit_event, SNIPPET_CREATED

log_audit_event(
    event_type=SNIPPET_CREATED,
    snippet_id="snippet-123",
    metadata={"language": "javascript", "size": 150}
)
```

### 4. Query Audit Events

```python
from agentos.core import get_audit_events

events = get_audit_events(snippet_id="snippet-123")
for event in events:
    print(f"{event['event_type']}: {event['payload']}")
```

## Available Presets

| Preset ID | Description | Use Case |
|-----------|-------------|----------|
| `html-basic` | Pure HTML/CSS/JS | Simple static pages |
| `three-webgl-umd` | Three.js r169 | 3D graphics, WebGL |
| `chartjs-umd` | Chart.js | Data visualization, charts |
| `d3-umd` | D3.js | Complex data visualizations |

## Audit Event Types

### Snippet Events
- `SNIPPET_CREATED` - New snippet created
- `SNIPPET_UPDATED` - Snippet metadata updated
- `SNIPPET_DELETED` - Snippet deleted
- `SNIPPET_USED_IN_TASK` - Snippet used in task

### Preview Events
- `PREVIEW_SESSION_CREATED` - Preview session created
- `PREVIEW_SESSION_OPENED` - User opened preview
- `PREVIEW_SESSION_EXPIRED` - Session expired
- `PREVIEW_RUNTIME_SELECTED` - Runtime preset selected
- `PREVIEW_DEP_INJECTED` - Dependency auto-injected

### Task Events
- `TASK_MATERIALIZED_FROM_SNIPPET` - Task created from snippet

## Three.js Preset Auto-Injection

The `three-webgl-umd` preset automatically injects dependencies based on code content:

| Pattern in Code | Auto-Injected Dependency |
|-----------------|--------------------------|
| `FontLoader` | `three-fontloader` |
| `OrbitControls` | `three-orbit-controls` |
| `GLTFLoader` | `three-gltf-loader` |
| `TextGeometry` | `three-text-geometry` |

**Example**:
```javascript
// This code:
const controls = new THREE.OrbitControls(camera);

// Automatically injects:
// - three-core (always loaded)
// - three-orbit-controls (detected)
```

## Integration Patterns

### Pattern 1: Preview API Integration

```python
from agentos.core import (
    get_capability_registry,
    log_audit_event,
    PREVIEW_SESSION_CREATED,
    PREVIEW_DEP_INJECTED,
)

def create_preview(code, preset_id="three-webgl-umd"):
    # Get preset and detect dependencies
    registry = get_capability_registry()
    preset = registry.get_preset("preview", preset_id)
    deps = registry.detect_required_deps(preset, code)

    # Create session
    session_id = generate_session_id()

    # Log session creation
    log_audit_event(
        event_type=PREVIEW_SESSION_CREATED,
        preview_id=session_id,
        metadata={
            "preset": preset_id,
            "deps_count": len(deps),
        }
    )

    # Log each auto-injected dependency
    for dep in deps:
        if dep.condition:  # Only optional deps
            log_audit_event(
                event_type=PREVIEW_DEP_INJECTED,
                preview_id=session_id,
                metadata={"dep_id": dep.id}
            )

    return session_id, deps
```

### Pattern 2: Snippet API Integration

```python
from agentos.core import log_audit_event, SNIPPET_CREATED

def create_snippet(code, language, metadata=None):
    snippet_id = generate_snippet_id()

    # Save to database
    save_to_db(snippet_id, code, language)

    # Log audit event
    log_audit_event(
        event_type=SNIPPET_CREATED,
        snippet_id=snippet_id,
        metadata={
            "language": language,
            "size": len(code),
            **(metadata or {})
        }
    )

    return snippet_id
```

### Pattern 3: Task Materialization

```python
from agentos.core import (
    log_audit_event,
    TASK_MATERIALIZED_FROM_SNIPPET,
)

def materialize_task(snippet_id, auto_run=False):
    # Create task
    task_id = create_task_from_snippet(snippet_id)

    # Log materialization
    log_audit_event(
        event_type=TASK_MATERIALIZED_FROM_SNIPPET,
        task_id=task_id,
        snippet_id=snippet_id,
        metadata={"auto_run": auto_run}
    )

    return task_id
```

## Tips & Best Practices

1. **Always log operations** - Use audit events for traceability
2. **Use orphan events** - Set `task_id=None` for events not tied to tasks
3. **Rich metadata** - Include context in metadata dict
4. **Import constants** - Use event type constants, not strings
5. **Query efficiently** - Use specific filters to narrow results
6. **Check dependencies** - Always run `detect_required_deps` before preview
7. **Handle errors** - Audit log failures don't break core functionality

## Testing

Quick test to verify setup:

```python
from agentos.core import get_capability_registry

registry = get_capability_registry()
print(f"✓ Registry loaded with {len(registry.list_all())} capabilities")

preset = registry.get_preset("preview", "three-webgl-umd")
print(f"✓ Three.js preset loaded with {len(preset.dependencies)} dependencies")
```

## Common Issues

### Q: Foreign key constraint failed when logging audit?
**A**: Either provide a valid `task_id` or use `task_id=None` for orphan events.

### Q: Dependencies not auto-injecting?
**A**: Check the code contains the exact keyword (e.g., "OrbitControls").

### Q: Preset not found?
**A**: Use `registry.list_all()` to see available capabilities and presets.

## More Information

- **Full Documentation**: `docs/capability_registry_and_audit.md`
- **Examples**: `examples/capability_audit_usage.py`
- **Tests**: `test_capability_registry_audit.py`

## Support

For questions or issues:
1. Check the full documentation
2. Run the examples
3. Review the test suite
4. Examine the source code with inline comments
