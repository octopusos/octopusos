# Skills Administration Guide

This guide explains how to manage Skills using the Admin Token protection system.

## Table of Contents

- [Admin Token Configuration](#admin-token-configuration)
- [CLI Usage](#cli-usage)
- [API Usage](#api-usage)
- [Security Best Practices](#security-best-practices)
- [Troubleshooting](#troubleshooting)

---

## Admin Token Configuration

### What is Admin Token?

Admin Token is a security mechanism that protects high-risk operations:
- **Importing skills** (local or GitHub)
- **Enabling skills** (making them available for runtime)
- **Disabling skills** (preventing their use)

### Setting Up Admin Token

#### Method 1: Environment Variable (Recommended)

```bash
export AGENTOS_ADMIN_TOKEN="your-secure-token-here"
```

Add this to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.) to persist across sessions.

#### Method 2: Configuration File

Create or edit `~/.agentos/config.yaml`:

```yaml
admin_token: your-secure-token-here
```

### Generating a Secure Token

**Using OpenSSL:**
```bash
openssl rand -hex 32
```

**Using Python:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**Using the provided script:**
```bash
python scripts/generate_admin_token.py
```

Example output:
```
Generated Admin Token:
a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
```

---

## CLI Usage

### Listing Skills (No Token Required)

List all skills:
```bash
agentos skill list
```

Filter by status:
```bash
agentos skill list --status enabled
agentos skill list --status disabled
agentos skill list --status imported_disabled
agentos skill list --status all
```

Example output:
```
Status               Skill ID                       Version         Description
----------------------------------------------------------------------------------------------------
✓ enabled            example.skill                  1.0.0           Example skill for testing
○ disabled           old.skill                      0.9.0           Deprecated skill
⊗ imported_disabled  new.skill                      1.1.0           Recently imported skill

Total: 3 skills
```

### Getting Skill Details (No Token Required)

```bash
agentos skill info <skill_id>
```

Example:
```bash
agentos skill info example.skill
```

Output:
```
============================================================
Skill: example.skill
============================================================
Version:      1.0.0
Status:       enabled
Repo Hash:    abc123...
Imported At:  1706745600000
Enabled At:   1706746200000

Manifest:
  Name:        Example Skill
  Author:      Example Author
  Description: A skill that demonstrates capabilities

  Capabilities:
    Class: action
    Tags:  demo, example

  Requires:
    Phase: execution
    Permissions:
      Network:  api.example.com
      Actions:  write_state
```

### Importing Skills (Requires Token)

#### Import from Local Path

```bash
agentos skill import /path/to/skill
```

#### Import from GitHub

```bash
# Basic import (uses default branch)
agentos skill import github:owner/repo

# Specify branch/tag
agentos skill import github:owner/repo#main
agentos skill import github:owner/repo#v1.0.0

# Specify subdirectory
agentos skill import github:owner/repo#main:skills/example
```

**Note:** Import operations require Admin Token via environment variable (`AGENTOS_ADMIN_TOKEN`).

### Enabling Skills (Requires Token)

#### Using Environment Variable Token

```bash
export AGENTOS_ADMIN_TOKEN="your-token"
agentos skill enable my.skill
```

#### Using Command-Line Token

```bash
agentos skill enable my.skill --token your-token
```

Success output:
```
✅ Skill enabled: my.skill
```

### Disabling Skills (Requires Token)

```bash
agentos skill disable my.skill --token your-token
```

Or with environment variable:
```bash
export AGENTOS_ADMIN_TOKEN="your-token"
agentos skill disable my.skill
```

Success output:
```
✅ Skill disabled: my.skill
```

---

## API Usage

### Authentication

All protected API endpoints require Admin Token in the `Authorization` header:

```
Authorization: Bearer your-admin-token-here
```

### Listing Skills (Public)

**Request:**
```bash
curl http://localhost:8000/api/skills
```

**With Status Filter:**
```bash
curl http://localhost:8000/api/skills?status=enabled
```

**Response:**
```json
{
  "ok": true,
  "data": [
    {
      "skill_id": "example.skill",
      "name": "Example Skill",
      "version": "1.0.0",
      "status": "enabled",
      "source_type": "local",
      "source_ref": "/path/to/skill",
      "manifest_json": {...},
      "created_at": 1706745600000,
      "updated_at": 1706746200000
    }
  ]
}
```

### Getting Skill Details (Public)

**Request:**
```bash
curl http://localhost:8000/api/skills/example.skill
```

**Response:**
```json
{
  "ok": true,
  "data": {
    "skill_id": "example.skill",
    "name": "Example Skill",
    "version": "1.0.0",
    "status": "enabled",
    "manifest_json": {
      "skill_id": "example.skill",
      "name": "Example Skill",
      "version": "1.0.0",
      "capabilities": {...},
      "requires": {...}
    }
  }
}
```

### Importing Skill (Protected)

#### Import from Local Path

**Request:**
```bash
curl -X POST http://localhost:8000/api/skills/import \
  -H "Authorization: Bearer your-admin-token" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "local",
    "path": "/path/to/skill"
  }'
```

#### Import from GitHub

**Request:**
```bash
curl -X POST http://localhost:8000/api/skills/import \
  -H "Authorization: Bearer your-admin-token" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "github",
    "owner": "owner",
    "repo": "repo",
    "ref": "main",
    "subdir": "skills/example"
  }'
```

**Success Response (200):**
```json
{
  "skill_id": "example.skill",
  "status": "imported_disabled",
  "message": "Successfully imported skill from GitHub: owner/repo"
}
```

**Error Response (401):**
```json
{
  "detail": "Authentication required"
}
```

### Enabling Skill (Protected)

**Request:**
```bash
curl -X POST http://localhost:8000/api/skills/example.skill/enable \
  -H "Authorization: Bearer your-admin-token"
```

**Success Response (200):**
```json
{
  "skill_id": "example.skill",
  "status": "enabled",
  "message": "Skill enabled successfully"
}
```

**Error Response (404):**
```json
{
  "detail": "Skill not found: example.skill"
}
```

### Disabling Skill (Protected)

**Request:**
```bash
curl -X POST http://localhost:8000/api/skills/example.skill/disable \
  -H "Authorization: Bearer your-admin-token"
```

**Success Response (200):**
```json
{
  "skill_id": "example.skill",
  "status": "disabled",
  "message": "Skill disabled successfully"
}
```

---

## Security Best Practices

### Token Management

1. **Use Strong Tokens**
   - Minimum 32 bytes (64 hex characters)
   - Use cryptographically secure random generation
   - Example: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6...`

2. **Never Hardcode Tokens**
   ```bash
   # ❌ Bad
   AGENTOS_ADMIN_TOKEN="my-token" agentos skill enable my.skill

   # ✅ Good
   export AGENTOS_ADMIN_TOKEN="$(cat ~/.agentos/.token)"
   agentos skill enable my.skill
   ```

3. **Store Tokens Securely**
   ```bash
   # Create secure token file
   openssl rand -hex 32 > ~/.agentos/.token
   chmod 600 ~/.agentos/.token

   # Load token when needed
   export AGENTOS_ADMIN_TOKEN="$(cat ~/.agentos/.token)"
   ```

4. **Rotate Tokens Regularly**
   - Generate new token monthly
   - Update in all environments
   - Revoke old token

5. **Limit Token Exposure**
   - Don't log tokens
   - Don't commit tokens to git
   - Use `.gitignore` for token files
   - Clear history after accidental exposure

### Access Control

1. **Principle of Least Privilege**
   - Only share admin token with trusted administrators
   - Use separate tokens for different environments (dev/staging/prod)

2. **Audit Operations**
   - Monitor skill enable/disable operations
   - Review import logs regularly
   - Track who has admin token access

3. **Environment Separation**
   ```bash
   # Development
   export AGENTOS_ADMIN_TOKEN="${DEV_ADMIN_TOKEN}"

   # Production
   export AGENTOS_ADMIN_TOKEN="${PROD_ADMIN_TOKEN}"
   ```

### Network Security

1. **Use HTTPS**
   - Never send admin token over unencrypted HTTP
   - Enable TLS for production deployments

2. **API Rate Limiting**
   - Configure rate limits for protected endpoints
   - Monitor for brute-force attempts

---

## Troubleshooting

### Common Issues

#### 1. "Admin token required" Error

**Problem:**
```bash
❌ Admin token required. Provide via --token or AGENTOS_ADMIN_TOKEN env var.
```

**Solution:**
```bash
# Option 1: Set environment variable
export AGENTOS_ADMIN_TOKEN="your-token"
agentos skill enable my.skill

# Option 2: Use --token flag
agentos skill enable my.skill --token your-token
```

#### 2. "Invalid admin token" Error

**Problem:**
```bash
❌ Invalid admin token
```

**Causes:**
- Token is incorrect
- Token has been rotated
- Environment variable not set correctly

**Solution:**
```bash
# Verify token is set
echo $AGENTOS_ADMIN_TOKEN

# Regenerate and set new token
openssl rand -hex 32
export AGENTOS_ADMIN_TOKEN="new-token"
```

#### 3. "401 Unauthorized" from API

**Problem:**
```json
{"detail": "Authentication required"}
```

**Solution:**
```bash
# Ensure Authorization header is correct
curl -X POST http://localhost:8000/api/skills/my.skill/enable \
  -H "Authorization: Bearer your-admin-token-here"
```

#### 4. "Skill not found" Error

**Problem:**
```bash
❌ Skill not found: my.skill
```

**Solution:**
```bash
# List all skills to verify ID
agentos skill list

# Check exact skill ID (case-sensitive)
agentos skill info exact.skill.id
```

#### 5. Token Works in CLI but not API

**Problem:** CLI commands work but API returns 401.

**Cause:** Different token formats.

**Solution:**
```bash
# API expects Bearer token in header
curl -H "Authorization: Bearer ${AGENTOS_ADMIN_TOKEN}" \
  http://localhost:8000/api/skills/my.skill/enable
```

### Debugging

#### Enable Debug Logging

```bash
export AGENTOS_LOG_LEVEL=DEBUG
agentos skill enable my.skill
```

#### Verify Token Validation

```bash
# Check if token validation is working
python3 << 'EOF'
from agentos.core.capabilities.admin_token import validate_admin_token
import os

token = os.environ.get('AGENTOS_ADMIN_TOKEN')
print(f"Token set: {bool(token)}")
print(f"Token valid: {validate_admin_token(token)}")
EOF
```

#### Test API Connectivity

```bash
# Test public endpoint (no token)
curl -v http://localhost:8000/api/skills

# Test protected endpoint (with token)
curl -v -X POST http://localhost:8000/api/skills/test/enable \
  -H "Authorization: Bearer ${AGENTOS_ADMIN_TOKEN}"
```

---

## Examples

### Complete Workflow Example

```bash
# 1. Generate and set admin token
export AGENTOS_ADMIN_TOKEN="$(openssl rand -hex 32)"
echo "Token: $AGENTOS_ADMIN_TOKEN"

# 2. Import skill from GitHub
agentos skill import github:example/skill#v1.0.0

# 3. List imported skills
agentos skill list --status imported_disabled

# 4. Get skill details
agentos skill info example.skill

# 5. Enable skill
agentos skill enable example.skill

# 6. Verify skill is enabled
agentos skill list --status enabled

# 7. Later, disable if needed
agentos skill disable example.skill
```

### Automated Script Example

```bash
#!/bin/bash
# deploy-skill.sh - Automated skill deployment

set -e

SKILL_REPO="$1"
SKILL_ID="$2"

if [ -z "$AGENTOS_ADMIN_TOKEN" ]; then
    echo "Error: AGENTOS_ADMIN_TOKEN not set"
    exit 1
fi

echo "Importing skill from ${SKILL_REPO}..."
agentos skill import "github:${SKILL_REPO}"

echo "Enabling skill ${SKILL_ID}..."
agentos skill enable "${SKILL_ID}"

echo "Deployment complete!"
agentos skill info "${SKILL_ID}"
```

Usage:
```bash
chmod +x deploy-skill.sh
export AGENTOS_ADMIN_TOKEN="your-token"
./deploy-skill.sh "owner/repo" "skill.id"
```

---

## API Reference Summary

| Endpoint | Method | Auth Required | Description |
|----------|--------|---------------|-------------|
| `/api/skills` | GET | No | List all skills |
| `/api/skills/{id}` | GET | No | Get skill details |
| `/api/skills/import` | POST | **Yes** | Import skill |
| `/api/skills/{id}/enable` | POST | **Yes** | Enable skill |
| `/api/skills/{id}/disable` | POST | **Yes** | Disable skill |

---

## Related Documentation

- [Skill Manifest Reference](./SKILL_MANIFEST_REFERENCE.md)
- [Skill Development Guide](./SKILL_DEVELOPMENT_GUIDE.md)
- [Security Architecture](./SECURITY_ARCHITECTURE.md)
- [API Documentation](./API_DOCUMENTATION.md)

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/agentos/agentos/issues
- Documentation: https://docs.agentos.dev
- Community: https://community.agentos.dev

---

**Last Updated:** 2026-02-01
**Version:** 1.0.0
