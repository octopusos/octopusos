# Answers Module Quickstart

## Overview

The Answers module manages reusable Q&A packs that can be applied to intents and tasks through a Guardian-approved proposal workflow.

## Architecture

```
API Layer (answers.py)
    ↓
Service Layer (AnswersService)
    ↓
Repository Layer (AnswersRepo)
    ↓
Database (v23 schema: answer_packs, answer_pack_usage)
```

## Quick Start

### 1. Setup Database

```bash
# Apply v23 migration if not already done
sqlite3 agentos/store/registry.sqlite < agentos/store/migrations/v23_content_answers.sql
```

### 2. Create Answer Pack (Python)

```python
from pathlib import Path
from agentos.core.answers.service import AnswersService
from agentos.store.answers_store import AnswersRepo
from agentos.store import get_db_path

# Initialize service
repo = AnswersRepo(get_db_path())
service = AnswersService(repo)

# Create pack
pack = service.create_pack(
    name="Security Best Practices",
    items=[
        {
            "question": "How should secrets be stored?",
            "answer": "Use environment variables or vault services",
            "type": "security_answer"
        },
        {
            "question": "What is the authentication policy?",
            "answer": "OAuth2 with scope validation required",
            "type": "security_answer"
        }
    ],
    metadata={"category": "security", "version": "1.0"}
)

print(f"Created pack: {pack.id}")
```

### 3. Validate Pack

```python
# Validate structure and content
result = service.validate_pack(pack.id)

if result["valid"]:
    print("✅ Pack is valid")
else:
    print(f"❌ Errors: {result['errors']}")
    print(f"⚠️  Warnings: {result['warnings']}")
```

### 4. Generate Apply Proposal

```python
# IMPORTANT: This does NOT apply answers directly
# It creates a proposal that requires Guardian approval

proposal = service.create_apply_proposal(
    pack_id=pack.id,
    target_intent_id="intent_abc123"
)

print(f"Proposal ID: {proposal['proposal_id']}")
print(f"Status: {proposal['status']}")  # pending_review
print(f"Requires Guardian: {proposal['requires_guardian']}")  # True
print(f"Preview: {proposal['preview']}")
```

### 5. Link to Task/Intent

```python
# Create link between pack and task
link = service.link_to_entity(
    pack_id=pack.id,
    entity_type="task",
    entity_id="task_001"
)

print(f"Linked {link.entity_type} {link.entity_id}")
```

### 6. Query Related Entities

```python
# Find all tasks/intents that reference this pack
related = service.get_related_entities(pack.id)

for entity in related:
    print(f"{entity['type']}: {entity['id']} (linked at {entity['linked_at']})")
```

## API Usage

### List Packs

```bash
# List all packs
curl http://localhost:8080/api/answers/packs

# Filter by status
curl "http://localhost:8080/api/answers/packs?status=validated"

# Search by name
curl "http://localhost:8080/api/answers/packs?search=security"

# Pagination
curl "http://localhost:8080/api/answers/packs?limit=10&offset=20"
```

### Create Pack

```bash
curl -X POST http://localhost:8080/api/answers/packs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Configuration Q&A",
    "description": "Common configuration questions",
    "answers": [
      {
        "question": "What is the default timeout?",
        "answer": "30 seconds",
        "type": "config_answer"
      }
    ]
  }'
```

**Response**:
```json
{
  "ok": true,
  "data": {
    "id": "uuid-here",
    "name": "Configuration Q&A",
    "status": "draft",
    "created_at": "2026-01-29T..."
  }
}
```

### Get Pack Details

```bash
curl http://localhost:8080/api/answers/packs/{pack_id}
```

**Response**:
```json
{
  "ok": true,
  "data": {
    "id": "uuid-here",
    "name": "Configuration Q&A",
    "status": "validated",
    "items": [
      {"question": "...", "answer": "...", "type": "config_answer"}
    ],
    "metadata": {},
    "created_at": "2026-01-29T...",
    "updated_at": "2026-01-29T..."
  }
}
```

### Validate Pack

```bash
curl -X POST http://localhost:8080/api/answers/packs/{pack_id}/validate
```

**Response**:
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
    "target_intent_id": "intent_123",
    "target_type": "intent"
  }'
