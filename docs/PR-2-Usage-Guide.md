# PR-2: WebUI Governance Views - Usage Guide

## Quick Start

The 4 new governance views provide read-only visibility into the AgentOS Governance system.

## Accessing the Views

### Via Browser Console (for testing)

```javascript
// Governance Overview
window.loadView('governance')

// Quota Monitoring
window.loadView('governance-quotas')

// Trust Tier Topology
window.loadView('governance-trust-tiers')

// Provenance Details (requires invocation ID)
window.loadView('governance-provenance', 'your-invocation-id')
```

### Via Navigation (once added to sidebar)

Add the following to the sidebar navigation in `index.html`:

```html
<!-- Governance Section -->
<div>
    <h2 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Governance</h2>

    <a href="#" class="nav-item" data-view="governance">
        <span class="material-icons md-18">security</span>
        <span>Overview</span>
    </a>

    <a href="#" class="nav-item" data-view="governance-quotas">
        <span class="material-icons md-18">speed</span>
        <span>Quotas</span>
    </a>

    <a href="#" class="nav-item" data-view="governance-trust-tiers">
        <span class="material-icons md-18">layers</span>
        <span>Trust Tiers</span>
    </a>
</div>
```

## View Features

### 1. Governance Overview (`/governance`)

**What you see:**
- Total capabilities count
- Distribution by trust tier (T0, T1, T2, T3)
- Quota warnings and denials
- Recent governance events

**Actions:**
- Click on trust tier cards → Navigate to Trust Tier View
- Click on "View Details" → Navigate to Quota View
- Click on events → View audit details

**Use cases:**
- Quick health check of governance system
- Identify quota issues at a glance
- Monitor recent policy violations

### 2. Quota Monitoring (`/governance-quotas`)

**What you see:**
- Table of all capabilities with quota status
- Usage percentage with color-coded progress bars
- Trust tier badges
- Last triggered timestamps

**Filters:**
- Trust Tier: All / T0 / T1 / T2 / T3
- Status: All / OK / Warning / Denied

**Color codes:**
- 🟢 Green (< 80%): Healthy usage
- 🟠 Orange (80-100%): Warning - approaching limit
- 🔴 Red (> 100%): Denied - over quota

**Important:** Display shows read-only status with reminder:
> "Quotas can only be modified via CLI with admin token. WebUI is read-only."

**Use cases:**
- Monitor quota usage across all capabilities
- Identify capabilities approaching limits
- Track quota violations

### 3. Trust Tier Topology (`/governance-trust-tiers`)

**What you see:**
- Hierarchical view of all trust tiers
- Risk level and default quota for each tier
- Admin token requirements
- Expandable list of capabilities per tier

**Tier Information:**

| Tier | Name | Risk | Default Quota | Admin Token |
|------|------|------|---------------|-------------|
| T0 | Local Extension | LOW | 1000/min | No |
| T1 | Local MCP | MEDIUM | 500/min | No |
| T2 | Remote MCP | HIGH | 100/min | For side-effects |
| T3 | Cloud MCP | CRITICAL | 10/min | Always |

**Actions:**
- Click tier header → Expand/collapse capability list
- Click capability → View capability details
- "Expand All" / "Collapse All" buttons

**Use cases:**
- Understand trust tier policies
- View which capabilities belong to each tier
- Verify admin token requirements

### 4. Provenance Details (`/governance-provenance/:id`)

**What you see:**
- Complete audit trail for a specific tool invocation
- Tool and capability information
- Execution environment (host, PID, container)
- Audit chain with gate decisions

**Entry points:**
- From audit logs (click on invocation ID)
- From tool invocation records
- From history view (click on provenance link)

**Information displayed:**
- Invocation ID and timestamp
- Tool ID and capability ID
- Source and trust tier
- Execution environment details
- Complete audit event chain

**Use cases:**
- Investigate specific tool invocations
- Verify execution environment
- Audit gate decision trail
- Compliance and security audits

## Common Workflows

### Workflow 1: Investigate Quota Warning

1. Open **Governance Overview**
2. See "2 warnings" in Quota Status
3. Click "View Details"
4. Navigate to **Quota View**
5. Filter by Status: "Warning"
6. Identify capabilities at 80-100% usage
7. Click capability ID to see details

### Workflow 2: Check Trust Tier Policy

1. Open **Trust Tier View**
2. Click on tier header (e.g., "T2 - Remote MCP")
3. View risk level and default quota
4. Expand capability list
5. Click capability to see implementation details

### Workflow 3: Audit Tool Invocation

1. From audit logs, copy invocation ID
2. Open browser console
3. Run: `window.loadView('governance-provenance', 'inv-123')`
4. Review tool information
5. Check execution environment
6. Verify audit chain

### Workflow 4: Monitor System Health

1. Open **Governance Overview** as first page
2. Check capabilities distribution
3. Verify quota status shows "All OK"
4. Review recent events for anomalies
5. Set up periodic refresh (manual or automated)

## API Endpoints Used

All views consume read-only API endpoints:

```
GET /api/governance/summary
GET /api/governance/quotas?trust_tier={tier}&status={status}
GET /api/governance/trust-tiers
GET /api/governance/provenance/{invocation_id}
```

These endpoints have no side effects and do not modify system state.

## Troubleshooting

### View shows "Failed to Load"

**Possible causes:**
- Backend API not running
- Network connectivity issue
- Database not initialized

**Solution:**
1. Check WebUI server is running
2. Open browser console (F12)
3. Look for error messages
4. Verify API endpoint is accessible: `curl http://localhost:8080/api/governance/summary`

### Empty data in views

**Possible causes:**
- No capabilities registered
- No quota data tracked
- No audit events recorded

**Solution:**
- Install at least one extension
- Invoke some tools to generate data
- Wait for quota tracking to initialize

### Provenance view shows "No Invocation Selected"

**Cause:** Provenance view requires an invocation ID parameter

**Solution:**
- Access provenance view from audit logs
- Or use: `window.loadView('governance-provenance', 'your-id')`
- Do not access provenance view directly from navigation

## Design Principles

These views follow strict read-only principles:

✅ **Allowed:**
- View all governance data
- Filter and search
- Navigate between views
- Copy data for reports

❌ **Not Allowed:**
- Modify quota limits
- Change trust tiers
- Bypass gates
- Override policies

**Why read-only?**
Governance modifications require:
- Admin token authentication
- CLI access for audit trail
- Explicit authorization

## Next Steps

After familiarizing yourself with these views:

1. **Add navigation links** to sidebar for easy access
2. **Create bookmarks** for frequently used views
3. **Set up monitoring** dashboards
4. **Document your policies** based on current settings
5. **Train team** on how to use governance views

## Support

For issues or questions:
- Check implementation doc: `docs/PR-2-WebUI-Views-Implementation.md`
- Review backend API: `agentos/webui/api/governance.py`
- Inspect browser console for errors
- Contact development team

## Related Documentation

- [ADR-GOV-001: Capability Governance](../adr/ADR-GOV-001-capability-governance.md)
- [Backend API Documentation](../api/governance.md)
- [Trust Tier Policy](../architecture/trust-tiers.md)
