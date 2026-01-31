# Task Template Quick Reference

**Quick guide for using the Task Template API**

## API Endpoints

### Create Template
```http
POST /api/task-templates
Content-Type: application/json

{
  "name": "Template Name",
  "title_template": "Task Title Template",
  "description": "Optional description",
  "created_by_default": "user@example.com",
  "metadata_template": {
    "priority": "high",
    "type": "feature"
  }
}
```

**Response:** `200 OK` with TaskTemplate object

---

### List Templates
```http
GET /api/task-templates?limit=50&offset=0&order_by=created_at
```

**Query Parameters:**
- `limit` (optional): Max results (1-200, default: 50)
- `offset` (optional): Pagination offset (default: 0)
- `order_by` (optional): Sort field (created_at, name, use_count, updated_at)

**Response:** `200 OK` with array of TemplateSummary

---

### Get Template
```http
GET /api/task-templates/{template_id}
```

**Response:** `200 OK` with TaskTemplate object or `404 Not Found`

---

### Update Template
```http
PUT /api/task-templates/{template_id}
Content-Type: application/json

{
  "name": "Updated Name",
  "description": "Updated description"
}
```

**Note:** Only include fields you want to update. All fields are optional.

**Response:** `200 OK` with updated TaskTemplate or `404 Not Found`

---

### Delete Template
```http
DELETE /api/task-templates/{template_id}
```

**Response:** `200 OK` with success message or `404 Not Found`

---

### Create Task from Template
```http
POST /api/task-templates/{template_id}/tasks
Content-Type: application/json

{
  "title_override": "Specific Task Title",
  "created_by_override": "user@example.com",
  "metadata_override": {
    "priority": "critical"
  }
}
```

**Note:** All fields are optional. Omit to use template defaults.

**Response:** `200 OK` with created Task object or `404 Not Found`

---

## Python Service Usage

### Import
```python
from agentos.core.task.template_service import TemplateService
```

### Create Template
```python
service = TemplateService()

template = service.create_template(
    name="Bug Fix Template",
    title_template="Fix bug in {component}",
    description="Standard bug fix workflow",
    created_by_default="developer@example.com",
    metadata_template={"priority": "medium", "type": "bug"},
    created_by="admin"
)

print(f"Created: {template.template_id}")
```

### List Templates
```python
# Get all templates
templates = service.list_templates()

# With pagination
templates = service.list_templates(limit=10, offset=0)

# Sorted by popularity
templates = service.list_templates(order_by="use_count")

# Sorted by name
templates = service.list_templates(order_by="name")
```

### Get Template
```python
template = service.get_template("template_id")
if template:
    print(f"Name: {template.name}")
    print(f"Use count: {template.use_count}")
```

### Update Template
```python
updated = service.update_template(
    template_id="template_id",
    name="New Name",
    description="New description"
)
```

### Delete Template
```python
success = service.delete_template("template_id")
print(f"Deleted: {success}")
```

### Create Task from Template
```python
task = service.create_task_from_template(
    template_id="template_id",
    title_override="Fix authentication bug",
    created_by_override="user@example.com",
    metadata_override={"priority": "high"}
)

print(f"Task created: {task.task_id}")
print(f"Status: {task.status}")
print(f"Metadata: {task.metadata}")
```

---

## Data Models

### TaskTemplate
```python
@dataclass
class TaskTemplate:
    template_id: str                      # ULID format
    name: str                             # 1-100 characters
    title_template: str                   # Task title template
    description: Optional[str]            # Optional description
    created_by_default: Optional[str]     # Default creator
    metadata_template: Dict[str, Any]     # Metadata template
    created_at: Optional[str]             # ISO 8601 timestamp
    updated_at: Optional[str]             # ISO 8601 timestamp
    created_by: Optional[str]             # Template creator
    use_count: int                        # Usage count
```

### TemplateSummary (List View)
```python
{
    "template_id": "01HQZX...",
    "name": "Template Name",
    "description": "Optional description",
    "title_template": "Task Title",
    "use_count": 15,
    "created_at": "2026-01-29T07:00:00.000Z",
    "updated_at": "2026-01-29T07:00:00.000Z"
}
```

---

## Validation Rules

### Template Name
- ✅ Required
- ✅ Length: 1-100 characters
- ✅ Trimmed whitespace
- ❌ Empty or whitespace-only

### Title Template
- ✅ Required
- ✅ Non-empty after trimming
- ❌ Empty or whitespace-only

