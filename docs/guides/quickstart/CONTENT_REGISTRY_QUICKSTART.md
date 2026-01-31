# Content Registry View - Quick Start Guide

## What is Content Registry?

Content Registry manages the lifecycle of reusable AI components:
- **Agents**: Autonomous task executors (e.g., Code Review Agent)
- **Workflows**: Multi-step orchestration patterns (e.g., CI/CD Pipeline)
- **Skills**: Specialized capabilities (e.g., NLP Processing)
- **Tools**: Utility integrations (e.g., Git, Docker, Database)

## Key Features

### 📋 Content Management
- View all registered content in card or table layout
- Filter by type (agents/workflows/skills/tools)
- Filter by status (active/deprecated/frozen)
- Search by name or tags
- Pagination for large datasets

### 🔍 Version Control
- Track all versions of each content item
- View version history with release notes
- Compare versions side-by-side (diff viewer)
- Rollback to previous versions

### 🔐 Admin Operations (Managed Mode Only)
- Register new content with metadata
- Activate specific versions
- Deprecate outdated content
- Freeze content for stability
- All actions logged for audit

### 🏠 Local Mode (Read-Only)
- View all content without admin privileges
- Explore metadata and version history
- Write operations disabled with clear notice

## Quick Start

### 1. Access the View

```bash
# Start AgentOS WebUI
cd /Users/pangge/PycharmProjects/AgentOS
python -m agentos.webui.app

# Open browser
open http://localhost:8080

# Navigate to: Governance → Content Registry
```

### 2. Browse Content

**Card View** (Default):
- Visual cards with status badges
- Quick metadata preview
- Tags and version display
- Action buttons at bottom

**Table View**:
- Compact tabular format
- Sortable columns
- More items visible at once
- Quick action icons

**Filters**:
- Type: All / Agents / Workflows / Skills / Tools
- Status: All / Active / Deprecated / Frozen
- Search: Type to filter by name or tags

### 3. View Details

Click "View Details" on any item to see:
- Full metadata (name, author, description)
- Current version and status
- Creation and update timestamps
- Tags and categories
- Dependencies (what it requires)
- Complete version history

### 4. Compare Versions

In the detail modal:
1. Find the version you want to compare
2. Click "View Diff with [previous version]"
3. See side-by-side comparison of configurations

### 5. Admin Actions (Managed Mode)

**Register New Content**:
```
1. Click "Register New" button (top right)
2. Fill in the form:
   - Type: agent/workflow/skill/tool
   - Name: Descriptive name
   - Version: e.g., 1.0.0
   - Description: What it does
   - Tags: Comma-separated keywords
   - Config File: Upload JSON/YAML
3. Click "Register"
4. Confirmation shown + audit log created
```

**Activate Version**:
```
1. View content details
2. Find version in history
3. Click "Activate"
4. Confirm in dialog
5. Version becomes active
```

**Deprecate Content**:
```
1. View content details
2. Click "Deprecate" button
3. Confirm in dialog (shows impact)
4. Content marked as deprecated
5. Still accessible but flagged
```

**Freeze Content**:
```
1. View content details
2. Click "Freeze" button
3. Confirm in dialog
4. Content frozen for stability
5. No modifications allowed until unfrozen
```

## Status Meanings

| Status | Badge Color | Meaning |
|--------|------------|---------|
| **Active** | 🟢 Green | Current production version, recommended for use |
| **Deprecated** | 🟠 Orange | Legacy version, replaced by newer content, still works but not recommended |
| **Frozen** | 🔵 Blue | Locked for stability, no changes allowed, guaranteed stability |

## Content Types

### 🤖 Agents
Autonomous executors that can:
- Analyze code and provide reviews
- Monitor systems and alert on issues
- Generate documentation
- Automate testing

**Example**: Code Review Agent v2.1.0

### 🔄 Workflows
Multi-step orchestration:
- CI/CD pipelines
- Data processing flows
- Approval chains
- Deployment sequences

**Example**: CI/CD Pipeline v1.3.0

### 🧠 Skills
Specialized capabilities:
- Natural language processing
- Image recognition
- Code analysis
- Data transformation

**Example**: NLP Processing v3.0.0

### 🔧 Tools
Utility integrations:
- Git operations
- Database connectors
- API clients
- File processors

**Example**: Database Connector v1.0.0

## API Usage (for Developers)

### List Content

```bash
curl http://localhost:8080/api/content/registry?type=agent&status=active
```

