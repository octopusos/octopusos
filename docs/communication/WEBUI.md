# CommunicationOS WebUI Control Panel

## Overview

The CommunicationOS WebUI Control Panel provides a comprehensive dashboard for monitoring and managing external communication operations in AgentOS. It offers real-time visibility into network policies, audit logs, and service status.

## Features

### 1. Network Status Control
- **Network Mode Toggle**: Switch between OFF, READONLY, and ON modes
- **Current Mode Display**: Visual indicator of the active network mode
- **Mode Descriptions**: Clear explanations of each mode's behavior

### 2. Service Status Monitoring
- **Operational Status**: Real-time service health indicator
- **Registered Connectors**: List of all available communication connectors
- **Connector Details**: View enabled status, supported operations, and rate limits
- **Statistics Dashboard**: Total requests, success rate, and per-connector metrics

### 3. Policy Configuration Snapshot
- **Policy Overview**: View all connector policies at a glance
- **Configuration Details**: Rate limits, timeouts, response size limits
- **Security Settings**: Sanitization, approval requirements, domain restrictions
- **Enabled/Disabled Status**: Quick visibility into active policies

### 4. Recent Audit Logs
- **Audit Table**: Displays up to 50 recent audit records
- **Filtering**: Filter by connector type, operation, status, and date range
- **Sortable Columns**: Sort by timestamp, status, risk level
- **Export Functionality**: Export audit data to CSV format

### 5. Evidence Viewer
- **Detailed Evidence View**: Click any audit record to view full details
- **Request/Response Summary**: Inspect request parameters and responses
- **Metadata Display**: View all audit metadata including risk assessments
- **Evidence Hash**: Cryptographic hash for audit trail verification
- **Citations**: View all external sources referenced in the operation

### 6. Auto-Refresh
- **Real-time Updates**: Toggle auto-refresh for live monitoring
- **Configurable Interval**: Updates every 10 seconds when enabled
- **Manual Refresh**: Refresh all data on demand

## Architecture

### Frontend Components

#### JavaScript View: `CommunicationView.js`
```javascript
class CommunicationView {
    - constructor(container)
    - init()
    - setupFilterBar()
    - setupDataTable()
    - setupEventListeners()
    - loadAllData()
    - loadStatus()
    - loadPolicy()
    - loadAudits()
    - renderStatus()
    - renderPolicy()
    - showEvidenceDetail()
    - toggleAutoRefresh()
    - exportAudits()
}
```

**Key Features:**
- Component-based architecture
- Reactive data updates
- Efficient DOM manipulation
- Event-driven interactions

#### CSS Styles: `communication.css`
- Responsive grid layouts
- Card-based design system
- Drawer animations
- Badge components
- Status indicators
- Color-coded risk levels

### Backend Integration

#### API Endpoints Used

1. **GET /api/communication/policy**
   - Retrieves all connector policies
   - Returns policy configuration for each connector type

2. **GET /api/communication/status**
   - Service operational status
   - Connector information
   - Statistics and metrics

3. **GET /api/communication/audits**
   - List audit records with filtering
   - Supports pagination and date ranges
   - Returns summary information

4. **GET /api/communication/audits/{audit_id}**
   - Detailed evidence information
   - Full request/response data
   - Metadata and hashes

5. **POST /api/communication/search** (future)
   - Execute web search operations
   - Integrated testing interface

6. **POST /api/communication/fetch** (future)
   - Execute web fetch operations
   - Integrated testing interface

## Usage

### Accessing the Control Panel

1. Start the AgentOS WebUI server:
   ```bash
   python -m agentos.webui.app
   ```

2. Open your browser to: `http://localhost:8000`

3. Navigate to: **Communication > CommunicationOS**

### Viewing Policy Configuration

The Policy Configuration section displays all active policies:

- **Connector Name**: Identifier for the policy
- **Enabled Status**: Whether the connector is active
- **Rate Limit**: Requests allowed per minute
- **Timeout**: Maximum request duration
- **Max Response**: Maximum response size in MB
- **Sanitization**: Input/output sanitization settings
- **Domain Restrictions**: Blocked or allowed domains

### Filtering Audit Logs

Use the filter bar to narrow down audit records:

1. **By Connector Type**: web_search, web_fetch, email_send
2. **By Operation**: search, fetch, send
3. **By Status**: success, failed, denied, rate_limited
4. **By Date Range**: Start and end dates

Click "Apply Filters" to update the table.

### Viewing Evidence Details

1. Click any row in the audit table, or
2. Click the "View Evidence" icon button

The evidence drawer will slide in from the right showing:
- Request ID and timestamp
- Connector and operation details
- Full request parameters
- Response data (if available)
- All metadata including risk level
- Evidence hash for verification
- Citations and external references

