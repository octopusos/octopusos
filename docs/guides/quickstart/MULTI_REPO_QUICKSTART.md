# Multi-Repository Project Quickstart

This guide helps you get started with multi-repository project management in AgentOS.

## Prerequisites

1. **Initialize AgentOS database**:
   ```bash
   agentos init
   ```

2. **Setup authentication** (for private repos):
   ```bash
   # Option 1: SSH Key
   agentos auth add --name github-ssh --type ssh_key --key-path ~/.ssh/id_rsa

   # Option 2: Personal Access Token
   agentos auth add --name github-pat --type pat_token --token <YOUR_TOKEN> --provider github
   ```

## Quick Start: 3 Ways to Import Projects

### Method 1: Config File (Recommended for 2+ repos)

1. **Create a project config file** (`my-project.yaml`):

```yaml
name: my-app
description: My multi-repo application

repos:
  - name: backend
    url: git@github.com:myorg/backend
    path: ./backend
    role: code
    writable: true
    auth_profile: github-ssh  # References the auth profile created above

  - name: frontend
    url: git@github.com:myorg/frontend
    path: ./frontend
    role: code
    writable: true
    auth_profile: github-ssh
```

2. **Import the project**:
```bash
agentos project import --from my-project.yaml
```

### Method 2: Inline CLI Options (Quick one-liner)

```bash
agentos project import my-app \
  --repo name=backend,url=git@github.com:org/backend,path=./be,auth_profile=github-ssh \
  --repo name=frontend,url=git@github.com:org/frontend,path=./fe,auth_profile=github-ssh \
  --yes
```

### Method 3: Interactive (Add repos one by one)

```bash
# 1. Create empty project
agentos project add ./workspace --id my-app

# 2. Add repositories
agentos project repos add my-app \
  --name backend \
  --url git@github.com:org/backend \
  --path ./backend \
  --auth-profile github-ssh

agentos project repos add my-app \
  --name frontend \
  --url git@github.com:org/frontend \
  --path ./frontend \
  --auth-profile github-ssh
```

## Common Use Cases

### Use Case 1: Microservices Project

```yaml
name: my-microservices
repos:
  - name: auth-service
    url: git@github.com:org/auth-service
    path: ./services/auth
  - name: api-gateway
    url: git@github.com:org/api-gateway
    path: ./services/gateway
  - name: user-service
    url: git@github.com:org/user-service
    path: ./services/users
```

### Use Case 2: Frontend + Backend + Shared Library

```yaml
name: fullstack-app
repos:
  - name: backend
    url: git@github.com:org/backend
    path: ./backend
    writable: true
  - name: frontend
    url: git@github.com:org/frontend
    path: ./frontend
    writable: true
  - name: shared-lib
    url: git@github.com:org/shared-lib
    path: ./lib
    writable: false  # Read-only dependency
```

### Use Case 3: Code + Docs + Infrastructure

```yaml
name: devops-project
repos:
  - name: application
    url: git@github.com:org/app
    path: ./app
    role: code
  - name: documentation
    url: git@github.com:org/docs
    path: ./docs
    role: docs
  - name: terraform
    url: git@github.com:org/infra
    path: ./infra
    role: infra
    writable: false
```

## Common Commands

### View Project Repositories

```bash
# List all repositories
agentos project repos list my-app

# Verbose mode (shows URLs, branches, auth profiles)
agentos project repos list my-app --verbose
```

### Validate Project

```bash
# Basic validation (workspace conflicts)
agentos project validate my-app

# Full validation (paths + auth + URLs)
agentos project validate my-app --all
```

### Manage Repositories

```bash
# Add a new repository
agentos project repos add my-app \
  --name docs \
  --path ./docs \
  --role docs

# Update repository URL
agentos project repos update my-app backend \
  --url git@github.com:org/new-backend

# Remove repository
agentos project repos remove my-app docs --yes
```

### List All Projects

```bash
agentos project list
```

## Configuration Reference

### Repository Roles

- `code` (default) - Code repository
- `docs` - Documentation repository
- `infra` - Infrastructure repository (Terraform, K8s, etc.)
- `mono-subdir` - Monorepo subdirectory

### Repository Fields

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `name` | ✅ Yes | - | Unique repository name |
| `url` | ❌ No | - | Remote Git URL |
| `path` | ❌ No | `.` | Workspace relative path |
| `role` | ❌ No | `code` | Repository role |
| `writable` | ❌ No | `true` | Read-write flag |
| `branch` | ❌ No | `main` | Default branch |
| `auth_profile` | ❌ No | - | Auth profile name |

### Workspace Path Rules

- Must be relative (e.g., `./backend`, `./services/auth`)
- Can use parent directories (e.g., `../shared`)
- Must be unique within project (no conflicts)
- Recommended: Use subdirectories for organization

## Troubleshooting

### Error: "Auth profile not found"

**Solution**: Create auth profile first:
```bash
agentos auth add --name github-ssh --type ssh_key --key-path ~/.ssh/id_rsa
```

### Error: "Duplicate repository names"

**Solution**: Each repository must have a unique name:
```yaml
repos:
  - name: backend-api  # ✅ Good
  - name: backend-web  # ✅ Good
  # - name: backend   # ❌ Would conflict
```

### Error: "Path conflict detected"

**Solution**: Each repository must use a different workspace path:
```yaml
repos:
  - name: backend
    path: ./be        # ✅ Good
  - name: frontend
    path: ./fe        # ✅ Good
  # - path: ./be     # ❌ Would conflict with backend
```

### Warning: "Write access required but not available"

**Solution**: Either:
1. Fix repository permissions on GitHub/GitLab
2. Update auth profile with correct credentials
3. Set `writable: false` if read-only is acceptable

### Error: "Unable to access remote URL"

**Solutions**:
1. Check network connectivity
2. Verify URL is correct
3. Ensure SSH key is loaded: `ssh-add -l`
4. Test manually: `git ls-remote <URL>`
5. Skip validation if needed: `--skip-validation`

## Examples Repository

See `examples/` directory for more configurations:
- `project_config_example.yaml` - Full-featured example
- `project_config_simple.yaml` - Minimal example
- `test_project_import.sh` - Test script

## Full Documentation

- [Complete CLI Reference](docs/cli/project_import.md)
- [Auth Profile Guide](docs/cli/auth.md)
- [Multi-Repo Architecture](docs/architecture/multi_repo.md)

## Next Steps

After importing your project:

1. **Validate configuration**:
   ```bash
   agentos project validate my-app --all
   ```

2. **View repository list**:
   ```bash
   agentos project repos list my-app --verbose
   ```

3. **Start working with tasks** (Phase 5.1):
   ```bash
   # Coming soon: Cross-repo task execution
   agentos task create --project my-app --repos backend,frontend
   ```

## Support

For issues or questions:
- Check [Troubleshooting](#troubleshooting) section
- Review [Full Documentation](docs/cli/project_import.md)
- Open an issue on GitHub

---

**Happy multi-repo coding!** 🚀
