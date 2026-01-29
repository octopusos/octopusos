/**
 * BatchRenderer - Batch DOM updates using requestAnimationFrame
 *
 * Collects multiple updates and applies them in a single animation frame,
 * reducing layout thrashing and improving rendering performance.
 *
 * Features:
 * - Batches updates within single animation frame
 * - Prevents unnecessary reflows/repaints
 * - Automatic flushing on next frame
 * - Manual flush support
 * - Update deduplication
 *
 * Usage:
 * ```javascript
 * const renderer = new BatchRenderer((updates) => {
 *     updates.forEach(update => {
 *         const element = document.getElementById(update.id);
 *         element.textContent = update.text;
 *     });
 * });
 *
 * // Queue updates (batched automatically)
 * renderer.schedule({ id: 'elem1', text: 'Update 1' });
 * renderer.schedule({ id: 'elem2', text: 'Update 2' });
 *
 * // Both updates applied in next animation frame
 * ```
 */

export class BatchRenderer {
    /**
     * Create batch renderer
     *
     * @param {Function} renderFn - Render function (updates[]) => void
     * @param {Object} [options] - Configuration
     * @param {number} [options.maxBatchSize=100] - Max updates per batch
     * @param {boolean} [options.deduplicate=false] - Deduplicate updates by key
     * @param {Function} [options.getKey] - Key function for deduplication (update) => string
     */
    constructor(renderFn, options = {}) {
        this.renderFn = renderFn;
        this.options = {
            maxBatchSize: 100,
            deduplicate: false,
            getKey: null,
            ...options
        };

        // State
        this.pendingUpdates = [];
        this.updateMap = new Map(); // For deduplication
        this.rafId = null;
        this.isDestroyed = false;

        // Stats
        this.stats = {
            batchesRendered: 0,
            updatesRendered: 0,
            updatesDeduplicated: 0
        };
    }

    /**
     * Schedule update for next frame
     *
     * @param {*} update - Update data
     */
    schedule(update) {
        if (this.isDestroyed) {
            console.warn('[BatchRenderer] Cannot schedule - renderer destroyed');
            return;
        }

        // Deduplication
        if (this.options.deduplicate && this.options.getKey) {
            const key = this.options.getKey(update);
            if (this.updateMap.has(key)) {
                // Replace existing update
                const existingIndex = this.pendingUpdates.findIndex(
                    u => this.options.getKey(u) === key
                );
                if (existingIndex !== -1) {
                    this.pendingUpdates[existingIndex] = update;
                    this.stats.updatesDeduplicated++;
                }
            } else {
                this.updateMap.set(key, update);
                this.pendingUpdates.push(update);
            }
        } else {
            this.pendingUpdates.push(update);
        }

        // Schedule flush if not already scheduled
        if (!this.rafId) {
            this.rafId = requestAnimationFrame(() => {
                this.flush();
            });
        }

        // Force flush if batch is full
        if (this.pendingUpdates.length >= this.options.maxBatchSize) {
            this.flushImmediate();
        }
    }

    /**
     * Flush pending updates immediately (synchronous)
     */
    flushImmediate() {
        if (this.rafId) {
            cancelAnimationFrame(this.rafId);
            this.rafId = null;
        }
        this._flush();
    }

    /**
     * Flush pending updates (called by RAF)
     */
    flush() {
        this._flush();
        this.rafId = null;
    }

    /**
     * Internal flush implementation
     */
    _flush() {
        if (this.pendingUpdates.length === 0) {
            return;
        }

        try {
            // Call render function with batched updates
            this.renderFn(this.pendingUpdates);

            // Update stats
            this.stats.batchesRendered++;
            this.stats.updatesRendered += this.pendingUpdates.length;

        } catch (error) {
            console.error('[BatchRenderer] Render error:', error);
        } finally {
            // Clear pending updates
            this.pendingUpdates = [];
            this.updateMap.clear();
        }
    }

    /**
     * Check if there are pending updates
     *
     * @returns {boolean} True if updates are pending
     */
    hasPending() {
        return this.pendingUpdates.length > 0;
    }

