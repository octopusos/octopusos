# Content/Answers/Auth API Quickstart Guide

Quick guide to get started with the new Content, Answers, and Auth Profile APIs.

---

## Prerequisites

1. **Apply Database Migration**

```bash
# Backup first
cp agentos/store/registry.sqlite agentos/store/registry.sqlite.backup

# Apply v23 migration
sqlite3 agentos/store/registry.sqlite < agentos/store/migrations/v23_content_answers.sql

# Verify
sqlite3 agentos/store/registry.sqlite "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'content%' OR name LIKE 'answer%' OR name LIKE 'admin%';"
```

Expected output:
```
admin_tokens
answer_pack_usage
answer_packs
content_registry
content_versions
```

2. **Start WebUI**

```bash
# From project root
uvicorn agentos.webui.app:app --port 8080 --reload
```

---

## Part 1: Admin Token Setup

Generate an admin token for protected operations:

```bash
python scripts/generate_admin_token.py --name "Dev Admin Token" --permissions "*"
```

Save the output token securely. You'll need it for write operations.

Example output:
```
Token ID: 01H8X...
RAW TOKEN: 1234567890abcdef...
```

---

## Part 2: Content API

### List Content

```bash
# List all content
curl http://localhost:8080/api/content

# Filter by type
curl http://localhost:8080/api/content?content_type=agent

# Filter by status
curl http://localhost:8080/api/content?status=active

# Pagination
curl http://localhost:8080/api/content?limit=10&offset=0
```

### Register New Content

```bash
curl -X POST http://localhost:8080/api/content/register \
  -H "X-Admin-Token: YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "content_type": "agent",
    "content_name": "my-test-agent",
    "description": "Test agent for demonstration",
    "author": "developer@example.com",
    "tags": ["test", "demo"],
    "metadata": {"version": "0.1.0"}
  }'
```

Response:
```json
{
  "content": {
    "content_id": "01H8X...",
    "content_type": "agent",
    "content_name": "my-test-agent",
    "status": "draft",
    ...
  }
}
```

### Activate Content

```bash
# Replace {content_id} with actual ID from previous step
curl -X PATCH http://localhost:8080/api/content/{content_id}/activate \
  -H "X-Admin-Token: YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "confirm": true
  }'
```

### Deprecate Content

```bash
curl -X PATCH http://localhost:8080/api/content/{content_id}/deprecate \
  -H "X-Admin-Token: YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "confirm": true
  }'
```

### List Versions

```bash
curl http://localhost:8080/api/content/{content_id}/versions?limit=10
```

---

## Part 3: Answers API

### List Answer Packs

```bash
# List all packs
curl http://localhost:8080/api/answers/packs

# Filter by status
curl http://localhost:8080/api/answers/packs?status=valid

# Search
curl http://localhost:8080/api/answers/packs?search=security
```

### Create Answer Pack

```bash
curl -X POST http://localhost:8080/api/answers/packs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Python Best Practices",
    "description": "Common Python coding questions",
    "answers": [
      {
        "question": "How to handle exceptions?",
        "answer": "Use try/except blocks with specific exception types"
      },
      {
        "question": "When to use list comprehension?",
        "answer": "For simple transformations; avoid for complex logic"
      }
    ]
  }'
```

Response:
```json
{
  "ok": true,
  "data": {
    "id": "pack_abc123",
    "name": "Python Best Practices",
    "status": "valid",
    ...
  }
}
```

### Validate Answer Pack

```bash
curl -X POST http://localhost:8080/api/answers/packs/{pack_id}/validate
```

Response:
```json
{
  "ok": true,
  "data": {
    "valid": true,
    "errors": [],
    "warnings": []
  }
}
```

### Generate Apply Proposal

```bash
curl -X POST http://localhost:8080/api/answers/packs/{pack_id}/apply-proposal \
  -H "Content-Type: application/json" \
  -d '{
    "target_intent_id": "intent-123",
    "target_type": "intent"
  }'
```

Response:
```json
{
  "ok": true,
  "data": {
    "id": "proposal_xyz789",
    "preview": {
      "pack_name": "Python Best Practices",
      "total_changes": 2
    },
    "status": "pending"
  }
}
```

### Get Related Tasks

```bash
curl http://localhost:8080/api/answers/packs/{pack_id}/related
```

---

## Part 4: Auth Profiles API

### List Auth Profiles

```bash
# List all profiles (credentials masked)
curl http://localhost:8080/api/auth/profiles

# Filter by type
curl http://localhost:8080/api/auth/profiles?profile_type=pat_token
```

