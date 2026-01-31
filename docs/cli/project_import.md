# CLI Project Import Guide

**AgentOS Multi-Repository Project Import**

Complete guide to importing and managing multi-repository projects via CLI.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Command Reference](#command-reference)
- [Configuration File Format](#configuration-file-format)
- [Common Scenarios](#common-scenarios)
- [Advanced Usage](#advanced-usage)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### 3-Step Import (Fastest Path)

```bash
# 1. Configure authentication
agentos auth add --name github-ssh --type ssh_key --key-path ~/.ssh/id_rsa

# 2. Create configuration file
cat > my-app.yaml <<EOF
name: my-app
description: Full-stack application with separate backend and frontend
repos:
  - name: backend
    url: git@github.com:org/backend
    path: ./be
    role: code
    writable: true
    branch: main
    auth_profile: github-ssh
  - name: frontend
    url: git@github.com:org/frontend
    path: ./fe
    role: code
    writable: true
    branch: main
    auth_profile: github-ssh
EOF

# 3. Import project
agentos project import --from my-app.yaml
```