### Exporting Audit Data

1. Filter the audit logs as desired
2. Click the "Export" button
3. A CSV file will be downloaded with all visible records

The CSV includes:
- Timestamp
- Request ID
- Connector type
- Operation
- Status
- Risk level

### Auto-Refresh Mode

Enable auto-refresh for real-time monitoring:

1. Toggle the "Auto-refresh" switch in the header
2. Data refreshes every 10 seconds
3. Toggle off to stop automatic updates

## Responsive Design

The control panel is fully responsive and adapts to different screen sizes:

- **Desktop (>1200px)**: Three-column grid layout for dashboard cards
- **Tablet (768-1199px)**: Two-column grid with adjusted spacing
- **Mobile (<768px)**: Single-column layout with stacked cards

The evidence drawer adapts to screen width:
- Desktop: 600px fixed width
- Mobile: 90% of viewport width

## Browser Compatibility

Tested and supported on:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Accessibility

- Semantic HTML structure
- ARIA labels for interactive elements
- Keyboard navigation support
- Focus indicators
- Screen reader friendly

## Performance

Optimizations implemented:
- Lazy loading of audit records
- Pagination (50 records per page)
- Debounced filter updates
- Efficient DOM updates
- CSS animations with GPU acceleration

## Security Considerations

- All API calls are authenticated
- CSRF protection enabled
- XSS prevention via proper escaping
- No sensitive data stored in localStorage
- Secure evidence hash verification

## Future Enhancements

Planned features for future releases:

1. **Interactive Testing**
   - Execute search/fetch operations from UI
   - Real-time operation monitoring
   - Response preview

2. **Policy Management**
   - Edit policies from UI
   - Enable/disable connectors
   - Dynamic rate limit adjustment

3. **Advanced Analytics**
   - Traffic patterns visualization
   - Risk trend analysis
   - Performance metrics charts

4. **Notification System**
   - Real-time alerts for denied requests
   - Rate limit warnings
   - Policy violation notifications

5. **Bulk Operations**
   - Batch approve/deny requests
   - Bulk audit exports
   - Mass policy updates

## Troubleshooting

### Control Panel Not Loading

1. Check server is running: `curl http://localhost:8000/health`
2. Verify static files exist:
   - `/static/js/views/CommunicationView.js`
   - `/static/css/communication.css`
3. Check browser console for JavaScript errors

### API Errors

1. Verify CommunicationService is initialized
2. Check API endpoint availability: `/api/communication/status`
3. Review server logs for error details
4. Ensure database/storage is accessible

### Empty Audit Logs

1. Verify evidence logger is configured
2. Execute some communication operations
3. Check audit storage location
4. Verify filtering criteria isn't too restrictive

### Evidence Drawer Not Opening

1. Check browser console for JavaScript errors
2. Verify audit_id is valid
3. Ensure evidence record exists in storage
4. Try manual refresh of the page

## Testing

### Manual Testing

Run the validation script:
```bash
./tests/webui/validate_communication_webui.sh
```

### Automated Testing

Run the test suite:
```bash
pytest tests/webui/test_communication_view.py -v
```

### Browser Testing

1. Navigate to control panel
2. Verify all sections load correctly
3. Test filtering and sorting
4. Open evidence drawer
5. Toggle auto-refresh
6. Export audit data
7. Test responsive layouts

## Integration Points

### With CommunicationService
- Real-time status monitoring
- Policy configuration display
- Audit log retrieval

### With Evidence Logger
- Audit record queries
- Evidence detail retrieval
- Citation tracking

### With Policy Engine
- Policy configuration access
- Connector status monitoring
- Rule enforcement visibility

### With Rate Limiter
- Rate limit monitoring
- Usage statistics
- Throttling indicators

## Development

### Adding New Features

1. Update `CommunicationView.js` class
2. Add necessary CSS to `communication.css`
3. Update API integration if needed
4. Add tests to `test_communication_view.py`
5. Update this documentation

### Code Style

Follow existing patterns:
- Use ES6 class syntax
- Implement cleanup in `destroy()` method
- Use template literals for HTML
- Apply consistent naming conventions
- Add JSDoc comments for public methods

### Dependencies

Required libraries:
- FilterBar component
- DataTable component
- Toast notification component
- ApiClient utility

## License

Part of AgentOS - See main LICENSE file for details.

## Support

For issues or questions:
1. Check this documentation
2. Review API documentation in `/docs/communication/API.md`
3. Check test files for examples
4. Open an issue on GitHub

---

**Last Updated**: 2025-01-30
**Version**: 1.0.0
**Status**: Production Ready
