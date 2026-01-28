/**
 * RiskBadge - Risk level badge component
 *
 * Features:
 * - Risk level display (CRITICAL/HIGH/MEDIUM/LOW)
 * - Color-coded visual indicators
 * - Pulse animation for critical risks
 * - Size variants (small/medium/large)
 * - Dynamic updates
 *
 * Task #7 - Governance Dashboard Visualization Components
 * v0.3.2 - WebUI 100% Coverage Sprint
 */

class RiskBadge {
    /**
     * Create a RiskBadge component
     * @param {Object} options - Configuration options
     * @param {string} options.level - Risk level: 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
     * @param {HTMLElement|string} options.container - Container element or selector
     * @param {string} [options.size='medium'] - Size: 'small', 'medium', 'large'
     * @param {boolean} [options.showIcon=true] - Whether to show icon
     * @param {boolean} [options.uppercase=true] - Whether to uppercase text
     */
    constructor(options = {}) {
        this.options = {
            level: options.level || 'LOW',
            size: options.size || 'medium',
            showIcon: options.showIcon !== false,
            uppercase: options.uppercase !== false,
            ...options,
        };

        this.container = typeof options.container === 'string'
            ? document.querySelector(options.container)
            : options.container;

        if (!this.container) {
            throw new Error('RiskBadge: container is required');
        }

        this.element = null;
        this.render();
    }

    /**
     * Get configuration for risk level
     * @param {string} level - Risk level
     * @returns {Object} Level configuration
     */
    getLevelConfig(level) {
        const configs = {
            CRITICAL: {
                color: 'critical',
                icon: 'warning',
                label: 'Critical',
                cssClass: 'risk-badge-critical',
                pulse: true,
            },
            HIGH: {
                color: 'high',
                icon: 'arrow_drop_up',
                label: 'High',
                cssClass: 'risk-badge-high',
                pulse: false,
            },
            MEDIUM: {
                color: 'medium',
                icon: 'fiber_manual_record',
                label: 'Medium',
                cssClass: 'risk-badge-medium',
                pulse: false,
            },
            LOW: {
                color: 'low',
                icon: 'check',
                label: 'Low',
                cssClass: 'risk-badge-low',
                pulse: false,
            },
        };

        const normalizedLevel = level.toUpperCase();
        return configs[normalizedLevel] || configs.LOW;
    }

    /**
     * Render the badge
     */
    render() {
        const config = this.getLevelConfig(this.options.level);

        // Create badge element
        this.element = document.createElement('span');
        this.element.className = `risk-badge ${config.cssClass} risk-badge-${this.options.size}`;

        // Add pulse animation for critical
        if (config.pulse) {
            this.element.classList.add('risk-badge-pulse');
        }

        // Build content
        let content = '';

        if (this.options.showIcon) {
            content += `<span class="material-icons risk-badge-icon" style="font-size: 1em;">${config.icon}</span>`;
        }

        const labelText = this.options.uppercase
            ? config.label.toUpperCase()
            : config.label;
        content += `<span class="risk-badge-label">${labelText}</span>`;

        this.element.innerHTML = content;

        // Clear and append to container
        this.container.innerHTML = '';
        this.container.appendChild(this.element);
    }

    /**
     * Update the risk level
     * @param {string} newLevel - New risk level
     */
    update(newLevel) {
        if (this.options.level === newLevel) {
            return; // No change needed
        }

        this.options.level = newLevel;
        this.render();
    }

    /**
     * Get current risk level
     * @returns {string} Current level
     */
    getLevel() {
        return this.options.level;
    }

    /**
     * Start pulse animation
     */
    startPulse() {
        if (this.element) {
            this.element.classList.add('risk-badge-pulse');
        }
    }

    /**
     * Stop pulse animation
     */
    stopPulse() {
        if (this.element) {
            this.element.classList.remove('risk-badge-pulse');
        }
    }

    /**
     * Set custom tooltip
     * @param {string} tooltip - Tooltip text
     */
    setTooltip(tooltip) {
        if (this.element) {
            this.element.title = tooltip;
        }
    }

    /**
     * Destroy the component
     */
    destroy() {
        if (this.element && this.element.parentNode) {
            this.element.parentNode.removeChild(this.element);
        }
        this.element = null;
    }
}

// Export to window
window.RiskBadge = RiskBadge;
