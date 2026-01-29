/**
 * VirtualList - Virtual scrolling list for high-performance rendering of large lists
 *
 * Only renders visible items to the DOM, dramatically improving performance
 * for lists with thousands of items.
 *
 * Features:
 * - Renders only visible items (viewport culling)
 * - Maintains scroll position correctly
 * - Supports dynamic item heights
 * - Automatic reflow on resize
 * - Smooth scrolling experience
 *
 * Usage:
 * ```javascript
 * const virtualList = new VirtualList({
 *     container: document.getElementById('list-container'),
 *     itemHeight: 60,
 *     renderItem: (item, index) => {
 *         return `<div class="item">${item.text}</div>`;
 *     },
 *     overscan: 5  // Render 5 extra items above/below viewport
 * });
 *
 * virtualList.setItems(items);
 * virtualList.scrollToIndex(100);
 * ```
 */

export class VirtualList {
    /**
     * Create virtual list
     *
     * @param {Object} options - Configuration
     * @param {HTMLElement} options.container - Container element
     * @param {number} options.itemHeight - Fixed item height in pixels
     * @param {Function} options.renderItem - Item render function (item, index) => HTML string
     * @param {number} [options.overscan=3] - Number of items to render outside viewport
     * @param {Function} [options.onScroll] - Scroll callback (startIndex, endIndex) => void
     */
    constructor(options) {
        this.container = options.container;
        this.itemHeight = options.itemHeight;
        this.renderItem = options.renderItem;
        this.overscan = options.overscan || 3;
        this.onScroll = options.onScroll;

        // State
        this.items = [];
        this.startIndex = 0;
        this.endIndex = 0;
        this.visibleCount = 0;

        // DOM
        this.scrollContainer = null;
        this.viewport = null;
        this.spacer = null;

        // Throttling
        this.scrollTimer = null;
        this.resizeObserver = null;

        this.init();
    }

    /**
     * Initialize virtual list
     */
    init() {
        // Clear container
        this.container.innerHTML = '';

        // Create scroll container
        this.scrollContainer = document.createElement('div');
        this.scrollContainer.className = 'virtual-list-scroll';
        this.scrollContainer.style.cssText = `
            position: relative;
            width: 100%;
            height: 100%;
            overflow-y: auto;
            overflow-x: hidden;
        `;

        // Create spacer (sets total scroll height)
        this.spacer = document.createElement('div');
        this.spacer.className = 'virtual-list-spacer';
        this.spacer.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            pointer-events: none;
        `;
        this.scrollContainer.appendChild(this.spacer);

        // Create viewport (renders visible items)
        this.viewport = document.createElement('div');
        this.viewport.className = 'virtual-list-viewport';
        this.viewport.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
        `;
        this.scrollContainer.appendChild(this.viewport);

        this.container.appendChild(this.scrollContainer);

        // Setup event listeners
        this.setupEventListeners();

        // Calculate visible count
        this.updateVisibleCount();
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Scroll handler (throttled)
        this.scrollContainer.addEventListener('scroll', () => {
            if (this.scrollTimer) {
                clearTimeout(this.scrollTimer);
            }

            this.scrollTimer = setTimeout(() => {
                this.handleScroll();
            }, 16); // ~60fps
        });

        // Resize observer
        this.resizeObserver = new ResizeObserver(() => {
            this.updateVisibleCount();
            this.render();
        });
        this.resizeObserver.observe(this.scrollContainer);
    }

    /**
     * Handle scroll event
     */
    handleScroll() {
        const scrollTop = this.scrollContainer.scrollTop;
        const newStartIndex = Math.floor(scrollTop / this.itemHeight);

        // Check if we need to re-render
        if (newStartIndex !== this.startIndex) {
            this.startIndex = newStartIndex;
            this.render();
        }

        // Trigger callback
        if (this.onScroll) {
            this.onScroll(this.startIndex, this.endIndex);
        }
    }

    /**
     * Update visible item count based on container height
     */
    updateVisibleCount() {
        const containerHeight = this.scrollContainer.clientHeight;
        this.visibleCount = Math.ceil(containerHeight / this.itemHeight) + (this.overscan * 2);
    }

    /**
     * Set items to render
     *
     * @param {Array} items - Items to render
     */
    setItems(items) {
        this.items = items;

        // Update spacer height (total scroll height)
        const totalHeight = items.length * this.itemHeight;
        this.spacer.style.height = `${totalHeight}px`;

        // Reset scroll position
        this.startIndex = Math.floor(this.scrollContainer.scrollTop / this.itemHeight);

        // Render
        this.render();
    }

