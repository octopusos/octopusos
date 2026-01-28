/**
 * ApiClient - Unified API request wrapper
 *
 * Features:
 * - Automatic timeout
 * - Error normalization
 * - Request ID tracking
 * - Retry logic
 *
 * v0.3.2 - WebUI 100% Coverage Sprint
 */

class ApiClient {
    constructor(baseUrl = '', defaultTimeout = 30000) {
        this.baseUrl = baseUrl;
        this.defaultTimeout = defaultTimeout;
        this.requestIdCounter = 0;
    }

    /**
     * Generate unique request ID
     */
    generateRequestId() {
        this.requestIdCounter++;
        const timestamp = Date.now();
        return `req_${timestamp}_${this.requestIdCounter}`;
    }

    /**
     * Normalize error response
     */
    normalizeError(error, requestId) {
        // Network errors
        if (error.name === 'AbortError') {
            return {
                ok: false,
                error: 'timeout',
                message: 'Request timeout',
                request_id: requestId,
                timestamp: new Date().toISOString(),
            };
        }

        if (error.message === 'Failed to fetch' || error.message.includes('NetworkError')) {
            return {
                ok: false,
                error: 'network_error',
                message: 'Network connection failed',
                request_id: requestId,
                timestamp: new Date().toISOString(),
            };
        }

        // HTTP errors
        if (error.status) {
            const errorMap = {
                400: 'bad_request',
                401: 'unauthorized',
                403: 'forbidden',
                404: 'not_found',
                429: 'rate_limited',
                500: 'internal_error',
                502: 'bad_gateway',
                503: 'service_unavailable',
            };

            return {
                ok: false,
                error: errorMap[error.status] || 'http_error',
                message: error.message || `HTTP ${error.status}`,
                status: error.status,
                request_id: requestId,
                timestamp: new Date().toISOString(),
                detail: error.detail,
            };
        }

        // Generic error
        return {
            ok: false,
            error: 'unknown_error',
            message: error.message || 'An unknown error occurred',
            request_id: requestId,
            timestamp: new Date().toISOString(),
        };
    }

    /**
     * Make HTTP request with timeout and error handling
     */
    async request(url, options = {}) {
        const requestId = options.requestId || this.generateRequestId();
        const timeout = options.timeout || this.defaultTimeout;

        // Create abort controller for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);

        try {
            // Merge options
            const fetchOptions = {
                ...options,
                signal: controller.signal,
                headers: {
                    'Content-Type': 'application/json',
                    'X-Request-ID': requestId,
                    ...options.headers,
                },
            };

            // Make request
            const response = await fetch(this.baseUrl + url, fetchOptions);

            clearTimeout(timeoutId);

            // Parse response
            let data;
            const contentType = response.headers.get('content-type');

            if (contentType && contentType.includes('application/json')) {
                data = await response.json();
            } else {
                data = await response.text();
            }

            // Check HTTP status
            if (!response.ok) {
                const error = new Error(data.detail || data.message || `HTTP ${response.status}`);
                error.status = response.status;
                error.detail = data.detail;
                throw error;
            }

            // Success response
            return {
                ok: true,
                data: data,
                request_id: requestId,
                timestamp: new Date().toISOString(),
                status: response.status,
            };

        } catch (error) {
            clearTimeout(timeoutId);
            return this.normalizeError(error, requestId);
        }
    }

    /**
     * Convenience methods
     */
    async get(url, options = {}) {
        return this.request(url, { ...options, method: 'GET' });
    }

    async post(url, data, options = {}) {
        return this.request(url, {
            ...options,
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async put(url, data, options = {}) {
        return this.request(url, {
            ...options,
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async patch(url, data, options = {}) {
        return this.request(url, {
            ...options,
            method: 'PATCH',
            body: JSON.stringify(data),
        });
    }

    async delete(url, options = {}) {
        return this.request(url, { ...options, method: 'DELETE' });
    }

    /**
     * Retry wrapper
     */
    async withRetry(fn, retries = 3, delay = 1000) {
        let lastError;

        for (let i = 0; i < retries; i++) {
            try {
                const result = await fn();
                if (result.ok) {
                    return result;
                }
                lastError = result;

                // Don't retry on client errors (4xx)
                if (result.status && result.status >= 400 && result.status < 500) {
                    return result;
                }
            } catch (error) {
                lastError = this.normalizeError(error, this.generateRequestId());
            }

            // Wait before retry (exponential backoff)
            if (i < retries - 1) {
                await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, i)));
            }
        }

        return lastError;
    }
}

// Create global instance
window.apiClient = new ApiClient();
