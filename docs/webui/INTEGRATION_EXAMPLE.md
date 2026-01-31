# Decision Lag Source Display Integration Example

This document shows how to integrate the `DecisionLagSource` component into existing WebUI views.

## Integration Points

There are three main places where decision lag statistics can be displayed:

1. **Governance Dashboard** - Overall system health view
2. **Task Detail View** - Individual task's decision trace
3. **Statistics Page** - Dedicated metrics and analytics page

## Example 1: Governance Dashboard Integration

**File**: `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/static/js/views/GovernanceDashboard.js`

```javascript
class GovernanceDashboard {
    constructor(container) {
        this.container = container;
        this.lagSourceComponent = null;
    }

    init() {
        this.container.innerHTML = `
            <div class="governance-dashboard">
                <h2>Governance Dashboard</h2>

                <!-- Decision Lag Section -->
                <div class="dashboard-section">
                    <h3>Decision Lag Analysis</h3>
                    <div id="decision-lag-stats" class="stats-container"></div>
                </div>

                <!-- Other sections... -->
            </div>
        `;

        this.loadDecisionLagStats();
    }

    async loadDecisionLagStats() {
        const container = document.getElementById('decision-lag-stats');

        try {
            container.innerHTML = '<div class="loading-spinner">Loading lag statistics...</div>';

            // Fetch data from API
            const result = await apiClient.get('/api/governance/stats/decision-lag?window=24h');

            if (result.ok) {
                // Initialize and render the component
                this.lagSourceComponent = new DecisionLagSource(container, {
                    showSamples: true,
                    showCoverage: true,
                    showStatistics: true
                });

                this.lagSourceComponent.render(result.data);
            } else {
                container.innerHTML = `
                    <div class="error-message">
                        Failed to load lag statistics: ${result.message}
                    </div>
                `;
            }
        } catch (error) {
            console.error('Failed to load decision lag stats:', error);
            container.innerHTML = `
                <div class="error-message">
                    Failed to load lag statistics
                </div>
            `;
        }
    }

    destroy() {
        if (this.lagSourceComponent) {
            this.lagSourceComponent.destroy();
        }
        this.container.innerHTML = '';
    }
}
```

## Example 2: Task Detail View Integration

**File**: `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/static/js/views/TasksView.js`

Add a new section to the task detail drawer showing decision lag for that specific task:

```javascript
class TasksView {
    // ... existing code ...

    renderTaskDetail(task) {
        const drawerBody = this.container.querySelector('.drawer-body');

        drawerBody.innerHTML = `
            <div class="task-detail">
                <!-- Existing tabs -->
                <div class="tab-buttons">
                    <button class="tab-btn active" data-tab="overview">Overview</button>
                    <button class="tab-btn" data-tab="decision-trace">Decision Trace</button>
                    <button class="tab-btn" data-tab="lag-stats">Lag Analysis</button>
                    <!-- Other tabs... -->
                </div>

                <div class="tab-content">
                    <!-- Overview Tab -->
                    <div class="tab-pane active" data-tab-pane="overview">
                        <!-- Existing overview content -->
                    </div>

                    <!-- Decision Trace Tab -->
                    <div class="tab-pane" data-tab-pane="decision-trace">
                        <div id="decision-trace-content"></div>
                    </div>

                    <!-- NEW: Lag Analysis Tab -->
                    <div class="tab-pane" data-tab-pane="lag-stats">
                        <div class="lag-analysis-container">
                            <h4>Decision Lag Analysis for this Task</h4>
                            <div id="task-lag-stats"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Setup tab switching
        this.setupTabSwitching(task);
    }

    setupTabSwitching(task) {
        const tabButtons = this.container.querySelectorAll('.tab-btn');

        tabButtons.forEach(button => {
            button.addEventListener('click', async () => {
                // ... existing tab switching logic ...

                const tabName = button.dataset.tab;

                // Load lag stats when tab is activated
                if (tabName === 'lag-stats' && !this.lagStatsLoaded) {
                    await this.loadTaskLagStats(task.task_id);
                    this.lagStatsLoaded = true;
                }
            });
        });
    }

    async loadTaskLagStats(taskId) {
        const container = document.getElementById('task-lag-stats');

        try {
            container.innerHTML = '<div class="loading-spinner">Loading lag statistics...</div>';

            // Fetch lag data for this specific task
            // Note: You might need to create a new API endpoint for per-task lag stats
            const result = await apiClient.get(`/api/governance/tasks/${taskId}/lag-stats`);

            if (result.ok) {
                const lagSource = new DecisionLagSource(container, {
                    showSamples: true,
                    showCoverage: true,
                    showStatistics: true
                });

                lagSource.render(result.data);
            } else {
                container.innerHTML = `
                    <div class="info-message">
                        No lag statistics available for this task
                    </div>
                `;
            }
        } catch (error) {
            console.error('Failed to load task lag stats:', error);
            container.innerHTML = `
                <div class="error-message">
                    Failed to load lag statistics
                </div>
            `;
        }
    }
}
```

## Example 3: Standalone Statistics Page

**File**: `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/static/js/views/StatisticsView.js`

Create a dedicated statistics page with multiple time windows:

```javascript
class StatisticsView {
    constructor(container) {
        this.container = container;
        this.lagComponents = {};
    }

