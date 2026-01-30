/**
 * EventThrottler - Throttle high-frequency events
 *
 * Reduces event frequency to prevent UI overload while ensuring
 * latest state is always eventually delivered.
 *
 * Features:
 * - Time-based throttling (max N events per second)
 * - Automatic aggregation of throttled events
 * - Type-based throttling rules
 * - Latest state preservation
 * - Periodic flush of aggregated events
 *
 * Usage:
 * ```javascript
 * const throttler = new EventThrottler({
 *     interval: 1000,  // Max 1 event per second per key
 *     flushInterval: 500,  // Flush aggregated events every 500ms
 *     getKey: (event) => event.span_id,
 *     shouldThrottle: (event) => event.event_type.includes('progress')
 * });
 *
 * stream.on('event', (event) => {
 *     const result = throttler.process(event);
 *     if (result.shouldEmit) {
 *         renderEvent(result.event);
 *     }
 * });
 *
 * // Periodically flush aggregated events
 * setInterval(() => {
 *     throttler.flush().forEach(event => renderEvent(event));
 * }, 500);
 * ```
 */

export class EventThrottler {
    /**
     * Create event throttler
     *
     * @param {Object} [options] - Configuration
     * @param {number} [options.interval=1000] - Throttle interval in ms
     * @param {number} [options.flushInterval=1000] - Auto-flush interval in ms
     * @param {Function} [options.getKey] - Key extraction function (event) => string
     * @param {Function} [options.shouldThrottle] - Throttle predicate (event) => boolean
     */
    constructor(options = {}) {
        this.options = {
            interval: 1000,
            flushInterval: 1000,
            getKey: (event) => event.span_id || event.event_id,
            shouldThrottle: (event) => this._defaultShouldThrottle(event),
            ...options
        };

        // State
        this.lastEmit = new Map(); // key -> timestamp
        this.aggregated = new Map(); // key -> event
        this.flushTimer = null;
        this.isDestroyed = false;

        // Stats
        this.stats = {
            eventsProcessed: 0,
            eventsEmitted: 0,
            eventsThrottled: 0,
            eventsFlushed: 0
        };

        // Start auto-flush timer
        this.startAutoFlush();
    }

    /**
     * Process event through throttler
     *
     * @param {Object} event - Event to process
     * @returns {Object} { shouldEmit: boolean, event: Object }
     */
    process(event) {
        if (this.isDestroyed) {
            return { shouldEmit: false, event: null };
        }

        this.stats.eventsProcessed++;

        // Check if this event type should be throttled
        if (!this.options.shouldThrottle(event)) {
            this.stats.eventsEmitted++;
            return { shouldEmit: true, event };
        }

        // Get throttle key
        const key = this.options.getKey(event);
        if (!key) {
            // No key, cannot throttle
            this.stats.eventsEmitted++;
            return { shouldEmit: true, event };
        }

        // Check if we should emit
        const now = Date.now();
        const lastEmitTime = this.lastEmit.get(key) || 0;
        const timeSinceLastEmit = now - lastEmitTime;

        if (timeSinceLastEmit >= this.options.interval) {
            // Emit immediately
            this.lastEmit.set(key, now);
            this.aggregated.delete(key); // Clear any aggregated event
            this.stats.eventsEmitted++;
            return { shouldEmit: true, event };
        } else {
            // Throttle - store latest event
            this.aggregated.set(key, event);
            this.stats.eventsThrottled++;
            return { shouldEmit: false, event: null };
        }
    }

    /**
     * Flush all aggregated events
     *
     * @returns {Array} Array of aggregated events
     */
    flush() {
        const events = Array.from(this.aggregated.values());

        if (events.length > 0) {
            this.stats.eventsFlushed += events.length;

            // Clear aggregated events
            this.aggregated.clear();

            // Update last emit times
            const now = Date.now();
            events.forEach(event => {
                const key = this.options.getKey(event);
                if (key) {
                    this.lastEmit.set(key, now);
                }
            });
        }

        return events;
    }

    /**
     * Start auto-flush timer
     */
    startAutoFlush() {
        if (this.flushTimer) {
            clearInterval(this.flushTimer);
        }

        this.flushTimer = setInterval(() => {
            this.flush();
        }, this.options.flushInterval);
    }

