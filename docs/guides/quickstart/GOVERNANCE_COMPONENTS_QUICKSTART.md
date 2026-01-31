# Governance Components Quick Start Guide

**Version:** 0.3.2 | **Status:** Production Ready

## Quick Reference

### 1. RiskBadge - Show Risk Levels

```javascript
// Critical risk with pulse
new RiskBadge({
    container: '#risk',
    level: 'CRITICAL'  // Pulsing red badge
});

// Update dynamically
badge.update('LOW');  // Changes to green
```

**Levels:** `CRITICAL` (red) | `HIGH` (orange) | `MEDIUM` (yellow) | `LOW` (green)

---

### 2. TrendSparkline - Mini Trend Charts

```javascript
// Show trend with arrow
new TrendSparkline({
    container: '#trend',
    data: [10, 12, 15, 18, 20],
    width: 100,
    height: 30
});

// With area fill
new TrendSparkline({
    container: '#trend',
    data: [10, 12, 15, 18, 20],
    showArea: true
});
```

**Auto-detects:** ↑ Upward | ↓ Downward | → Stable

---

### 3. MetricCard - Display Metrics

```javascript
// Basic metric card
new MetricCard({
    container: '#metric',
    title: 'Active Tasks',
    value: '42',
    trend: 'up',
    trendValue: 12.5
});

// With sparkline
new MetricCard({
    container: '#metric',
    title: 'Weekly Activity',
    value: '1,234',
    trend: 'up',
    trendValue: 8.4,
    sparklineData: [900, 950, 1020, 980, 1100, 1150, 1234],
    subtitle: 'Events this week'
});

// Loading state
card.setLoading(true);

// Error state
card.setError('Failed to load');

// Update value
card.setValue('50', { trend: 'down', trendValue: -5 });
```

---

### 4. HealthIndicator - System Health

```javascript
// Bar mode (default)
new HealthIndicator({
    container: '#health',
    percentage: 87,
    label: 'System Health',
    mode: 'bar'
});

// Circular mode (donut chart)
new HealthIndicator({
    container: '#health',
    percentage: 92,
    label: 'Health',
    mode: 'circular'
});

// Compact mode (inline)
new HealthIndicator({
    container: '#health',
    percentage: 85,
    label: 'Healthy',
    mode: 'compact'
});

// Update percentage
health.update(95);
```

**Thresholds (default):**
- Healthy: ≥70% (green)
- Warning: 50-69% (yellow)
- Critical: <50% (red)

---

## Complete Dashboard Example

```javascript
// System health overview
new HealthIndicator({
    container: '#system-health',
    percentage: 87,
    label: 'Overall System Health',
    mode: 'bar',
    description: 'System operating normally'
});

// Key metrics
new MetricCard({
    container: '#metric-tasks',
    title: 'Total Tasks',
    value: '156',
    trend: 'up',
    trendValue: 23.4,
    sparklineData: [120, 125, 130, 135, 140, 150, 156]
});

new MetricCard({
    container: '#metric-issues',
    title: 'Critical Issues',
    value: '5',
    trend: 'down',
    trendValue: -28.6,
    sparklineData: [12, 10, 8, 7, 6, 6, 5]
});

new MetricCard({
    container: '#metric-quality',
    title: 'Code Quality',
    value: '8.7/10',
    trend: 'up',
    trendValue: 5.1
});

// Risk indicators
new RiskBadge({
    container: '#risk-critical',
    level: 'CRITICAL'
});

new RiskBadge({
    container: '#risk-high',
    level: 'HIGH'
});
```

---

## HTML Setup

```html
<!DOCTYPE html>
<html>
<head>
    <!-- Include CSS -->
    <link rel="stylesheet" href="/static/css/governance-components.css">
</head>
<body>
    <!-- Containers -->
    <div class="governance-grid">
        <div id="metric-1"></div>
        <div id="metric-2"></div>
        <div id="metric-3"></div>
    </div>

    <!-- Include Scripts -->
    <script src="/static/js/components/RiskBadge.js"></script>
    <script src="/static/js/components/TrendSparkline.js"></script>
    <script src="/static/js/components/MetricCard.js"></script>
    <script src="/static/js/components/HealthIndicator.js"></script>

    <!-- Initialize -->
    <script>
        // Your component code here
    </script>
</body>
</html>
```

---

## API Integration Pattern

```javascript
async function loadDashboard() {
    // Create cards with loading state
    const taskCard = new MetricCard({
        container: '#tasks',
        title: 'Active Tasks',
        value: '0',
        loading: true
    });

    try {
        // Fetch data from API
        const response = await fetch('/api/governance/metrics/tasks');
        const data = await response.json();

        // Update with real data
        taskCard.setValue(data.count, {
            trend: data.trend,
            trendValue: data.changePercent,
            sparklineData: data.history,
            subtitle: `Updated ${data.lastUpdate}`
        });
    } catch (error) {
        // Show error state
        taskCard.setError('Failed to load metric');
    }
}

// Load on page load
loadDashboard();

// Refresh every 30 seconds
setInterval(loadDashboard, 30000);
```

---

## Styling Tips

### Custom Colors

```css
:root {
    --risk-critical: #DC2626;  /* Custom red */
    --trend-up: #059669;        /* Custom green */
}
```

### Grid Layout

```html
<div class="governance-grid">
    <!-- Auto-fits cards, min 250px each -->
</div>
```

### Card Hover Effects

All MetricCards have built-in hover effects (lift + shadow).

---

## Common Patterns

### Loading → Success

```javascript
card.setLoading(true);
// ... fetch data ...
card.setValue(data.value);
```

### Loading → Error

```javascript
card.setLoading(true);
// ... fetch fails ...
card.setError('Network error');
```

### Periodic Updates

```javascript
setInterval(() => {
    sparkline.update(getLatestData());
    health.update(getHealthPercentage());
}, 10000);
```

### Dynamic Risk Levels

```javascript
function updateRisk(severity) {
    badge.update(severity);
    if (severity === 'CRITICAL') {
        badge.setTooltip('Immediate action required!');
    }
}
```

---

## Testing

### Visual Testing

```bash
# Open demo in browser
open test_governance_components.html
```

### Validation

```bash
# Run automated validation
node validate_governance_components.js
```

---

## Troubleshooting

### Components not showing

1. Check CSS is loaded: View Page Source → Look for `governance-components.css`
2. Check JS is loaded: Open DevTools Console → Type `RiskBadge` → Should see class
3. Check container exists: `document.querySelector('#your-container')` → Should not be null

### Styling issues

1. Check for CSS conflicts: Inspect element in DevTools
2. Verify CSS variables are defined
3. Ensure container has proper width

### Update not working

1. Call `component.update()` with new data
2. Check console for errors
3. Verify data format matches expected type

---

## File Locations

```
/agentos/webui/static/
├── js/components/
│   ├── RiskBadge.js
│   ├── TrendSparkline.js
│   ├── MetricCard.js
│   └── HealthIndicator.js
└── css/
    └── governance-components.css
```

---

## Next Steps

1. ✅ Components ready
2. ⏭️ Create dashboard view (Task #6)
3. ⏭️ Connect to governance APIs
4. ⏭️ Add to main WebUI navigation

---

## Support

- **Demo:** `test_governance_components.html`
- **Docs:** `GOVERNANCE_COMPONENTS_README.md`
- **Delivery:** `TASK_7_GOVERNANCE_COMPONENTS_DELIVERY.md`

---

**Version:** 0.3.2
**Status:** ✅ Production Ready
**Date:** January 28, 2026
