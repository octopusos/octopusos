/**
 * Toast - Toast notification component
 *
 * Features:
 * - Success/Error/Warning/Info types
 * - Auto-dismiss
 * - Manual dismiss
 * - Stacking
 * - Position configuration
 *
 * v0.3.2 - WebUI 100% Coverage Sprint
 */

class ToastManager {
    constructor(options = {}) {
        this.options = {
            position: options.position || 'top-right',
            duration: options.duration || 3000,
            maxToasts: options.maxToasts || 5,
            ...options,
        };

        this.toasts = [];
        this.container = null;
        this.init();
    }

    /**
     * Initialize toast container
     */
    init() {
        this.container = document.createElement('div');
        this.container.className = `toast-container ${this.options.position}`;
        document.body.appendChild(this.container);
    }

    /**
     * Show toast
     */
    show(message, type = 'info', duration = null) {
        // Remove oldest toast if at max capacity
        if (this.toasts.length >= this.options.maxToasts) {
            this.remove(this.toasts[0]);
        }

        const toast = this.createToast(message, type, duration);
        this.toasts.push(toast);
        this.container.appendChild(toast.element);

        // Trigger animation
        setTimeout(() => {
            toast.element.classList.add('show');
        }, 10);

        // Auto-dismiss
        if (toast.duration > 0) {
            toast.timer = setTimeout(() => {
                this.remove(toast);
            }, toast.duration);
        }

        return toast;
    }

    /**
     * Create toast element
     */
    createToast(message, type, duration) {
        const toast = {
            id: Date.now() + Math.random(),
            type: type,
            message: message,
            duration: duration !== null ? duration : this.options.duration,
            element: null,
            timer: null,
        };

        // Toast element
        const element = document.createElement('div');
        element.className = `toast toast-${type}`;
        element.dataset.toastId = toast.id;

        // Icon
        const icon = document.createElement('div');
        icon.className = 'toast-icon';
        icon.innerHTML = this.getIcon(type);
        element.appendChild(icon);

        // Content
        const content = document.createElement('div');
        content.className = 'toast-content';

        const messageEl = document.createElement('div');
        messageEl.className = 'toast-message';
        messageEl.textContent = message;
        content.appendChild(messageEl);

        element.appendChild(content);

        // Close button
        const closeBtn = document.createElement('button');
        closeBtn.className = 'toast-close';
        closeBtn.innerHTML = '×';
        closeBtn.onclick = () => this.remove(toast);
        element.appendChild(closeBtn);

        toast.element = element;
        return toast;
    }

    /**
     * Get icon for toast type
     */
    getIcon(type) {
        const icons = {
            success: 'check_circle',
            error: 'cancel',
            warning: 'warning',
            info: 'info',
        };
        const iconName = icons[type] || icons.info;
        return `<span class="material-icons">${iconName}</span>`;
    }

    /**
     * Remove toast
     */
    remove(toast) {
        if (!toast || !toast.element) {
            return;
        }

        // Clear timer
        if (toast.timer) {
            clearTimeout(toast.timer);
        }

        // Fade out
        toast.element.classList.remove('show');

        // Remove from DOM after animation
        setTimeout(() => {
            if (toast.element && toast.element.parentNode) {
                toast.element.parentNode.removeChild(toast.element);
            }

            // Remove from array
            this.toasts = this.toasts.filter(t => t.id !== toast.id);
        }, 300);
    }

    /**
     * Remove all toasts
     */
    clear() {
        this.toasts.forEach(toast => this.remove(toast));
    }

    /**
     * Convenience methods
     */
    success(message, duration) {
        return this.show(message, 'success', duration);
    }

    error(message, duration) {
        return this.show(message, 'error', duration);
    }

    warning(message, duration) {
        return this.show(message, 'warning', duration);
    }

    info(message, duration) {
        return this.show(message, 'info', duration);
    }
}

// Create global instance
window.toastManager = new ToastManager();

// Global function for convenience
window.showToast = (message, type, duration) => {
    return window.toastManager.show(message, type, duration);
};

// Export Toast object for convenience (alias to toastManager)
window.Toast = window.toastManager;
