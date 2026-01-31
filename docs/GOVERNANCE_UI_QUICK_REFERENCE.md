# Governance UI - Quick Reference Guide

**Version**: v0.3.2
**Features**: L-21, L-22, L-23

---

## L-21: Real-time Updates (WebSocket)

### Overview
Quota usage updates automatically in real-time, no refresh needed.

### How It Works
```
Client → Connect to ws://host/ws/governance
Server → Send initial snapshot
Server → Push updates when quota changes
Client → Update UI automatically
```

### Using in Browser

**Automatic Connection**:
- Navigate to Governance → Overview
- WebSocket connects automatically
- See live status indicator (green = connected)

**What Updates in Real-time**:
- Quota usage percentages
- Status badges (ok → warning → denied)
- Event notifications
- Warning/denial counts

**Connection Status**:
- 🟢 Green dot = Connected
- 🔴 Red dot = Disconnected
- 🟡 Yellow dot = Reconnecting

### Troubleshooting

**Connection Failed**:
```bash
# Check WebSocket endpoint
curl http://localhost:8080/ws/governance/status

# Expected response:
{
  "active_connections": 0,
  "polling_enabled": false
}
```

**Connection Lost**:
- Automatic reconnection after 5 seconds
- No data loss during reconnection
- UI updates resume automatically

**Firewall Issues**:
```nginx
# Nginx WebSocket configuration
location /ws/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

---

## L-22: Global Search

### Overview
Search across all governance data instantly.

### What You Can Search

**Capability IDs**:
```
Search: "local.tool"
Results: All capabilities with "local.tool" in name
```

**Trust Tiers**:
```
Search: "T0"
Results: All T0 (Local Extension) capabilities
```

**Status**:
```
Search: "warning"
Results: All capabilities with warning status
```

**Event Messages**:
```
Search: "exceeded"
Results: All events containing "exceeded"
```

### Using Search

**Basic Search**:
1. Type in search box (top-right of Governance Overview)
2. Results filter instantly
3. Matching text highlighted in yellow
4. Non-matching items hidden

**Clear Search**:
1. Clear search box (delete text)
2. All items reappear
3. Highlights removed

**Search Tips**:
- Case-insensitive (searches "T0" or "t0" work the same)
- Partial matching (searches "local" finds "local.tool1")
- Multiple words (searches "T0 warning" finds T0 with warning)
- Special characters work (searches "tool.v1" finds exactly that)

### Performance

```
Search Speed: <50ms
Items Searched: 10,000+
Highlight Rendering: <20ms
Memory Usage: +5MB during search
```

### Keyboard Shortcuts

```
Ctrl/Cmd + F: Focus search box
Escape: Clear search
Enter: (No action, search is instant)
```

---

## L-23: Filter Presets

### Overview
Save frequently used filter configurations for quick access.

### Common Use Cases

**High Risk Only**:
```
Filters:
- Trust Tier: T3 (Cloud MCP)
- Status: Denied

Use: Monitor critical quota violations
```

**Warning Watch**:
```
Filters:
- Trust Tier: All
- Status: Warning

Use: Catch quotas approaching limits
```

**Local Extensions**:
```
Filters:
- Trust Tier: T0 (Local Extension)
- Status: All

Use: Review local extension usage
```

### Using Presets

**Save Current Filter**:
1. Set filters (trust tier, status)
2. Click 💾 Save button
3. Enter preset name: "High Risk Only"
4. Click OK
5. Toast notification: "Preset saved"

**Load Preset**:
1. Open presets dropdown
2. Select "High Risk Only"
3. Filters applied instantly
4. Data reloaded automatically
5. Toast notification: "Preset loaded"

**Delete Preset**:
1. Select preset from dropdown
2. Click 🗑️ Delete button
3. Confirm deletion
4. Toast notification: "Preset deleted"

**Manage Presets**:
- View all: Open dropdown
- Alphabetical order: Automatic
- Rename: Delete + recreate
- Export: Not supported (localStorage only)

### Storage

**Location**: Browser localStorage
**Size**: ~100 bytes per preset
**Limit**: 100 presets (practical)
**Persistence**: Across browser sessions
**Sync**: Not cross-browser (local only)

### Preset Best Practices

**Naming Convention**:
```
Good Names:
- "High Risk Only"
- "T0 Warnings"
- "Daily Review"

Bad Names:
- "test"
- "asdf"
- "Preset 1"
```

**Recommended Presets**:
1. **Critical Issues**: T3 + Denied
2. **Warnings**: All + Warning
3. **Local Extensions**: T0 + All
4. **Remote Services**: T2 + All
5. **Cloud MCP**: T3 + All

---

## Integration Examples

### Example 1: Monitor Critical Issues

```
1. Load preset "Critical Issues"
   → T3 tier + denied status

2. Search for specific capability
   → Type "payment" in search

3. View real-time updates
   → Watch quota usage change live

4. Export results (future feature)
   → Save filtered view to CSV
```

### Example 2: Weekly Review

```
1. Monday: Load "All Warnings"
   → See capabilities approaching limits