Response:
```json
{
  "profiles": [
    {
      "profile_name": "github-personal",
      "profile_type": "pat_token",
      "token": "ghp_...******************",
      "token_scopes": ["repo", "workflow"],
      "validation_status": "valid"
    }
  ],
  "total": 1,
  "cli_hint": "To add/remove auth profiles, use CLI: agentos auth add/remove"
}
```

### Get Profile Details

```bash
curl http://localhost:8080/api/auth/profiles/github-personal
```

### Validate Profile Credentials

```bash
# For PAT tokens (test_url optional)
curl -X POST http://localhost:8080/api/auth/profiles/github-personal/validate

# For SSH keys (test_url required)
curl -X POST http://localhost:8080/api/auth/profiles/work-ssh/validate \
  -H "Content-Type: application/json" \
  -d '{
    "test_url": "git@github.com:org/repo.git"
  }'
```

Response:
```json
{
  "profile_id": "01H8Y...",
  "profile_name": "github-personal",
  "valid": true,
  "message": "Credentials validated successfully",
  "validated_at": "2026-01-29T10:00:00Z"
}
```

### Get Usage History

```bash
curl http://localhost:8080/api/auth/profiles/github-personal/usage?limit=20
```

---

## Part 5: Managing Auth Profiles (CLI Only)

Auth profiles can only be added/removed via CLI for security reasons.

### Add SSH Key Profile

```bash
agentos auth add \
  --name work-ssh \
  --type ssh_key \
  --key-path ~/.ssh/id_rsa
```

### Add GitHub PAT Profile

```bash
agentos auth add \
  --name github-personal \
  --type pat_token \
  --token ghp_YOUR_TOKEN_HERE \
  --provider github
```

### Add Netrc Profile

```bash
agentos auth add \
  --name gitlab-netrc \
  --type netrc \
  --machine gitlab.com \
  --login username \
  --password YOUR_PASSWORD
```

### List Profiles (CLI)

```bash
agentos auth list -v
```

### Validate Profile (CLI)

```bash
agentos auth validate github-personal
```

### Remove Profile

```bash
agentos auth remove github-personal --yes
```

---

## Part 6: Smoke Testing

Run the automated smoke tests:

```bash
# Make sure WebUI is running
python test_content_answers_auth_api.py
```

---

## Part 7: Audit Trail

All operations are logged to the audit table. Query audit logs:

```python
from agentos.core.audit import get_audit_events

# Get content operations
events = get_audit_events(event_type="CONTENT_ACTIVATED", limit=10)
for event in events:
    print(f"{event['event_type']}: {event['payload']}")

# Get answer pack operations
events = get_audit_events(event_type="ANSWER_PACK_CREATED", limit=10)
for event in events:
    print(f"{event['event_type']}: {event['payload']}")
```

Or via SQL:

```bash
sqlite3 agentos/store/registry.sqlite "
SELECT event_type, payload, created_at
FROM task_audits
WHERE event_type IN (
  'CONTENT_REGISTERED',
  'CONTENT_ACTIVATED',
  'CONTENT_DEPRECATED',
  'CONTENT_FROZEN',
  'ANSWER_PACK_CREATED',
  'ANSWER_PACK_PROPOSAL_GENERATED'
)
ORDER BY created_at DESC
LIMIT 10;
"
```

---

## Common Issues

### Issue: "Admin token required"

**Solution:** Make sure you're passing the admin token in the header:
```bash
-H "X-Admin-Token: YOUR_TOKEN_HERE"
```

### Issue: "Confirmation required"

**Solution:** Add `"confirm": true` to the request body for state-changing operations.

### Issue: "Table not found"

**Solution:** Apply the v23 migration:
```bash
sqlite3 agentos/store/registry.sqlite < agentos/store/migrations/v23_content_answers.sql
```

### Issue: "Invalid admin token"

**Solution:** Generate a new token:
```bash
python scripts/generate_admin_token.py --name "New Token" --permissions "*"
```

---

## API Documentation

Full API documentation available at:
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

---

## Next Steps

1. **Implement Tests:** Write unit/integration tests (see `AGENT_API_CONTENT_ANSWERS_AUTH_DELIVERY.md`)
2. **Create Frontend:** Build WebUI components for content/answers management
3. **Add Version Creation:** Implement content version upload endpoint
4. **Execute Proposals:** Implement answer pack proposal execution workflow

---

## Quick Reference

**Content API Base:** `/api/content`
**Answers API Base:** `/api/answers`
**Auth API Base:** `/api/auth/profiles`

**Admin Token Header:** `X-Admin-Token: <token>`
**Confirmation Parameter:** `{"confirm": true}`

**Permissions:**
- `*` - All permissions
- `content:register` - Register content
- `content:activate` - Activate content
- `content:deprecate` - Deprecate content
- `content:freeze` - Freeze content

---

**Created:** 2026-01-29
**Version:** 1.0
