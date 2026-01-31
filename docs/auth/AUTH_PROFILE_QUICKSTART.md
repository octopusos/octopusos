# Auth Profile Quickstart Guide

> Phase 3.1 - Git Credential Management for Multi-Repo Projects

## Overview

Auth Profiles provide secure credential management for Git operations in AgentOS. This system enables:

- **Secure Storage**: Credentials encrypted at rest using AES-256-GCM
- **Multiple Auth Types**: SSH keys, Personal Access Tokens (PAT), and netrc
- **Environment Fallback**: Automatic detection of tokens from environment variables
- **Audit Trail**: All credential usage logged for security compliance
- **Validation**: Test credentials before use

## Quick Start

### 1. Install Dependencies

```bash
pip install cryptography python-ulid
```

### 2. Run Database Migration

```bash
agentos migrate
# This will apply v0.19 migration for auth_profiles table
```

### 3. Add Your First Auth Profile

#### Option A: GitHub Personal Access Token

```bash
# Generate token at: https://github.com/settings/tokens
agentos auth add \
  --name github-personal \
  --type pat_token \
  --token ghp_YOUR_TOKEN_HERE \
  --provider github
```

#### Option B: SSH Key

```bash
agentos auth add \
  --name work-ssh \
  --type ssh_key \
  --key-path ~/.ssh/id_rsa
```

#### Option C: GitLab with Netrc

```bash
agentos auth add \
  --name gitlab-work \
  --type netrc \
  --machine gitlab.com \
  --login your-username \
  --password YOUR_PASSWORD
```

### 4. List Your Profiles

```bash
agentos auth list

# Output:
# Profile Name         Type         Provider     Status      Last Validated
# =====================================================================================
# github-personal      pat_token    github       valid       2024-01-28 10:30
# work-ssh             ssh_key      -            unknown     Never
```

### 5. Validate Credentials

```bash
# For PAT tokens (auto-detects provider URL)
agentos auth validate github-personal

# For SSH keys (requires test URL)
agentos auth validate work-ssh --url git@github.com:user/repo.git
```

### 6. Use Auth Profile in Multi-Repo Projects

When creating a multi-repo project, reference your auth profile:

```bash
# TODO: This will be implemented in Phase 2.1
agentos project add-repo \
  --project my-project \
  --name backend \
  --url git@github.com:org/backend.git \
  --auth github-personal
```

## CLI Reference

### `agentos auth add`

Add a new auth profile.

**SSH Key Example:**
```bash
agentos auth add \
  --name my-ssh \
  --type ssh_key \
  --key-path ~/.ssh/id_ed25519 \
  --passphrase  # Will prompt securely
```

**GitHub PAT Example:**
```bash
agentos auth add \
  --name github-work \
  --type pat_token \
  --token ghp_... \
  --provider github
```

**Netrc Example:**
```bash
agentos auth add \
  --name bitbucket-work \
  --type netrc \
  --machine bitbucket.org \
  --login username \
  --password  # Will prompt securely
```

### `agentos auth list`

List all configured auth profiles.

```bash
agentos auth list           # Summary view
agentos auth list -v        # Verbose (shows SSH paths, machines)
```

### `agentos auth show`

Show detailed information about a profile.

```bash
agentos auth show github-personal
```

### `agentos auth validate`

Test credentials against a Git service.

```bash
agentos auth validate github-personal
agentos auth validate work-ssh --url git@gitlab.com:org/repo.git
```

### `agentos auth remove`

Delete an auth profile.

```bash
agentos auth remove github-personal
agentos auth remove work-ssh --yes  # Skip confirmation
```

## Python API Usage

### Basic Usage

```python
from agentos.core.git.credentials import CredentialsManager, AuthProfileType, TokenProvider
from agentos.core.git.client import GitClientWithAuth

# Initialize manager
manager = CredentialsManager()

# Create a profile programmatically
profile = manager.create_profile(
    profile_name="api-github",
    profile_type=AuthProfileType.PAT_TOKEN,
    token="ghp_token_here",
    token_provider=TokenProvider.GITHUB,
)

# Get a profile
profile = manager.get_profile("api-github")
print(f"Token: {profile.token}")  # Decrypted automatically
```

### Clone with Authentication