```

**Response**:
```json
{
  "ok": true,
  "data": {
    "proposal_id": "uuid-here",
    "pack_id": "uuid-here",
    "target_intent_id": "intent_123",
    "preview": {
      "pack_name": "Configuration Q&A",
      "items_count": 1,
      "items_sample": [...]
    },
    "status": "pending_review",
    "requires_guardian": true
  },
  "message": "Apply proposal created. Awaiting approval."
}
```

### Get Related Entities

```bash
curl http://localhost:8080/api/answers/packs/{pack_id}/related
```

**Response**:
```json
{
  "ok": true,
  "data": [
    {
      "type": "task",
      "id": "task_001",
      "linked_at": "2026-01-29T..."
    },
    {
      "type": "intent",
      "id": "intent_002",
      "linked_at": "2026-01-29T..."
    }
  ]
}
```

## Item Format

### Required Fields
- `question` (string): The question text
- `answer` (string): The answer text

### Optional Fields
- `type` (string): One of:
  - `security_answer` - Security-related Q&A
  - `config_answer` - Configuration Q&A
  - `general` - General Q&A (default)

### Example
```json
{
  "question": "How do I configure logging?",
  "answer": "Set LOGLEVEL environment variable to DEBUG, INFO, WARN, or ERROR",
  "type": "config_answer"
}
```

## Status Lifecycle

```
draft → validated → deprecated
                 ↘ frozen
```

### Status Definitions

- **draft**: Newly created, not yet validated
- **validated**: Passed validation, ready for use
- **deprecated**: Marked for retirement, but still usable
- **frozen**: Completely locked, cannot be modified or activated

### Status Transitions

```python
# Validate (draft → validated)
service.validate_pack(pack_id)  # Auto-updates if valid

# Deprecate
service.set_status(pack_id, "deprecated")

# Freeze
service.set_status(pack_id, "frozen")

