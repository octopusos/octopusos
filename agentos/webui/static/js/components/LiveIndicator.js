/**
 * LiveIndicator - Live status indicator component
 *
 * Features:
 * - Connection status (connected/disconnected/connecting)
 * - Color-coded states
 * - Pulse animation
 * - Tooltip
 * - Click action
 *
 * v0.3.2 - WebUI 100% Coverage Sprint
 */

class LiveIndicator {
    constructor(container, options = {}) {
        this.container = typeof container === 'string'
            ? document.querySelector(container)
            : container;

        this.options = {
            status: options.status || 'disconnected',
            label: options.label || '',
            showLabel: options.showLabel !== false,
            tooltip: options.tooltip || null,
            onClick: options.onClick || null,
            size: options.size || 'medium', // small, medium, large
            ...options,
        };

        this.render();
    }

    /**
     * Render the indicator
     */
    render() {
        this.container.innerHTML = '';
        this.container.className = `live-indicator ${this.options.size}`;

        // Click handler
        if (this.options.onClick) {
            this.container.style.cursor = 'pointer';
            this.container.onclick = this.options.onClick;
        }

        // Tooltip
        if (this.options.tooltip) {
            this.container.title = this.options.tooltip;
        }

        // Dot
        const dot = document.createElement('span');
        dot.className = `indicator-dot ${this.getStatusClass()}`;
        this.container.appendChild(dot);

        // Label
        if (this.options.showLabel && this.options.label) {
            const label = document.createElement('span');
            label.className = 'indicator-label';
            label.textContent = this.options.label;
            this.container.appendChild(label);
        }
    }

    /**
     * Get status class
     */
    getStatusClass() {
        const statusMap = {
            connected: 'status-connected',
            disconnected: 'status-disconnected',
            connecting: 'status-connecting',
            error: 'status-error',
            warning: 'status-warning',
            ready: 'status-ready',
            degraded: 'status-degraded',
        };

        const status = this.options.status.toLowerCase();
        return statusMap[status] || 'status-unknown';
    }

    /**
     * Update status
     */
    setStatus(status, options = {}) {
        this.options.status = status;

        if (options.label !== undefined) {
            this.options.label = options.label;
        }

        if (options.tooltip !== undefined) {
            this.options.tooltip = options.tooltip;
        }

        this.render();
    }

    /**
     * Update label
     */
    setLabel(label) {
        this.options.label = label;
        const labelEl = this.container.querySelector('.indicator-label');
        if (labelEl) {
            labelEl.textContent = label;
        }
    }

    /**
     * Update tooltip
     */
    setTooltip(tooltip) {
        this.options.tooltip = tooltip;
        this.container.title = tooltip;
    }

    /**
     * Show pulse animation
     */
    pulse() {
        const dot = this.container.querySelector('.indicator-dot');
        if (dot) {
            dot.classList.add('pulse');
            setTimeout(() => {
                dot.classList.remove('pulse');
            }, 1000);
        }
    }

    /**
     * Start continuous pulse
     */
    startPulse() {
        const dot = this.container.querySelector('.indicator-dot');
        if (dot) {
            dot.classList.add('pulse-continuous');
        }
    }

    /**
     * Stop continuous pulse
     */
    stopPulse() {
        const dot = this.container.querySelector('.indicator-dot');
        if (dot) {
            dot.classList.remove('pulse-continuous');
        }
    }
}

/**
 * MultiLiveIndicator - Multiple status indicators
 *
 * For showing multiple service statuses (e.g., WebSocket + Health + DB)
 */
class MultiLiveIndicator {
    constructor(container, options = {}) {
        this.container = typeof container === 'string'
            ? document.querySelector(container)
            : container;

        this.options = {
            indicators: options.indicators || [],
            layout: options.layout || 'horizontal', // horizontal, vertical
            spacing: options.spacing || 'medium',
            ...options,
        };

        this.indicators = {};
        this.render();
    }

    /**
     * Render all indicators
     */
    render() {
        this.container.innerHTML = '';
        this.container.className = `multi-live-indicator ${this.options.layout} spacing-${this.options.spacing}`;

        this.options.indicators.forEach(config => {
            const wrapper = document.createElement('div');
            wrapper.className = 'indicator-wrapper';
            wrapper.dataset.indicatorId = config.id;

            const indicator = new LiveIndicator(wrapper, config);
            this.indicators[config.id] = indicator;

            this.container.appendChild(wrapper);
        });
    }

    /**
     * Update specific indicator
     */
    updateIndicator(id, status, options = {}) {
        const indicator = this.indicators[id];
        if (indicator) {
            indicator.setStatus(status, options);
        }
    }

    /**
     * Get indicator by ID
     */
    getIndicator(id) {
        return this.indicators[id];
    }

    /**
     * Add new indicator
     */
    addIndicator(config) {
        const wrapper = document.createElement('div');
        wrapper.className = 'indicator-wrapper';
        wrapper.dataset.indicatorId = config.id;

        const indicator = new LiveIndicator(wrapper, config);
        this.indicators[config.id] = indicator;

        this.container.appendChild(wrapper);
    }

    /**
     * Remove indicator
     */
    removeIndicator(id) {
        const wrapper = this.container.querySelector(`[data-indicator-id="${id}"]`);
        if (wrapper) {
            wrapper.remove();
        }
        delete this.indicators[id];
    }

    /**
     * Get overall status (worst status wins)
     */
    getOverallStatus() {
        const statusPriority = {
            error: 0,
            disconnected: 1,
            warning: 2,
            degraded: 3,
            connecting: 4,
            connected: 5,
            ready: 6,
        };

        let worstStatus = 'ready';
        let worstPriority = statusPriority.ready;

        Object.values(this.indicators).forEach(indicator => {
            const status = indicator.options.status.toLowerCase();
            const priority = statusPriority[status] || 10;

            if (priority < worstPriority) {
                worstStatus = status;
                worstPriority = priority;
            }
        });

        return worstStatus;
    }
}

// Export to window
window.LiveIndicator = LiveIndicator;
window.MultiLiveIndicator = MultiLiveIndicator;