```python
from pathlib import Path
from agentos.core.git.client import GitClientWithAuth

client = GitClientWithAuth()

# Clone private repo using auth profile
git_client = client.clone(
    remote_url="https://github.com/org/private-repo.git",
    dest_path=Path("/tmp/private-repo"),
    auth_profile="github-personal",
)

# Or use environment variable fallback (no profile needed)
git_client = client.clone(
    remote_url="https://github.com/org/repo.git",
    dest_path=Path("/tmp/repo"),
    auth_profile=None,  # Will try GITHUB_TOKEN env var
)
```

### Pull/Push with Authentication

```python
from pathlib import Path
from agentos.core.git.client import GitClientWithAuth

client = GitClientWithAuth()

# Pull updates
client.pull(
    repo_path=Path("/tmp/repo"),
    auth_profile="github-personal",
)

# Push changes
client.push(
    repo_path=Path("/tmp/repo"),
    auth_profile="github-personal",
)
```

### Validate Credentials

```python
from agentos.core.git.client import GitClientWithAuth

client = GitClientWithAuth()

is_valid = client.validate_credentials(
    auth_profile="github-personal",
    test_url="https://github.com",  # Optional for PAT profiles
)

if is_valid:
    print("✅ Credentials are valid")
else:
    print("❌ Credentials validation failed")
```

## Environment Variable Fallback

If no auth profile is specified, the system automatically checks for tokens in environment variables:

| Provider   | Environment Variables                |
|------------|--------------------------------------|
| GitHub     | `GITHUB_TOKEN`, `GH_TOKEN`           |
| GitLab     | `GITLAB_TOKEN`, `CI_JOB_TOKEN`       |
| Bitbucket  | `BITBUCKET_TOKEN`                    |
| Gitea      | `GITEA_TOKEN`                        |

Example:

```bash
export GITHUB_TOKEN=ghp_your_token_here
agentos project clone https://github.com/org/repo.git
# Token automatically detected and used
```

## Security Considerations

### Encryption

- **Algorithm**: AES-256-GCM (via Fernet)
- **Key Storage**: Master key stored in `~/.agentos/credentials.key`
- **Key Permissions**: Automatically set to 0600 (owner read/write only)
- **Per-Field Encryption**: Each sensitive field encrypted independently

### Best Practices

1. **Use SSH Keys for Production**: More secure than tokens, supports key rotation
2. **Limit Token Scopes**: Create tokens with minimal required permissions
3. **Rotate Credentials Regularly**: Update tokens every 90 days
4. **Use Different Profiles per Project**: Avoid sharing credentials across projects
5. **Enable 2FA**: Always enable two-factor authentication on Git services

### Audit Trail

All credential usage is logged:

```sql
SELECT * FROM auth_profile_usage
WHERE profile_id = 'profile-id'
ORDER BY used_at DESC;
```

View audit logs:

```python
from agentos.store import get_db

conn = get_db()
cursor = conn.cursor()

logs = cursor.execute("""
    SELECT operation, status, error_message, used_at
    FROM auth_profile_usage
    WHERE profile_id = ?
    ORDER BY used_at DESC
    LIMIT 10
""", (profile_id,)).fetchall()

for log in logs:
    print(f"{log['used_at']}: {log['operation']} - {log['status']}")
```

## Troubleshooting

### Issue: "Auth profile not found"

**Solution**: List profiles to verify name:

```bash
agentos auth list
```

### Issue: "SSH key not found"

**Solution**: Verify key path:

```bash
ls -la ~/.ssh/id_rsa
agentos auth show your-ssh-profile
```

### Issue: "Credentials validation failed"

**Possible Causes**:
1. Token expired or revoked
2. Insufficient token permissions
3. SSH key not added to Git service
4. Network connectivity issues

**Debugging**:

```bash
# Check validation status
agentos auth show your-profile

# Test manually
git ls-remote https://github.com/user/repo.git

# For SSH keys
ssh -T git@github.com
```

### Issue: "Encryption key missing"

**Solution**: The master key is auto-generated on first use. If missing:

```bash
rm ~/.agentos/credentials.key
# Add a new profile (will regenerate key)
agentos auth add --name test --type pat_token --token test --provider github
```

## Migration from Existing Systems

### From Environment Variables

```bash
# Before: export GITHUB_TOKEN=ghp_...
# After:
agentos auth add \
  --name github-env \
  --type pat_token \
  --token $GITHUB_TOKEN \
  --provider github

# Remove from environment
unset GITHUB_TOKEN
```

### From .netrc

```bash
# Before: ~/.netrc contains credentials
# After:
agentos auth add \
  --name github-netrc \
  --type netrc \
  --machine github.com \
  --login your-username \
  --password your-password

# Keep .netrc as backup
mv ~/.netrc ~/.netrc.backup
```

