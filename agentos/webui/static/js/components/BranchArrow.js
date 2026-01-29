/**
 * BranchArrow Component - Visualize gate failure branch-back
 *
 * PR-V4: Pipeline Visualization
 * Shows animated arrow from verifying back to planning on gate failure
 */

class BranchArrow {
    /**
     * Create branch arrow
     *
     * @param {SVGElement} svgContainer - SVG container
     * @param {Object} options - Options
     * @param {string} options.from - Source stage ID
     * @param {string} options.to - Target stage ID
     * @param {string} [options.reason] - Reason for branch
     */
    constructor(svgContainer, options) {
        this.svgContainer = svgContainer;
        this.from = options.from;
        this.to = options.to;
        this.reason = options.reason || 'Gate failed';

        this.arrowElement = null;
        this.labelElement = null;

        this.render();
    }

    /**
     * Render branch arrow
     */
    render() {
        console.log(`[BranchArrow] Creating arrow: ${this.from} -> ${this.to}`);

        // Get positions of from/to stages
        const fromEl = document.querySelector(`[data-stage="${this.from}"]`);
        const toEl = document.querySelector(`[data-stage="${this.to}"]`);

        if (!fromEl || !toEl) {
            console.warn('[BranchArrow] Could not find stage elements');
            return;
        }

        const fromRect = fromEl.getBoundingClientRect();
        const toRect = toEl.getBoundingClientRect();
        const svgRect = this.svgContainer.getBoundingClientRect();

        // Calculate positions relative to SVG
        const fromX = fromRect.left + fromRect.width / 2 - svgRect.left;
        const fromY = fromRect.bottom - svgRect.top;
        const toX = toRect.left + toRect.width / 2 - svgRect.left;
        const toY = toRect.bottom - svgRect.top;

        // Create curved path (arc downward)
        const midY = Math.max(fromY, toY) + 80;
        const path = `
            M ${fromX} ${fromY}
            Q ${fromX} ${midY}, ${(fromX + toX) / 2} ${midY}
            T ${toX} ${toY}
        `;

        // Create path element
        const pathEl = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        pathEl.setAttribute('d', path);
        pathEl.setAttribute('class', 'branch-arrow');

        // Create arrow head
        const arrowHead = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
        arrowHead.setAttribute('points', `${toX},${toY} ${toX - 8},${toY - 12} ${toX + 8},${toY - 12}`);
        arrowHead.setAttribute('class', 'branch-arrow-head');

        this.svgContainer.appendChild(pathEl);
        this.svgContainer.appendChild(arrowHead);

        this.arrowElement = pathEl;

        // Create label
        this.createLabel(fromX, toX, midY);
    }

    /**
     * Create label for branch arrow
     *
     * @param {number} fromX - From X position
     * @param {number} toX - To X position
     * @param {number} midY - Middle Y position
     */
    createLabel(fromX, toX, midY) {
        const label = document.createElement('div');
        label.className = 'branch-label';
        label.textContent = this.reason;

        // Position at midpoint
        label.style.left = `${(fromX + toX) / 2}px`;
        label.style.top = `${midY}px`;
        label.style.transform = 'translate(-50%, -50%)';

        // Append to parent of SVG (so it's positioned correctly)
        const parent = this.svgContainer.parentElement;
        if (parent) {
            parent.appendChild(label);
            this.labelElement = label;
        }
    }

    /**
     * Destroy branch arrow
     */
    destroy() {
        console.log('[BranchArrow] Destroying arrow');

        if (this.arrowElement && this.arrowElement.parentNode) {
            this.arrowElement.remove();
        }

        if (this.labelElement && this.labelElement.parentNode) {
            this.labelElement.remove();
        }

        this.arrowElement = null;
        this.labelElement = null;
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BranchArrow;
}