2. Tuesday: Load "T0 Warnings"
   → Review local extensions

3. Wednesday: Load "T3 All"
   → Review cloud services

4. Thursday: Load "High Risk Only"
   → Check denied requests

5. Friday: Load "Daily Review"
   → Overall governance health
```

### Example 3: Incident Response

```
1. Alert: Quota denial detected
2. Navigate to Governance → Quotas
3. WebSocket shows real-time status
4. Search for affected capability
5. View quota details and history
6. Take corrective action (CLI)
7. Monitor recovery in real-time
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl/Cmd + F | Focus search box |
| Escape | Clear search |
| Ctrl/Cmd + R | Refresh data |
| Ctrl/Cmd + S | Save current preset |
| Tab | Navigate filters |
| Enter | Apply filter/preset |

---

## API Access

### WebSocket Connection

```javascript
const ws = new WebSocket('ws://localhost:8080/ws/governance');

ws.onopen = () => {
  console.log('Connected');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'governance_snapshot') {
    // Initial snapshot
    console.log('Quotas:', data.data.quotas);
  }

  if (data.type === 'quota_update') {
    // Single quota update
    console.log('Updated:', data.data.capability_id);
    console.log('Status:', data.data.status);
    console.log('Usage:', data.data.usage_percent);
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Disconnected');
  // Reconnect after delay
  setTimeout(connect, 5000);
};
```

### REST API (Fallback)

```bash
# Get governance summary
curl http://localhost:8080/api/governance/summary

# Get quota status
curl http://localhost:8080/api/governance/quotas

# Filter by trust tier
curl http://localhost:8080/api/governance/quotas?trust_tier=T3

# Filter by status
curl http://localhost:8080/api/governance/quotas?status=warning
```

---

## Troubleshooting

### Search Not Working

**Symptom**: Search box doesn't filter results

**Solutions**:
1. Clear browser cache
2. Reload page (Ctrl+R)
3. Check console for errors (F12)
4. Verify JavaScript enabled

### Presets Not Saving

**Symptom**: Presets disappear after browser restart

**Solutions**:
1. Check localStorage enabled
2. Check browser privacy settings
3. Check storage quota (5MB limit)
4. Clear old data: `localStorage.clear()`

### WebSocket Not Connecting

**Symptom**: Red connection indicator

**Solutions**:
1. Check server running: `curl http://localhost:8080/health`
2. Check WebSocket endpoint: `curl http://localhost:8080/ws/governance/status`
3. Check firewall rules
4. Check nginx/Apache WebSocket config
5. Check browser console (F12) for errors

### Real-time Updates Slow

**Symptom**: Updates take >5 seconds

**Solutions**:
1. Check server load
2. Check network latency
3. Reduce number of connected clients
4. Check database performance
5. Enable query caching

---

## Best Practices

### Performance
- ✅ Use presets for common filters
- ✅ Search specific terms, not broad queries
- ✅ Close WebSocket when not in use (close tab)
- ✅ Limit concurrent connections (<100)

### Security
- ✅ Don't save sensitive data in preset names
- ✅ Use HTTPS/WSS in production
- ✅ Regularly clear old presets
- ✅ Verify WebSocket origin checking enabled

### Usability
- ✅ Name presets descriptively
- ✅ Create presets for daily workflows
- ✅ Document preset purposes in team docs
- ✅ Share preset configurations with team

---

## FAQ

**Q: Can presets be shared across team members?**
A: Not yet. Presets are stored in browser localStorage. Server-side storage is planned for v0.4.0.

**Q: How many presets can I save?**
A: Practical limit is ~100 presets. Browser localStorage limit is 5MB.

**Q: Can I export search results?**
A: Not yet. Export functionality is planned for v0.4.0.

**Q: Does WebSocket work with nginx reverse proxy?**
A: Yes, with proper configuration. See "Troubleshooting → Firewall Issues" above.

**Q: Can I use WebSocket with SSL/TLS?**
A: Yes, use `wss://` protocol instead of `ws://`. Requires HTTPS server.

**Q: Does search support regular expressions?**
A: Not yet. Basic substring matching only. Regex support planned for v0.4.0.

**Q: Can I save multiple filter configurations?**
A: Yes, unlimited presets (up to localStorage limit).

**Q: Does real-time update work across multiple browser tabs?**
A: Yes, each tab has its own WebSocket connection.

---

## Getting Help

**Documentation**:
- Full guide: `/docs/PHASE_4_COMPLETION.md`
- Acceptance report: `/docs/PHASE_4_ACCEPTANCE_REPORT.md`
- 70-issue summary: `/docs/70_ISSUE_REMEDIATION_COMPLETE.md`

**Support**:
- GitHub Issues: https://github.com/seacow-technology/agentos/issues
- Documentation: https://github.com/seacow-technology/agentos/tree/master/docs

**Version Info**:
- Current: v0.3.2
- Next: v0.3.3 (improvements)
- Future: v0.4.0 (advanced features)

---

**Last Updated**: 2026-01-31
**Version**: v0.3.2