## Database Schema

Auth profiles are stored in three tables:

### `auth_profiles`

Stores credential configurations (encrypted).

```sql
CREATE TABLE auth_profiles (
    profile_id TEXT PRIMARY KEY,
    profile_name TEXT NOT NULL UNIQUE,
    profile_type TEXT NOT NULL,  -- ssh_key | pat_token | netrc
    ssh_key_path TEXT,
    ssh_passphrase_encrypted TEXT,
    token_encrypted TEXT,
    token_provider TEXT,  -- github | gitlab | bitbucket | gitea
    token_scopes TEXT,
    netrc_machine TEXT,
    netrc_login TEXT,
    netrc_password_encrypted TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    last_validated_at TIMESTAMP,
    validation_status TEXT,  -- unknown | valid | invalid | expired
    validation_message TEXT,
    metadata TEXT
);
```

### `auth_profile_usage`

Audit log for credential usage.

```sql
CREATE TABLE auth_profile_usage (
    usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT NOT NULL,
    repo_id TEXT,
    operation TEXT NOT NULL,  -- clone | pull | push | validate
    status TEXT NOT NULL,  -- success | failure
    error_message TEXT,
    used_at TIMESTAMP,
    metadata TEXT
);
```

### `encryption_keys`

Manages encryption keys (future use for key rotation).

```sql
CREATE TABLE encryption_keys (
    key_id TEXT PRIMARY KEY,
    key_type TEXT NOT NULL,  -- master | derived
    key_encrypted BLOB NOT NULL,
    salt BLOB,
    algorithm TEXT NOT NULL,
    created_at TIMESTAMP,
    rotated_at TIMESTAMP,
    metadata TEXT
);
```

## Roadmap

### Phase 3.1 (Current) ✅

- [x] Auth profile data models
- [x] Secure credential storage (encryption)
- [x] CLI commands (add/list/remove/validate/show)
- [x] SSH key authentication
- [x] PAT token authentication
- [x] Environment variable fallback
- [x] Credential validation
- [x] Usage audit logging

### Phase 3.2 (Next)

- [ ] Advanced validation (test clone/push permissions)
- [ ] Credential expiration detection
- [ ] Token refresh for OAuth providers
- [ ] Multi-repo integration (bind auth to repos)
- [ ] Credential rotation workflows

### Wave 2 (Future)

- [ ] OAuth 2.0 flow support (GitHub App, GitLab OAuth)
- [ ] Credential sharing between team members (encrypted vault)
- [ ] Integration with system keyrings (macOS Keychain, Windows Credential Manager)
- [ ] Hardware token support (YubiKey, etc.)

## Support

For issues or questions:

1. Check logs: `~/.agentos/logs/`
2. Verify database: `sqlite3 store/registry.sqlite "SELECT * FROM auth_profiles"`
3. GitHub Issues: [agentos/issues](https://github.com/agentos/issues)

## Examples

### Example 1: Multi-Repo Project with Different Auth

```bash
# Add profiles for different services
agentos auth add --name github-frontend --type pat_token --token ghp_... --provider github
agentos auth add --name gitlab-backend --type ssh_key --key-path ~/.ssh/gitlab_rsa

# Bind to repos (Phase 2.1)
agentos project add-repo --name frontend --url https://github.com/org/frontend --auth github-frontend
agentos project add-repo --name backend --url git@gitlab.com:org/backend.git --auth gitlab-backend
```

### Example 2: Temporary Test Credentials

```bash
# Add test credential
agentos auth add --name test-github --type pat_token --token ghp_test --provider github

# Use for one-time clone
agentos project clone https://github.com/test/repo --auth test-github

# Remove after use
agentos auth remove test-github --yes
```

### Example 3: SSH Key with Passphrase

```bash
# Generate SSH key with passphrase
ssh-keygen -t ed25519 -C "work@example.com" -f ~/.ssh/work_ed25519

# Add to AgentOS (will prompt for passphrase)
agentos auth add \
  --name work-github \
  --type ssh_key \
  --key-path ~/.ssh/work_ed25519 \
  --passphrase

# Add public key to GitHub
cat ~/.ssh/work_ed25519.pub | pbcopy
# Paste at: https://github.com/settings/keys

# Validate
agentos auth validate work-github --url git@github.com:org/repo.git
```

---

**Last Updated**: 2024-01-28
**Version**: 0.19.0
**Status**: Phase 3.1 Complete