    /**
     * Stop auto-flush timer
     */
    stopAutoFlush() {
        if (this.flushTimer) {
            clearInterval(this.flushTimer);
            this.flushTimer = null;
        }
    }

    /**
     * Default throttle predicate
     *
     * Throttles:
     * - progress events
     * - heartbeat events
     * - status_update events
     *
     * @param {Object} event - Event
     * @returns {boolean} True if should throttle
     */
    _defaultShouldThrottle(event) {
        const eventType = event.event_type || '';

        const throttleTypes = [
            'progress',
            'heartbeat',
            'status_update',
            'work_item_progress',
            'checkpoint_progress'
        ];

        return throttleTypes.some(type => eventType.toLowerCase().includes(type.toLowerCase()));
    }

    /**
     * Get statistics
     *
     * @returns {Object} Statistics
     */
    getStats() {
        return {
            ...this.stats,
            aggregatedCount: this.aggregated.size,
            throttleRatio: this.stats.eventsProcessed > 0
                ? (this.stats.eventsThrottled / this.stats.eventsProcessed * 100).toFixed(1)
                : 0
        };
    }

    /**
     * Reset statistics
     */
    resetStats() {
        this.stats = {
            eventsProcessed: 0,
            eventsEmitted: 0,
            eventsThrottled: 0,
            eventsFlushed: 0
        };
    }

    /**
     * Clear all state
     */
    clear() {
        this.lastEmit.clear();
        this.aggregated.clear();
    }

    /**
     * Destroy throttler
     */
    destroy() {
        this.isDestroyed = true;
        this.stopAutoFlush();
        this.clear();
    }
}

/**
 * DedupingEventThrottler - Throttler with deduplication
 *
 * Extends EventThrottler with event deduplication based on content hash.
 */
export class DedupingEventThrottler extends EventThrottler {
    constructor(options = {}) {
        super(options);
        this.seenHashes = new Set(); // Event content hashes
        this.hashTTL = options.hashTTL || 60000; // Hash TTL in ms
        this.hashTimestamps = new Map(); // hash -> timestamp
    }

    /**
     * Process event with deduplication
     *
     * @param {Object} event - Event to process
     * @returns {Object} { shouldEmit: boolean, event: Object, isDuplicate: boolean }
     */
    process(event) {
        // First check for duplicates
        const hash = this._hashEvent(event);
        const isDuplicate = this.seenHashes.has(hash);

        if (isDuplicate) {
            this.stats.eventsThrottled++;
            return { shouldEmit: false, event: null, isDuplicate: true };
        }

        // Add to seen hashes
        this.seenHashes.add(hash);
        this.hashTimestamps.set(hash, Date.now());

        // Clean up old hashes periodically
        this._cleanupOldHashes();

        // Process through normal throttling
        const result = super.process(event);
        return { ...result, isDuplicate: false };
    }

    /**
     * Hash event for deduplication
     *
     * @param {Object} event - Event
     * @returns {string} Event hash
     */
    _hashEvent(event) {
        // Create hash from event_type, span_id, and payload
        const key = JSON.stringify({
            type: event.event_type,
            span: event.span_id,
            seq: event.seq
        });
        return key;
    }

    /**
     * Clean up old hashes (expired TTL)
     */
    _cleanupOldHashes() {
        const now = Date.now();
        const expiredHashes = [];

        this.hashTimestamps.forEach((timestamp, hash) => {
            if (now - timestamp > this.hashTTL) {
                expiredHashes.push(hash);
            }
        });

        expiredHashes.forEach(hash => {
            this.seenHashes.delete(hash);
            this.hashTimestamps.delete(hash);
        });
    }

    /**
     * Clear all state including seen hashes
     */
    clear() {
        super.clear();
        this.seenHashes.clear();
        this.hashTimestamps.clear();
    }
}

// Export as default
export default EventThrottler;

// Also expose globally for non-module usage
if (typeof window !== 'undefined') {
    window.EventThrottler = EventThrottler;
    window.DedupingEventThrottler = DedupingEventThrottler;
}
