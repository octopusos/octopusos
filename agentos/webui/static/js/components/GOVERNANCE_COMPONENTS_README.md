# Governance Dashboard Visualization Components

**Task #7 - Governance Dashboard Component Library**
**Version:** 0.3.2
**Status:** ✅ Complete

## Overview

A collection of reusable, data-driven visualization components for the C-level Governance Dashboard. These components provide consistent visual language, configurable thresholds, loading/error states, and dynamic updates.

## Components

### 1. RiskBadge

Displays risk level indicators with color coding and animations.

**File:** `RiskBadge.js`

**Features:**
- Four risk levels: CRITICAL, HIGH, MEDIUM, LOW
- Color-coded visual indicators
- Pulse animation for critical risks
- Three size variants: small, medium, large
- Dynamic updates

**Usage:**

```javascript
const badge = new RiskBadge({
    container: '#risk-container',
    level: 'CRITICAL',      // 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    size: 'medium',         // 'small', 'medium', 'large'
    showIcon: true,         // Show icon (default: true)
    uppercase: true         // Uppercase text (default: true)
});

// Update risk level
badge.update('LOW');

// Control pulse animation
badge.startPulse();
badge.stopPulse();

// Set tooltip
badge.setTooltip('Security vulnerability detected');

// Get current level
const level = badge.getLevel();

// Clean up
badge.destroy();
```

