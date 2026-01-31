# Projects CRUD API - Usage Examples

Quick reference guide for using the Projects CRUD API endpoints.

## Base URL

```
http://localhost:8000/api/projects
```

## Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/projects` | Create new project |
| GET | `/api/projects` | List projects (with filters) |
| GET | `/api/projects/{id}` | Get project details |
| PATCH | `/api/projects/{id}` | Update project |
| POST | `/api/projects/{id}/archive` | Archive project |
| DELETE | `/api/projects/{id}` | Delete project |

## Examples

### 1. Create Project

**Request**:
```bash
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Web App",
    "description": "Full-stack web application",
    "tags": ["python", "fastapi", "react"],
    "default_workdir": "/workspace/myapp",
    "settings": {
      "default_runner": "llama.cpp",
      "provider_policy": "prefer-local",
      "env_overrides": {
        "DEBUG": "true",
        "LOG_LEVEL": "info"
      },
      "risk_profile": {
        "allow_shell_write": true,
        "require_admin_token": false,
        "writable_paths": ["/tmp", "/workspace/myapp"]
      }
    }
  }'
```

**Response** (200 OK):
```json
{
  "project_id": "01HQZX2Y3K5M6N7P8Q9R0S1T2U",
  "name": "My Web App",
  "description": "Full-stack web application",
  "status": "active",
  "tags": ["python", "fastapi", "react"],
  "default_workdir": "/workspace/myapp",
  "settings": {
    "default_runner": "llama.cpp",
    "provider_policy": "prefer-local",
    "env_overrides": {
      "DEBUG": "true",
      "LOG_LEVEL": "info"
    },
    "risk_profile": {
      "allow_shell_write": true,
      "require_admin_token": false,
      "writable_paths": ["/tmp", "/workspace/myapp"]
    }
  },
  "created_at": "2026-01-29T10:30:00Z",
  "updated_at": "2026-01-29T10:30:00Z",
  "repos": [],
  "repos_count": 0
}
```

**Error Response** (400 Bad Request):
```json
{
  "detail": "Project with name 'My Web App' already exists"
}
```

### 2. List Projects

#### Basic List

**Request**:
```bash
curl http://localhost:8000/api/projects
```

**Response** (200 OK):
```json
{
  "projects": [
    {
      "project_id": "01HQZX2Y3K5M6N7P8Q9R0S1T2U",
      "name": "My Web App",
      "description": "Full-stack web application",
      "status": "active",
      "tags": ["python", "fastapi", "react"],
      "repo_count": 2,
      "created_at": "2026-01-29T10:30:00Z",
      "updated_at": "2026-01-29T10:30:00Z"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

#### Filter by Status

**Request**:
```bash
curl http://localhost:8000/api/projects?status=active
```

#### Search Projects

**Request**:
```bash
curl http://localhost:8000/api/projects?search=web
```

#### Pagination

**Request**:
```bash
curl http://localhost:8000/api/projects?limit=10&offset=20
```

#### Combined Filters

**Request**:
```bash
curl "http://localhost:8000/api/projects?status=active&search=api&limit=20&offset=0"
```

### 3. Get Project Details

**Request**:
```bash
curl http://localhost:8000/api/projects/01HQZX2Y3K5M6N7P8Q9R0S1T2U
```

**Response** (200 OK):
```json
{
  "project_id": "01HQZX2Y3K5M6N7P8Q9R0S1T2U",
  "name": "My Web App",
  "description": "Full-stack web application",
  "status": "active",
  "tags": ["python", "fastapi", "react"],
  "default_repo_id": null,
  "default_workdir": "/workspace/myapp",
  "settings": {
    "default_runner": "llama.cpp",
    "provider_policy": "prefer-local",
    "env_overrides": {
      "DEBUG": "true",
      "LOG_LEVEL": "info"
    },
    "risk_profile": {
      "allow_shell_write": true,
      "require_admin_token": false,
      "writable_paths": ["/tmp", "/workspace/myapp"]
    }
  },
  "created_at": "2026-01-29T10:30:00Z",
  "updated_at": "2026-01-29T10:30:00Z",
  "created_by": null,
  "repos": [
    {
      "repo_id": "frontend_repo",
      "name": "Frontend",
      "remote_url": "https://github.com/user/frontend.git",
      "role": "code",
      "is_writable": true,
      "workspace_relpath": "frontend",
      "default_branch": "main",
      "created_at": "2026-01-29T10:35:00Z",
      "updated_at": "2026-01-29T10:35:00Z"
    }
  ],
  "repos_count": 1,
  "recent_tasks_count": 5
}
```

**Error Response** (404 Not Found):
```json
{
  "detail": "Project not found"
}
```

### 4. Update Project

#### Update Single Field

**Request**:
```bash
curl -X PATCH http://localhost:8000/api/projects/01HQZX2Y3K5M6N7P8Q9R0S1T2U \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Updated description"
  }'