Response:
```json
{
  "items": [
    {
      "id": "agent-001",
      "name": "Code Review Agent",
      "type": "agent",
      "status": "active",
      "version": "2.1.0",
      "description": "Automated code review",
      "tags": ["coding", "review"],
      "dependencies": ["tool-git"]
    }
  ],
  "total": 1
}
```

### Get Details

```bash
curl http://localhost:8080/api/content/registry/agent-001
```

### Register Content (Admin)

```bash
curl -X POST http://localhost:8080/api/content/registry \
  -H "X-Admin-Token: your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Agent",
    "type": "agent",
    "version": "1.0.0",
    "description": "Does something useful",
    "tags": ["automation"],
    "config": {}
  }'
```

### Update Status (Admin)

```bash
curl -X PUT http://localhost:8080/api/content/registry/agent-001/status \
  -H "X-Admin-Token: your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "deprecate",
    "reason": "Replaced by v2.0"
  }'
```

## Mock Data (Development)

The view includes mock data for testing:

1. **Code Review Agent** (Active)
   - Type: agent
   - Version: 2.1.0
   - Tags: coding, review, quality
   - Dependencies: tool-git, skill-code-analysis

2. **CI/CD Pipeline** (Active)
   - Type: workflow
   - Version: 1.3.0
   - Tags: cicd, automation, deployment
   - Dependencies: agent-build, agent-test, tool-docker

3. **NLP Processing** (Frozen)
   - Type: skill
   - Version: 3.0.0
   - Tags: nlp, text, ai
   - Dependencies: tool-transformers

4. **Database Connector** (Deprecated)
   - Type: tool
   - Version: 1.0.0
   - Tags: database, legacy
   - No dependencies

## Troubleshooting

### View Not Loading

**Symptom**: Blank page or error message

**Solutions**:
1. Check browser console for errors:
   ```
   F12 → Console tab
   ```

2. Verify ContentRegistryView.js is loaded:
   ```javascript
   console.log(window.ContentRegistryView);
   // Should show: [class ContentRegistryView]
   ```

3. Check API endpoint:
   ```bash
   curl http://localhost:8080/api/content/registry
   ```

### Write Buttons Hidden

**Symptom**: Can't see Register/Activate/Deprecate buttons

**Cause**: Running in local mode or not admin

**Solutions**:
1. Check mode:
   ```bash
   curl http://localhost:8080/api/content/mode
   ```

2. If local mode, this is expected behavior (read-only)

3. If managed mode, verify admin token:
   ```bash
   curl http://localhost:8080/api/governance/admin/validate \
     -H "X-Admin-Token: your-token"
   ```

### Data Not Persisting

**Symptom**: Changes lost after refresh

**Cause**: Using mock data (expected in development)

**Solution**: Backend implementation required:
1. Implement database schema (see CONTENT_REGISTRY_VIEW_DELIVERY.md)
2. Replace mock data with DB queries in content.py
3. Add admin token system
4. Connect audit logging

## Next Steps

1. **For Users**:
   - Explore existing content
   - Use filters and search
   - Review version histories
   - Understand dependencies

2. **For Admins**:
   - Register new content
   - Manage content lifecycle
   - Review audit logs
   - Monitor usage patterns

3. **For Developers**:
   - Implement backend persistence
   - Add admin token system
   - Connect audit logging
   - Implement version diff algorithm
   - Add usage analytics

## Best Practices

### Content Registration
- Use semantic versioning (major.minor.patch)
- Write clear descriptions
- Add relevant tags
- Document dependencies
- Include usage examples in config

### Version Management
- Increment major version for breaking changes
- Increment minor version for new features
- Increment patch version for bug fixes
- Write detailed release notes
- Test before activating

### Lifecycle Management
- Deprecate before removing
- Allow grace period for migration
- Freeze stable versions for critical systems
- Monitor usage before deprecating
- Document migration paths

### Audit Compliance
- Always provide reason for changes
- Review audit logs regularly
- Track who made what changes
- Monitor for suspicious activity
- Keep audit retention policy

## Support

For issues or questions:
1. Check console for error messages
2. Review CONTENT_REGISTRY_VIEW_DELIVERY.md
3. Inspect network tab for API failures
4. Check backend logs for server errors

## References

- **Delivery Doc**: CONTENT_REGISTRY_VIEW_DELIVERY.md
- **Test Page**: test_content_registry.html
- **API Module**: agentos/webui/api/content.py
- **View Module**: agentos/webui/static/js/views/ContentRegistryView.js
- **Styles**: agentos/webui/static/css/content-registry.css

---

**Last Updated**: 2026-01-29
**Version**: 1.0.0
**Status**: Production-Ready (Frontend)