# Frozen packs cannot change status
service.set_status(frozen_pack_id, "validated")  # ❌ Raises error
```

## Validation Rules

### Errors (Block Validation)
- Items must be non-empty list
- Each item must have `question` and `answer` fields
- Questions/answers cannot be empty strings

### Warnings (Allow Validation)
- Unknown item types (not security_answer, config_answer, general)
- Very short answers (< 10 characters)

### Example Validation Result
```python
{
    "valid": false,
    "errors": [
        "Item 0: question is empty",
        "Item 1: missing 'answer' field"
    ],
    "warnings": [
        "Item 2: unknown type 'custom_type'"
    ]
}
```

## Service API Reference

### AnswersService

```python
class AnswersService:
    """Answer pack management service"""

    def list_packs(
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[AnswerPack], int]:
        """List packs with filtering"""

    def get_pack(pack_id: str) -> AnswerPack:
        """Get pack (raises AnswerPackNotFoundError if not found)"""

    def create_pack(
        name: str,
        items: List[Dict[str, Any]],
        metadata: Optional[Dict] = None
    ) -> AnswerPack:
        """Create new pack (status=draft)"""

    def validate_pack(pack_id: str) -> Dict[str, Any]:
        """Validate pack (returns {valid, errors, warnings})"""

    def update_pack(
        pack_id: str,
        items: Optional[List[Dict]] = None,
        metadata: Optional[Dict] = None
    ) -> AnswerPack:
        """Update pack (only draft/validated can be updated)"""

    def set_status(pack_id: str, new_status: str) -> AnswerPack:
        """Change pack status (frozen packs cannot change)"""

    def create_apply_proposal(
        pack_id: str,
        target_intent_id: str,
        field_mappings: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Generate proposal (does NOT apply directly)"""

    def link_to_entity(
        pack_id: str,
        entity_type: str,
        entity_id: str
    ) -> AnswerPackLink:
        """Create link to task/intent"""

    def get_related_entities(pack_id: str) -> List[Dict[str, Any]]:
        """Get all linked tasks/intents"""
```

## Error Handling

### Service Exceptions

```python
from agentos.core.answers.service import (
    AnswerPackNotFoundError,      # 404
    AnswerPackValidationError,    # 400
    AnswersServiceError           # 500
)

try:
    pack = service.get_pack("nonexistent")
except AnswerPackNotFoundError as e:
    print(f"Not found: {e}")

try:
    service.create_pack("Test", [])  # Empty items
except AnswerPackValidationError as e:
    print(f"Validation error: {e}")
```

### API Error Responses

**404 Not Found**:
```json
{
  "detail": "Answer pack abc123 not found"
}
```

**400 Bad Request**:
```json
{
  "ok": false,
  "error": "Item 0 must have 'question' and 'answer' fields",
  "hint": "Check items structure: each must have question and answer"
}
```

**500 Internal Error**:
```json
{
  "ok": false,
  "error": "Database connection failed"
}
```

## Database Schema Quick Reference

### answer_packs
```
pack_id              TEXT PRIMARY KEY
pack_name            TEXT NOT NULL UNIQUE
description          TEXT
questions_answers    TEXT NOT NULL           -- JSON array
pack_size            INTEGER DEFAULT 0
validation_status    TEXT DEFAULT 'pending'  -- draft|validated|deprecated|frozen
validation_errors    TEXT                    -- JSON array
validation_at        TIMESTAMP
applied_count        INTEGER DEFAULT 0
last_applied_at      TIMESTAMP
author               TEXT
tags                 TEXT                    -- JSON array
metadata             TEXT                    -- JSON object
created_at           TIMESTAMP
updated_at           TIMESTAMP
```

### answer_pack_usage
```
usage_id        INTEGER PRIMARY KEY
pack_id         TEXT NOT NULL              -- FK to answer_packs
task_id         TEXT                       -- Optional task reference
intent          TEXT                       -- Optional intent reference
operation       TEXT NOT NULL              -- linked|proposal_generated|applied
questions_used  TEXT                       -- JSON array
metadata        TEXT
used_at         TIMESTAMP
```

## Testing

### Run Unit Tests
```bash
.venv/bin/python -m pytest tests/unit/core/answers/test_service.py -v
# Expected: 20 passed
```

### Manual Integration Test
```bash
.venv/bin/python test_answers_api_manual.py
# Tests service layer + API contracts
```

## Common Patterns

### Pattern 1: Create and Validate
```python
# Create pack
pack = service.create_pack("My Pack", [
    {"question": "Q1", "answer": "A1"}
])

# Validate
result = service.validate_pack(pack.id)

# Check status
updated_pack = service.get_pack(pack.id)
assert updated_pack.status == "validated"
```

### Pattern 2: Search and Filter
```python
# Find all validated security packs
packs, total = service.list_packs(
    status="validated",
    search="security"
)

for pack in packs:
    print(f"{pack.name}: {len(json.loads(pack.items_json))} items")
```

### Pattern 3: Proposal Workflow
```python
# 1. Create pack
pack = service.create_pack("Config Pack", items)

# 2. Validate
service.validate_pack(pack.id)

# 3. Generate proposal (does NOT apply)
proposal = service.create_apply_proposal(
    pack_id=pack.id,
    target_intent_id="intent_xyz"
)

# 4. Submit proposal to Guardian for review
# (Guardian approval workflow not shown)

# 5. After Guardian approval, apply answers
# (Application logic not shown)
```

### Pattern 4: Audit Trail
```python
# Link pack to task
service.link_to_entity(pack.id, "task", "task_001")

# Later: Find which tasks use this pack
related = service.get_related_entities(pack.id)

print(f"Pack {pack.name} is used by:")
for entity in related:
    print(f"  - {entity['type']} {entity['id']}")
```

## Troubleshooting

### Problem: "Answer pack not found"
```python
# Check pack exists
pack = service.get_pack(pack_id)
if not pack:
    print("Pack does not exist")
```

### Problem: "Cannot update frozen pack"
```python
# Check status before update
pack = service.get_pack(pack_id)
if pack.status == "frozen":
    print("Cannot update frozen pack")
    # Create new pack or unfreeze (not supported)
```

### Problem: Validation fails
```python
result = service.validate_pack(pack_id)
if not result["valid"]:
    print("Errors:")
    for error in result["errors"]:
        print(f"  - {error}")
```

### Problem: No related entities found
```python
related = service.get_related_entities(pack_id)
if not related:
    print("Pack has not been linked to any tasks/intents yet")
    # Use link_to_entity() to create links
```

## Best Practices

1. **Always validate before using**
   ```python
   result = service.validate_pack(pack.id)
   if result["valid"]:
       # Safe to use
   ```

2. **Use proposals, not direct apply**
   ```python
   # Good: Generate proposal
   proposal = service.create_apply_proposal(pack.id, intent.id)

   # Bad: Direct modification (not supported)
   # intent.answers = pack.items  # ❌
   ```

3. **Track usage with links**
   ```python
   # When using a pack, create link
   service.link_to_entity(pack.id, "task", task.id)
   ```

4. **Freeze packs when stable**
   ```python
   # After extensive testing
   service.set_status(pack.id, "frozen")
   # Now immutable - creates reliable baseline
   ```

5. **Search efficiently**
   ```python
   # Use filters to reduce results
   packs, total = service.list_packs(
       status="validated",
       search="security",
       limit=10
   )
   ```

## Next Steps

- Read [AGENT_DB_ANSWERS_DELIVERY.md](./AGENT_DB_ANSWERS_DELIVERY.md) for implementation details
- Check [v23 migration](./agentos/store/migrations/v23_content_answers.sql) for schema
- Review [unit tests](./tests/unit/core/answers/test_service.py) for examples
