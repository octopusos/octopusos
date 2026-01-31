# Task #12: app.py Integration Instructions

## Quick Integration Guide

To integrate the Mode Monitoring API into the WebUI, follow these steps:

### Step 1: Add Import Statement

In `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/app.py`, locate the import section around line 43:

```python
# Import API routers
from agentos.webui.api import health, sessions, tasks, events, skills, memory, config, logs, providers, selfcheck, context, runtime, providers_control, support, secrets, sessions_runtime, providers_lifecycle, providers_instances, providers_models, knowledge, history, share, preview, snippets, governance, guardians, lead, projects, task_dependencies, governance_dashboard, guardian, content, answers, auth, execution, dryrun, intent, auth_profiles, task_templates, task_events, evidence
```

**Add** `mode_monitoring` to the import list:

```python
# Import API routers
from agentos.webui.api import health, sessions, tasks, events, skills, memory, config, logs, providers, selfcheck, context, runtime, providers_control, support, secrets, sessions_runtime, providers_lifecycle, providers_instances, providers_models, knowledge, history, share, preview, snippets, governance, guardians, lead, projects, task_dependencies, governance_dashboard, guardian, content, answers, auth, execution, dryrun, intent, auth_profiles, task_templates, task_events, evidence, mode_monitoring
```

### Step 2: Register Router

Around line 257 (after `app.include_router(auth_profiles.router, tags=["auth_profiles"])`), add:

```python
app.include_router(mode_monitoring.router, prefix="/api/mode", tags=["mode"])
```

### Step 3: Verify

Start the server and test the endpoints:

```bash
# Start the WebUI
python -m agentos.webui.app

# Test the endpoints
curl http://localhost:8000/api/mode/stats
curl http://localhost:8000/api/mode/alerts
```

### Complete Integration Code

Here's the complete code to add:

```python
# In the import section (around line 43):
from agentos.webui.api import ..., mode_monitoring

# In the router registration section (around line 257):
app.include_router(mode_monitoring.router, prefix="/api/mode", tags=["mode"])
```

That's it! The API is now integrated and ready to use.

---

## Alternative: Using register_routes()

If you prefer, you can use the `register_routes()` function:

```python
from agentos.webui.api import mode_monitoring

# Call register_routes instead of include_router
mode_monitoring.register_routes(app)
```

Both approaches work identically.

---

## Verification Commands

After integration, verify all endpoints work:

```bash
# Get stats
curl http://localhost:8000/api/mode/stats

# Get alerts (empty initially)
curl http://localhost:8000/api/mode/alerts

# Generate a test alert (requires mode system to be active)
# Then check again:
curl http://localhost:8000/api/mode/alerts?limit=5

# Clear alerts
curl -X POST http://localhost:8000/api/mode/alerts/clear
```

---

## OpenAPI Documentation

Once integrated, the API will automatically appear in FastAPI's interactive docs:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

Look for the "mode" tag in the API documentation.