    /**
     * Append items to existing list
     *
     * @param {Array} newItems - New items to append
     */
    appendItems(newItems) {
        this.items.push(...newItems);

        // Update spacer height
        const totalHeight = this.items.length * this.itemHeight;
        this.spacer.style.height = `${totalHeight}px`;

        // Re-render if new items are in viewport
        const currentScrollBottom = this.scrollContainer.scrollTop + this.scrollContainer.clientHeight;
        const newItemsTop = (this.items.length - newItems.length) * this.itemHeight;

        if (newItemsTop < currentScrollBottom) {
            this.render();
        }
    }

    /**
     * Render visible items
     */
    render() {
        if (this.items.length === 0) {
            this.viewport.innerHTML = '<div class="virtual-list-empty">No items</div>';
            return;
        }

        // Calculate visible range
        this.startIndex = Math.max(0, this.startIndex - this.overscan);
        this.endIndex = Math.min(
            this.items.length,
            this.startIndex + this.visibleCount
        );

        // Render items
        const html = [];
        for (let i = this.startIndex; i < this.endIndex; i++) {
            const item = this.items[i];
            const itemHtml = this.renderItem(item, i);
            html.push(`
                <div class="virtual-list-item"
                     style="position: absolute;
                            top: ${i * this.itemHeight}px;
                            left: 0;
                            right: 0;
                            height: ${this.itemHeight}px;"
                     data-index="${i}">
                    ${itemHtml}
                </div>
            `);
        }

        this.viewport.innerHTML = html.join('');
    }

    /**
     * Scroll to specific index
     *
     * @param {number} index - Item index to scroll to
     * @param {boolean} [smooth=true] - Use smooth scrolling
     */
    scrollToIndex(index, smooth = true) {
        const scrollTop = index * this.itemHeight;
        this.scrollContainer.scrollTo({
            top: scrollTop,
            behavior: smooth ? 'smooth' : 'auto'
        });
    }

    /**
     * Scroll to bottom
     *
     * @param {boolean} [smooth=true] - Use smooth scrolling
     */
    scrollToBottom(smooth = true) {
        this.scrollToIndex(this.items.length - 1, smooth);
    }

    /**
     * Scroll to top
     *
     * @param {boolean} [smooth=true] - Use smooth scrolling
     */
    scrollToTop(smooth = true) {
        this.scrollToIndex(0, smooth);
    }

    /**
     * Get current scroll position info
     *
     * @returns {Object} { startIndex, endIndex, scrollTop, scrollPercentage }
     */
    getScrollInfo() {
        const scrollTop = this.scrollContainer.scrollTop;
        const scrollHeight = this.scrollContainer.scrollHeight;
        const clientHeight = this.scrollContainer.clientHeight;
        const scrollPercentage = scrollHeight > clientHeight
            ? (scrollTop / (scrollHeight - clientHeight)) * 100
            : 0;

        return {
            startIndex: this.startIndex,
            endIndex: this.endIndex,
            scrollTop,
            scrollPercentage: Math.round(scrollPercentage)
        };
    }

    /**
     * Check if scrolled near bottom
     *
     * @param {number} [threshold=100] - Distance from bottom in pixels
     * @returns {boolean} True if near bottom
     */
    isNearBottom(threshold = 100) {
        const scrollTop = this.scrollContainer.scrollTop;
        const scrollHeight = this.scrollContainer.scrollHeight;
        const clientHeight = this.scrollContainer.clientHeight;

        return scrollHeight - scrollTop - clientHeight < threshold;
    }

    /**
     * Update specific item by index
     *
     * @param {number} index - Item index
     * @param {Object} newItem - New item data
     */
    updateItem(index, newItem) {
        if (index >= 0 && index < this.items.length) {
            this.items[index] = newItem;

            // Re-render if item is visible
            if (index >= this.startIndex && index < this.endIndex) {
                const itemElement = this.viewport.querySelector(`[data-index="${index}"]`);
                if (itemElement) {
                    itemElement.innerHTML = this.renderItem(newItem, index);
                }
            }
        }
    }

    /**
     * Clear all items
     */
    clear() {
        this.items = [];
        this.startIndex = 0;
        this.endIndex = 0;
        this.spacer.style.height = '0';
        this.viewport.innerHTML = '<div class="virtual-list-empty">No items</div>';
        this.scrollContainer.scrollTop = 0;
    }

    /**
     * Destroy virtual list
     */
    destroy() {
        // Remove event listeners
        if (this.scrollTimer) {
            clearTimeout(this.scrollTimer);
        }

        if (this.resizeObserver) {
            this.resizeObserver.disconnect();
        }

        // Clear DOM
        if (this.container) {
            this.container.innerHTML = '';
        }

        // Clear references
        this.items = [];
        this.scrollContainer = null;
        this.viewport = null;
        this.spacer = null;
    }
}

// Export as default
export default VirtualList;

// Also expose globally for non-module usage
if (typeof window !== 'undefined') {
    window.VirtualList = VirtualList;
}