```

#### Update Multiple Fields

**Request**:
```bash
curl -X PATCH http://localhost:8000/api/projects/01HQZX2Y3K5M6N7P8Q9R0S1T2U \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Web App",
    "description": "New description",
    "tags": ["python", "fastapi", "react", "typescript"]
  }'
```

#### Update Settings

**Request**:
```bash
curl -X PATCH http://localhost:8000/api/projects/01HQZX2Y3K5M6N7P8Q9R0S1T2U \
  -H "Content-Type: application/json" \
  -d '{
    "settings": {
      "default_runner": "openai",
      "provider_policy": "cloud-only"
    }
  }'
```

**Response** (200 OK):
```json
{
  "project_id": "01HQZX2Y3K5M6N7P8Q9R0S1T2U",
  "name": "Updated Web App",
  "description": "New description",
  "status": "active",
  "tags": ["python", "fastapi", "react", "typescript"],
  "default_repo_id": null,
  "default_workdir": "/workspace/myapp",
  "settings": {
    "default_runner": "openai",
    "provider_policy": "cloud-only"
  },
  "created_at": "2026-01-29T10:30:00Z",
  "updated_at": "2026-01-29T11:45:00Z",
  "repos_count": 1
}
```

**Error Response** (400 Bad Request):
```json
{
  "detail": "Project with name 'Updated Web App' already exists"
}
```

### 5. Archive Project

**Request**:
```bash
curl -X POST http://localhost:8000/api/projects/01HQZX2Y3K5M6N7P8Q9R0S1T2U/archive
```

**Response** (200 OK):
```json
{
  "message": "Project '01HQZX2Y3K5M6N7P8Q9R0S1T2U' archived successfully",
  "project_id": "01HQZX2Y3K5M6N7P8Q9R0S1T2U",
  "status": "archived"
}
```

**Error Response** (400 Bad Request):
```json
{
  "detail": "Project is already archived"
}
```

**Error Response** (404 Not Found):
```json
{
  "detail": "Project not found"
}
```

### 6. Delete Project

#### Successful Deletion

**Request**:
```bash
curl -X DELETE http://localhost:8000/api/projects/01HQZX2Y3K5M6N7P8Q9R0S1T2U
```

**Response** (200 OK):
```json
{
  "message": "Project '01HQZX2Y3K5M6N7P8Q9R0S1T2U' deleted successfully",
  "project_id": "01HQZX2Y3K5M6N7P8Q9R0S1T2U"
}
```

#### Deletion Blocked (Has Tasks)

**Request**:
```bash
curl -X DELETE http://localhost:8000/api/projects/01HQZX2Y3K5M6N7P8Q9R0S1T2U
```

**Response** (400 Bad Request):
```json
{
  "detail": "Cannot delete project with existing tasks (5 tasks found). Archive instead."
}
```

## Python Client Examples

### Using requests library

```python
import requests

BASE_URL = "http://localhost:8000/api/projects"