### Metadata Template
- ✅ Optional (can be null)
- ✅ Must be valid JSON object
- ❌ Arrays or primitives

### Use Count
- ✅ Non-negative integer
- ✅ Auto-incremented on task creation

---

## Metadata Merging Example

**Template Metadata:**
```json
{
  "priority": "medium",
  "type": "bug",
  "estimated_hours": 4
}
```

**Override Metadata:**
```json
{
  "priority": "critical",
  "assignee": "john@example.com"
}
```

**Result (Merged):**
```json
{
  "priority": "critical",           // Overridden
  "type": "bug",                    // From template
  "estimated_hours": 4,             // From template
  "assignee": "john@example.com",   // New field
  "created_from_template": {        // Auto-added
    "template_id": "01HQZX...",
    "template_name": "Bug Fix Template"
  },
  "execution_context": {            // Auto-added by task service
    "created_method": "task_service",
    "created_at": "2026-01-29T..."
  }
}
```

---

## Error Codes

| Status | Reason | Example |
|--------|--------|---------|
| 200 | Success | Template created |
| 400 | Validation error | Name too long |
| 404 | Not found | Template doesn't exist |
| 422 | Invalid input | Missing required field |
| 500 | Server error | Database error |

---

## Common Use Cases

### 1. Standard Bug Fix Template
```python
template = service.create_template(
    name="Bug Fix",
    title_template="Fix: [Brief description]",
    metadata_template={
        "type": "bug",
        "priority": "medium",
        "workflow": ["investigate", "fix", "test", "review"]
    }
)
```

### 2. Feature Development Template
```python
template = service.create_template(
    name="Feature Development",
    title_template="Feature: [Feature name]",
    metadata_template={
        "type": "feature",
        "priority": "low",
        "workflow": ["design", "implement", "test", "document"]
    }
)
```

### 3. Emergency Hotfix Template
```python
template = service.create_template(
    name="Emergency Hotfix",
    title_template="HOTFIX: [Critical issue]",
    metadata_template={
        "type": "hotfix",
        "priority": "critical",
        "requires_immediate_attention": True,
        "workflow": ["investigate", "fix", "test", "deploy"]
    }
)
```

---

## Testing

### Run Tests
```bash
# Run all template tests
.venv/bin/python3 -m pytest tests/unit/webui/api/test_template_api.py -v

# Run specific test
.venv/bin/python3 -m pytest tests/unit/webui/api/test_template_api.py::TestTemplateAPI::test_create_template_success -v

# Run with coverage
.venv/bin/python3 -m pytest tests/unit/webui/api/test_template_api.py --cov=agentos.core.task.template_service --cov=agentos.webui.api.task_templates
```

---

## Database

### Migration
```bash
# Apply migration (automatic on startup)
python3 -c "from agentos.store import ensure_migrations, get_db_path; ensure_migrations(get_db_path())"
```

### Direct SQL Queries
```sql
-- List all templates
SELECT template_id, name, use_count FROM task_templates ORDER BY use_count DESC;

-- Get template by name
SELECT * FROM task_templates WHERE name = 'Bug Fix Template';

-- Count templates
SELECT COUNT(*) FROM task_templates;

-- Most popular templates
SELECT name, use_count FROM task_templates ORDER BY use_count DESC LIMIT 5;
```

---

## Tips & Best Practices

### 1. Template Naming
- ✅ Use descriptive names: "Bug Fix Template", "Feature Development"
- ✅ Keep names short but meaningful
- ❌ Avoid generic names: "Template 1", "My Template"

### 2. Metadata Design
- ✅ Use consistent key names across templates
- ✅ Document expected metadata fields
- ✅ Keep metadata flat when possible
- ❌ Avoid deep nesting

### 3. Template Organization
- ✅ Create templates for common workflows
- ✅ Review and update templates regularly
- ✅ Delete unused templates
- ❌ Don't create too many similar templates

### 4. Task Creation
- ✅ Override only what you need to change
- ✅ Use descriptive task titles
- ✅ Provide metadata overrides for context
- ❌ Don't override everything (defeats the purpose)

---

## Troubleshooting

### Template not found (404)
- Check template_id is correct
- Verify template wasn't deleted
- List all templates to confirm existence

### Validation error (400/422)
- Check name length (1-100 chars)
- Verify title_template is not empty
- Ensure metadata_template is valid JSON object

### Task creation fails
- Verify template exists
- Check TaskService is available
- Review logs for detailed error

---

**Last Updated:** 2026-01-29
**Version:** 1.0
**Status:** Production Ready