    init() {
        this.container.innerHTML = `
            <div class="statistics-view">
                <h2>System Statistics</h2>

                <!-- Time Window Selector -->
                <div class="window-selector">
                    <button class="window-btn active" data-window="24h">24 Hours</button>
                    <button class="window-btn" data-window="7d">7 Days</button>
                    <button class="window-btn" data-window="30d">30 Days</button>
                </div>

                <!-- Decision Lag Statistics -->
                <div class="stats-section">
                    <h3>Decision Lag Analysis</h3>
                    <div id="lag-stats-24h" class="stats-container"></div>
                    <div id="lag-stats-7d" class="stats-container" style="display: none;"></div>
                    <div id="lag-stats-30d" class="stats-container" style="display: none;"></div>
                </div>

                <!-- Other statistics sections... -->
            </div>
        `;

        this.setupWindowSelector();
        this.loadLagStats('24h');
    }

    setupWindowSelector() {
        const windowButtons = this.container.querySelectorAll('.window-btn');

        windowButtons.forEach(button => {
            button.addEventListener('click', () => {
                // Update active button
                windowButtons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');

                // Show corresponding stats container
                const window = button.dataset.window;
                this.showStatsContainer(window);

                // Load stats if not already loaded
                if (!this.lagComponents[window]) {
                    this.loadLagStats(window);
                }
            });
        });
    }

    showStatsContainer(window) {
        const containers = this.container.querySelectorAll('.stats-container');
        containers.forEach(c => c.style.display = 'none');

        const targetContainer = document.getElementById(`lag-stats-${window}`);
        if (targetContainer) {
            targetContainer.style.display = 'block';
        }
    }

    async loadLagStats(window) {
        const container = document.getElementById(`lag-stats-${window}`);

        try {
            container.innerHTML = '<div class="loading-spinner">Loading...</div>';

            const result = await apiClient.get(`/api/governance/stats/decision-lag?window=${window}`);

            if (result.ok) {
                const lagSource = new DecisionLagSource(container, {
                    showSamples: true,
                    showCoverage: true,
                    showStatistics: true
                });

                lagSource.render(result.data);
                this.lagComponents[window] = lagSource;
            } else {
                container.innerHTML = `
                    <div class="error-message">
                        Failed to load statistics: ${result.message}
                    </div>
                `;
            }
        } catch (error) {
            console.error(`Failed to load ${window} lag stats:`, error);
            container.innerHTML = `
                <div class="error-message">
                    Failed to load statistics
                </div>
            `;
        }
    }

    destroy() {
        Object.values(this.lagComponents).forEach(component => {
            if (component && component.destroy) {
                component.destroy();
            }
        });
        this.container.innerHTML = '';
    }
}
```

## Required HTML/CSS Includes

Add these to your main HTML file or template:

```html
<!-- In <head> section -->
<link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
<link rel="stylesheet" href="/static/css/decision-lag-source.css">

<!-- Before closing </body> tag -->
<script src="/static/js/components/DecisionLagSource.js"></script>
```

## API Endpoint Requirements

The following API endpoints should be available:

### 1. Global Decision Lag Stats
```
GET /api/governance/stats/decision-lag?window=24h&pctl=95
```

Response:
```json
{
  "window": "24h",
  "percentile": 95,
  "p50": 0.123,
  "p95": 0.456,
  "count": 100,
  "samples": [...],
  "query_method": "columns",
  "redundant_column_coverage": 0.95
}
```

### 2. Per-Task Lag Stats (Optional)
```
GET /api/governance/tasks/{task_id}/lag-stats
```

Response: Same structure as above, but filtered to specific task

## Testing Your Integration

### 1. Visual Testing
Open your browser's developer tools and:
- Check that the component renders correctly
- Verify colors and badges match the design
- Test responsive layout on different screen sizes

### 2. Functional Testing
- Switch between time windows (24h, 7d, 30d)
- Verify coverage percentages update correctly
- Hover over badges to see tooltips
- Check that samples display correct source tags

### 3. Performance Testing
- Monitor network requests (should only fetch once per window)
- Check rendering speed (should be < 100ms)
- Verify no memory leaks when destroying components

## Troubleshooting

### Component Not Rendering
- Check that `DecisionLagSource.js` is loaded
- Verify CSS file is included
- Check browser console for errors

### API Errors
- Verify API endpoint is available
- Check response format matches expected structure
- Ensure database has necessary columns

### Styling Issues
- Verify Material Icons font is loaded
- Check CSS specificity conflicts
- Use browser inspector to debug styles

## Next Steps

1. Choose integration point (Dashboard, Task Detail, or Statistics)
2. Add HTML structure and component initialization
3. Test with real data
4. Adjust styling to match your theme
5. Add error handling and loading states

---

**For questions or issues**, refer to:
- [Component Documentation](./LEAD_DATA_SOURCE_DISPLAY.md)
- [API Documentation](./governance_api.md)
- [Testing Guide](../../tests/unit/supervisor/test_decision_lag_source.py)
