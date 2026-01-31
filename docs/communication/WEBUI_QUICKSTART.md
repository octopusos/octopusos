# CommunicationOS WebUI Quick Start Guide

## 5-Minute Setup

### Step 1: Start the Server

```bash
cd /Users/pangge/PycharmProjects/AgentOS
python -m agentos.webui.app
```

### Step 2: Open Browser

Navigate to: **http://localhost:8000**

### Step 3: Access Control Panel

Click: **Communication > CommunicationOS** in the left navigation menu

That's it! The control panel should now be visible.

## What You'll See

### Dashboard (Top Section)

Three main cards:

1. **Network Status** (Left)
   - Shows current mode (OFF/READONLY/ON)
   - Toggle buttons to change mode
   - Mode description

2. **Service Status** (Middle)
   - Operational status indicator
   - List of registered connectors
   - Success rate statistics

3. **Policy Configuration** (Right)
   - All connector policies
   - Rate limits and timeouts
   - Security settings

### Audit Logs (Bottom Section)

- Table of recent communications
- Filter bar for searching
- Export button for CSV download

## Quick Actions

### Filter Audit Logs

1. Use filter bar above the table
2. Select connector type (e.g., "Web Search")
3. Choose operation (e.g., "search")
4. Click "Apply Filters"

### View Evidence

1. Click any row in the audit table
2. Evidence drawer slides in from right
3. View full request/response details
4. Click X or overlay to close

### Export Data

1. Filter the data as desired
2. Click "Export" button
3. CSV file downloads automatically

### Enable Auto-Refresh

1. Toggle "Auto-refresh" switch in header
2. Data refreshes every 10 seconds
3. Toggle off to stop updates

## Testing Without Real Data

If you don't have real communication data yet:

1. The dashboard will show empty state
2. Connectors will be listed but show 0 requests
3. Audit table will be empty

To generate test data, make some API calls:

```bash
# Test search operation
curl -X POST http://localhost:8000/api/communication/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "max_results": 5}'

# Test fetch operation
curl -X POST http://localhost:8000/api/communication/fetch \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

Refresh the WebUI to see the audit records.

## Troubleshooting

### Problem: Control Panel Not Loading

**Solution:**
1. Check browser console for errors (F12)
2. Verify server is running: `curl http://localhost:8000/health`
3. Clear browser cache and reload

### Problem: Empty Dashboard

**Solution:**
1. This is normal if no communications have occurred yet
2. Make test API calls (see above)
3. Or wait for real agent communications

### Problem: API Errors

**Solution:**
1. Check server logs for detailed errors
2. Verify CommunicationService is initialized
3. Ensure database/storage is accessible

## Next Steps

- Read full documentation: `/docs/communication/WEBUI.md`
- Review API documentation: `/docs/communication/API.md`
- Run tests: `pytest tests/webui/test_communication_view.py`
- Explore source code: `/agentos/webui/static/js/views/CommunicationView.js`

## Keyboard Shortcuts

- **Tab**: Navigate between elements
- **Enter**: Activate selected button
- **Esc**: Close evidence drawer
- **Ctrl+F**: Find in page

## Mobile Access

The control panel is fully responsive:

1. Open on mobile browser
2. Swipe to scroll dashboard cards
3. Tap row to view evidence
4. Swipe drawer to close

## Support

For help or issues:
1. Check documentation files in `/docs/communication/`
2. Review test files for examples
3. Check GitHub issues
4. Contact development team

---

**Happy Monitoring!** 🚀