# Create project
response = requests.post(BASE_URL, json={
    "name": "My Project",
    "description": "Test project",
    "tags": ["test"],
    "settings": {
        "default_runner": "llama.cpp"
    }
})
project = response.json()
project_id = project["project_id"]

# List projects
response = requests.get(BASE_URL, params={
    "status": "active",
    "limit": 10
})
projects = response.json()

# Get project
response = requests.get(f"{BASE_URL}/{project_id}")
project_detail = response.json()

# Update project
response = requests.patch(f"{BASE_URL}/{project_id}", json={
    "description": "Updated description"
})
updated_project = response.json()

# Archive project
response = requests.post(f"{BASE_URL}/{project_id}/archive")
result = response.json()

# Delete project
response = requests.delete(f"{BASE_URL}/{project_id}")
result = response.json()
```

### Using httpx (async)

```python
import httpx
import asyncio

async def main():
    async with httpx.AsyncClient() as client:
        # Create project
        response = await client.post(
            "http://localhost:8000/api/projects",
            json={
                "name": "Async Project",
                "tags": ["async", "python"]
            }
        )
        project = response.json()
        project_id = project["project_id"]

        # List projects
        response = await client.get(
            "http://localhost:8000/api/projects",
            params={"status": "active"}
        )
        projects = response.json()

        # Update project
        response = await client.patch(
            f"http://localhost:8000/api/projects/{project_id}",
            json={"description": "Updated async"}
        )

asyncio.run(main())
```

## Common Error Codes

| Status Code | Description | Common Causes |
|-------------|-------------|---------------|
| 200 | Success | Request completed successfully |
| 400 | Bad Request | Invalid input, duplicate name, validation error |
| 404 | Not Found | Project does not exist |
| 500 | Internal Server Error | Database error, unexpected error |

## Validation Rules

### Project Name
- **Required**: Yes
- **Type**: String
- **Constraints**: Must be unique across all projects
- **Example**: "My Web App"

### Description
- **Required**: No
- **Type**: String
- **Constraints**: None
- **Example**: "Full-stack web application"

### Status
- **Required**: No (defaults to "active")
- **Type**: String
- **Allowed Values**: "active", "archived", "deleted"
- **Constraints**: Enforced by database triggers

### Tags
- **Required**: No (defaults to [])
- **Type**: Array of strings
- **Constraints**: Must be valid JSON array
- **Example**: ["python", "web", "api"]

### Settings
- **Required**: No (defaults to {})
- **Type**: Object
- **Constraints**: Must match ProjectSettings schema
- **Fields**:
  - `default_runner`: String (optional)
  - `provider_policy`: String (optional)
  - `env_overrides`: Object (optional)
  - `risk_profile`: Object (optional)

### Default Workdir
- **Required**: No
- **Type**: String
- **Constraints**: Valid path, no null bytes
- **Example**: "/workspace/myapp"

## Best Practices

1. **Always validate before creating**: Check if a project with the same name exists
2. **Use partial updates**: Only send fields you want to change in PATCH requests
3. **Archive before delete**: Consider archiving instead of deleting projects with history
4. **Search efficiently**: Use status filters to reduce result sets before searching
5. **Paginate large lists**: Use limit/offset to handle large project collections
6. **Handle errors gracefully**: Check for 400/404 responses and handle appropriately
7. **Use settings validation**: Validate settings client-side before submission

## Testing Endpoints

You can test the API using:
1. **curl** (as shown in examples above)
2. **Postman** or **Insomnia** (import the OpenAPI schema)
3. **Swagger UI** at http://localhost:8000/docs
4. **ReDoc** at http://localhost:8000/redoc
5. **Python requests** or **httpx** libraries

## Related Documentation

- [PROJECTS_CRUD_API_REPORT.md](./PROJECTS_CRUD_API_REPORT.md) - Full implementation report
- [agentos/schemas/project.py](./agentos/schemas/project.py) - Project data models
- [agentos/webui/api/projects.py](./agentos/webui/api/projects.py) - API implementation