    /**
     * Get number of pending updates
     *
     * @returns {number} Pending update count
     */
    getPendingCount() {
        return this.pendingUpdates.length;
    }

    /**
     * Get statistics
     *
     * @returns {Object} Statistics
     */
    getStats() {
        return { ...this.stats };
    }

    /**
     * Reset statistics
     */
    resetStats() {
        this.stats = {
            batchesRendered: 0,
            updatesRendered: 0,
            updatesDeduplicated: 0
        };
    }

    /**
     * Destroy renderer
     */
    destroy() {
        this.isDestroyed = true;

        // Cancel pending RAF
        if (this.rafId) {
            cancelAnimationFrame(this.rafId);
            this.rafId = null;
        }

        // Flush any pending updates
        if (this.pendingUpdates.length > 0) {
            this._flush();
        }

        // Clear state
        this.pendingUpdates = [];
        this.updateMap.clear();
    }
}

/**
 * DOMBatchRenderer - Specialized batch renderer for DOM updates
 *
 * Provides common DOM update operations with automatic batching.
 */
export class DOMBatchRenderer extends BatchRenderer {
    constructor(options = {}) {
        super((updates) => {
            // Group updates by operation type for efficiency
            const textUpdates = [];
            const classUpdates = [];
            const styleUpdates = [];
            const attributeUpdates = [];

            updates.forEach(update => {
                switch (update.type) {
                    case 'text':
                        textUpdates.push(update);
                        break;
                    case 'class':
                        classUpdates.push(update);
                        break;
                    case 'style':
                        styleUpdates.push(update);
                        break;
                    case 'attribute':
                        attributeUpdates.push(update);
                        break;
                }
            });

            // Apply text updates
            textUpdates.forEach(({ element, text }) => {
                if (element) {
                    element.textContent = text;
                }
            });

            // Apply class updates
            classUpdates.forEach(({ element, add, remove }) => {
                if (element) {
                    if (remove) {
                        element.classList.remove(...(Array.isArray(remove) ? remove : [remove]));
                    }
                    if (add) {
                        element.classList.add(...(Array.isArray(add) ? add : [add]));
                    }
                }
            });

            // Apply style updates
            styleUpdates.forEach(({ element, styles }) => {
                if (element) {
                    Object.assign(element.style, styles);
                }
            });

            // Apply attribute updates
            attributeUpdates.forEach(({ element, attributes }) => {
                if (element) {
                    Object.entries(attributes).forEach(([key, value]) => {
                        if (value === null) {
                            element.removeAttribute(key);
                        } else {
                            element.setAttribute(key, value);
                        }
                    });
                }
            });
        }, options);
    }

    /**
     * Schedule text content update
     *
     * @param {HTMLElement} element - Element to update
     * @param {string} text - New text content
     */
    updateText(element, text) {
        this.schedule({ type: 'text', element, text });
    }

    /**
     * Schedule class update
     *
     * @param {HTMLElement} element - Element to update
     * @param {string|string[]} [add] - Classes to add
     * @param {string|string[]} [remove] - Classes to remove
     */
    updateClass(element, add, remove) {
        this.schedule({ type: 'class', element, add, remove });
    }

    /**
     * Schedule style update
     *
     * @param {HTMLElement} element - Element to update
     * @param {Object} styles - Style properties to update
     */
    updateStyle(element, styles) {
        this.schedule({ type: 'style', element, styles });
    }

    /**
     * Schedule attribute update
     *
     * @param {HTMLElement} element - Element to update
     * @param {Object} attributes - Attributes to update (null to remove)
     */
    updateAttribute(element, attributes) {
        this.schedule({ type: 'attribute', element, attributes });
    }
}

// Export as default
export default BatchRenderer;

// Also expose globally for non-module usage
if (typeof window !== 'undefined') {
    window.BatchRenderer = BatchRenderer;
    window.DOMBatchRenderer = DOMBatchRenderer;
}