**Visual Design:**
- **CRITICAL:** Red (#EF4444) with pulse animation ⚠
- **HIGH:** Orange (#F59E0B) ▲
- **MEDIUM:** Yellow/Orange (#F59E0B) ●
- **LOW:** Green (#10B981) ✓

---

### 2. TrendSparkline

Mini chart showing time series trends with direction indicators.

**File:** `TrendSparkline.js`

**Features:**
- SVG-based sparkline rendering
- Trend direction arrows (↑/↓/→)
- Color-coded by direction
- Optional area fill
- Responsive sizing
- Smooth updates

**Usage:**

```javascript
const sparkline = new TrendSparkline({
    container: '#sparkline-container',
    data: [10, 15, 12, 18, 20, 17, 22],    // Data points
    direction: 'auto',                      // 'auto', 'up', 'down', 'stable'
    width: 100,                             // Width in pixels
    height: 30,                             // Height in pixels
    color: 'auto',                          // Auto or custom color
    strokeWidth: 2,                         // Line thickness
    showArrow: true,                        // Show direction arrow
    showArea: false                         // Fill area under line
});

// Update with new data
sparkline.update([15, 18, 20, 22, 25]);

// Get current direction
const direction = sparkline.getDirection(); // 'up', 'down', 'stable'

// Get percentage change
const change = sparkline.getPercentageChange(); // e.g., 12.5

// Clean up
sparkline.destroy();
```

**Trend Colors:**
- **Up:** Green (#10B981) ↑
- **Down:** Red (#EF4444) ↓
- **Stable:** Gray (#6B7280) →

---

### 3. MetricCard

Display key metrics with values, trends, and optional sparklines.

**File:** `MetricCard.js`

**Features:**
- Large value display
- Trend indicator with percentage
- Optional sparkline integration
- Subtitle text
- Icon support
- Loading and error states
- Three size variants

**Usage:**

```javascript
const card = new MetricCard({
    container: '#metric-container',
    title: 'Active Tasks',
    value: '42',
    trend: 'up',                    // 'up', 'down', 'stable', null
    trendValue: 12.5,               // Percentage
    sparklineData: [30, 35, 32, 38, 40, 39, 42],
    subtitle: 'Last 7 days',
    icon: '📊',
    size: 'medium',                 // 'small', 'medium', 'large'
    loading: false,
    error: null
});

// Update value and trend
card.setValue('50', {
    trend: 'down',
    trendValue: -5.2
});

// Update entire card
card.update({
    value: '48',
    trend: 'stable',
    subtitle: 'Updated just now'
});

// Update sparkline only
card.updateSparkline([32, 38, 40, 39, 42, 45, 48]);

// Set loading state
card.setLoading(true);

// Set error state
card.setError('Failed to load data');

// Clean up
card.destroy();
```

**Card Layout:**
```
┌──────────────────┐
│ 📊 TITLE         │
│ 42        ↑12.5% │
│ Last 7 days      │
│ ─────────────    │
│   📈 Sparkline   │
└──────────────────┘
```

---

### 4. HealthIndicator

Display system health with color-coded thresholds and multiple visualization modes.

**File:** `HealthIndicator.js`

**Features:**
- Three display modes: bar, circular, compact
- Configurable thresholds
- Color-coded status (healthy/warning/critical)
- Percentage display
- Label and description
- Loading and error states
- Smooth transitions

**Usage:**

```javascript
const health = new HealthIndicator({
    container: '#health-container',
    percentage: 85,                 // Health percentage (0-100)
    label: 'System Health',
    description: 'All systems operational',
    thresholds: {
        critical: 50,               // Below this = critical (red)
        warning: 70                 // Below this = warning (yellow)
    },
    mode: 'bar',                    // 'bar', 'circular', 'compact'
    showPercentage: true,
    showLabel: true,
    loading: false,
    error: null
});

// Update health percentage
health.update(92);

// Update with options
health.update(78, {
    description: 'Minor issues detected'
});

// Set loading state
health.setLoading(true);

// Set error state
health.setError('Unable to fetch health data');

// Get current status
const status = health.getStatus();
// Returns: { status: 'healthy', color: '#10B981', label: 'Healthy', cssClass: 'health-healthy' }

// Clean up
health.destroy();
```

**Display Modes:**

1. **Bar Mode:** Horizontal progress bar
   ```
   System Health              85%
   ████████████████████░░░░░░░
   All systems operational
   ```

2. **Circular Mode:** Donut chart style
   ```
       ◐ 85%
      Health
   ```

3. **Compact Mode:** Minimal inline display
   ```
   ● System Health 85%
   ```

**Threshold Colors:**
- **Healthy (≥70%):** Green (#10B981)
- **Warning (50-69%):** Yellow/Orange (#F59E0B)
- **Critical (<50%):** Red (#EF4444)

---

## Styling

**CSS File:** `governance-components.css`

### CSS Variables

```css
/* Risk Colors */
--risk-critical: #EF4444;
--risk-high: #F59E0B;
--risk-medium: #F59E0B;
--risk-low: #10B981;

/* Health Colors */
--health-healthy: #10B981;
--health-warning: #F59E0B;
--health-critical: #EF4444;

/* Trend Colors */
--trend-up: #10B981;
--trend-down: #EF4444;
--trend-stable: #6B7280;

/* Card Colors */
--card-bg: #FFFFFF;
--card-border: #E5E7EB;
--card-shadow: rgba(0, 0, 0, 0.05);
```

### Utility Classes

```css
/* Grid layout for cards */
.governance-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1rem;
}

/* Card wrapper */
.governance-card-wrapper {
    min-width: 0;
}
```

---

## Integration Example

### Basic Setup

```html
<!DOCTYPE html>
<html>
<head>
    <!-- Component Styles -->
    <link rel="stylesheet" href="/static/css/governance-components.css">
</head>
<body>
    <div class="governance-grid">
        <div id="metric-1"></div>
        <div id="metric-2"></div>
        <div id="metric-3"></div>
    </div>

    <!-- Component Scripts -->
    <script src="/static/js/components/RiskBadge.js"></script>
    <script src="/static/js/components/TrendSparkline.js"></script>
    <script src="/static/js/components/MetricCard.js"></script>
    <script src="/static/js/components/HealthIndicator.js"></script>

    <script>
        // Initialize components
        new MetricCard({
            container: '#metric-1',
            title: 'Active Tasks',
            value: '42',
            trend: 'up',
            trendValue: 12.5
        });

        new MetricCard({
            container: '#metric-2',
            title: 'Critical Findings',
            value: '8',
            trend: 'down',
            trendValue: -15.3
        });

        new MetricCard({
            container: '#metric-3',
            title: 'Code Coverage',
            value: '87%',
            trend: 'stable'
        });
    </script>
</body>
</html>
```

### Complete Dashboard Example

```javascript
// System health overview
const health = new HealthIndicator({
    container: '#system-health',
    percentage: 87,
    label: 'Overall System Health',
    mode: 'bar',
    description: 'System operating normally'
});

// Key metrics
const metrics = [
    {
        title: 'Total Tasks',
        value: '156',
        trend: 'up',
        trendValue: 23.4,
        sparklineData: [120, 125, 130, 135, 140, 150, 156]
    },
    {
        title: 'Critical Issues',
        value: '5',
        trend: 'down',
        trendValue: -28.6,
        sparklineData: [12, 10, 8, 7, 6, 6, 5]
    },
    {
        title: 'Code Quality',
        value: '8.7/10',
        trend: 'up',
        trendValue: 5.1,
        sparklineData: [8.0, 8.2, 8.3, 8.5, 8.6, 8.6, 8.7]
    }
];

metrics.forEach((config, index) => {
    new MetricCard({
        container: `#metric-${index}`,
        ...config
    });
});

// Risk badges
const risks = [
    { level: 'CRITICAL', count: 2 },
    { level: 'HIGH', count: 5 },
    { level: 'MEDIUM', count: 12 }
];

risks.forEach(risk => {
    const container = document.createElement('div');
    document.getElementById('risks').appendChild(container);
    new RiskBadge({ container, level: risk.level });
});
```

---

## API Endpoints Integration

Components are designed to work with governance dashboard APIs:

```javascript
// Fetch and display metrics
async function loadMetrics() {
    const card = new MetricCard({
        container: '#tasks-metric',
        title: 'Active Tasks',
        value: '0',
        loading: true
    });

    try {
        const response = await fetch('/api/governance/metrics/tasks');
        const data = await response.json();

        card.setValue(data.count, {
            trend: data.trend,
            trendValue: data.changePercent,
            sparklineData: data.history,
            subtitle: `Updated ${data.lastUpdate}`
        });
    } catch (error) {
        card.setError('Failed to load metric');
    }
}

// Live health updates
async function updateHealth() {
    const health = new HealthIndicator({
        container: '#system-health',
        percentage: 0,
        label: 'System Health',
        mode: 'bar',
        loading: true
    });

    try {
        const response = await fetch('/api/governance/health');
        const data = await response.json();

        health.update(data.percentage, {
            description: data.message
        });
    } catch (error) {
        health.setError('Unable to fetch health data');
    }
}

// Periodic updates
setInterval(updateHealth, 30000); // Update every 30 seconds
```

---

## Testing

### Demo Page

Open `test_governance_components.html` in a browser to see all components in action with various configurations and states.

### Unit Testing

```javascript
// Test RiskBadge
const badge = new RiskBadge({
    container: document.createElement('div'),
    level: 'LOW'
});
badge.update('CRITICAL');
console.assert(badge.getLevel() === 'CRITICAL', 'Badge update failed');

// Test TrendSparkline
const sparkline = new TrendSparkline({
    container: document.createElement('div'),
    data: [10, 20, 15]
});
console.assert(sparkline.getDirection() === 'up', 'Direction calculation failed');

// Test MetricCard
const card = new MetricCard({
    container: document.createElement('div'),
    title: 'Test',
    value: '10'
});
card.setValue('20', { trend: 'up', trendValue: 100 });

// Test HealthIndicator
const health = new HealthIndicator({
    container: document.createElement('div'),
    percentage: 85
});
const status = health.getStatus();
console.assert(status.status === 'healthy', 'Health status failed');
```

---

## Browser Compatibility

- **Chrome/Edge:** 88+
- **Firefox:** 85+
- **Safari:** 14+
- **Mobile:** iOS 14+, Android Chrome 88+

All components use modern JavaScript (ES6+) and SVG for graphics.

---

## Design Principles

1. **Data-Driven:** All components accept data as props and update dynamically
2. **Configurable:** Colors, thresholds, and behavior can be customized
3. **State Management:** Proper handling of loading, error, and success states
4. **Accessibility:** Semantic HTML, proper color contrast, keyboard navigation
5. **Performance:** Efficient rendering, minimal DOM updates
6. **Consistency:** Unified visual language across all components
7. **Testability:** Independent components with clear APIs

---

## Future Enhancements

- **Animations:** Add smooth transitions for value changes
- **Themes:** Dark mode support
- **Export:** Screenshot/PDF export functionality
- **Accessibility:** ARIA labels and screen reader support
- **Internationalization:** Multi-language support for labels
- **Responsive:** Improved mobile layouts

---

## Credits

**Developed for:** AgentOS Governance Dashboard
**Task:** #7 - Governance Dashboard Visualization Components
**Version:** 0.3.2
**Date:** January 2026

---

## Support

For issues or questions:
1. Check the demo page: `test_governance_components.html`
2. Review component source code comments
3. Test with browser dev tools console
4. Verify CSS is loaded correctly

## License

Part of AgentOS project. See main project license.
