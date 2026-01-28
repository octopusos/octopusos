/**
 * Dialog Component - Modern replacement for native alert() and confirm()
 *
 * Usage:
 *   await Dialog.alert('Message here');
 *   const result = await Dialog.confirm('Are you sure?');
 *
 * Features:
 *   - Promise-based API
 *   - Keyboard support (Enter/Escape)
 *   - Backdrop click to dismiss (for alerts)
 *   - Customizable buttons
 *   - HTML content support
 */

class Dialog {
    /**
     * Show an alert dialog (single OK button)
     * @param {string} message - Message to display (supports HTML)
     * @param {Object} options - Optional configuration
     * @returns {Promise<void>}
     */
    static alert(message, options = {}) {
        const {
            title = 'Notice',
            confirmText = 'OK',
            confirmClass = 'btn-primary'
        } = options;

        return new Promise((resolve) => {
            const dialog = this._createDialog({
                title,
                message,
                buttons: [
                    {
                        text: confirmText,
                        className: confirmClass,
                        onClick: () => {
                            this._closeDialog(dialog);
                            resolve();
                        }
                    }
                ],
                onBackdropClick: () => {
                    this._closeDialog(dialog);
                    resolve();
                }
            });
        });
    }

    /**
     * Show a confirm dialog (Cancel + OK buttons)
     * @param {string} message - Message to display (supports HTML)
     * @param {Object} options - Optional configuration
     * @returns {Promise<boolean>} - true if confirmed, false if cancelled
     */
    static confirm(message, options = {}) {
        const {
            title = 'Confirm',
            cancelText = 'Cancel',
            confirmText = 'OK',
            confirmClass = 'btn-primary',
            danger = false
        } = options;

        return new Promise((resolve) => {
            const dialog = this._createDialog({
                title,
                message,
                buttons: [
                    {
                        text: cancelText,
                        className: 'btn-secondary',
                        onClick: () => {
                            this._closeDialog(dialog);
                            resolve(false);
                        }
                    },
                    {
                        text: confirmText,
                        className: danger ? 'btn-danger' : confirmClass,
                        onClick: () => {
                            this._closeDialog(dialog);
                            resolve(true);
                        }
                    }
                ],
                onBackdropClick: () => {
                    this._closeDialog(dialog);
                    resolve(false);
                },
                onEscape: () => {
                    this._closeDialog(dialog);
                    resolve(false);
                }
            });
        });
    }

    /**
     * Show a prompt dialog (input with Cancel + OK buttons)
     * @param {string} message - Message to display
     * @param {Object} options - Optional configuration
     * @returns {Promise<string|null>} - input value if confirmed, null if cancelled
     */
    static prompt(message, options = {}) {
        const {
            title = 'Input',
            cancelText = 'Cancel',
            confirmText = 'OK',
            defaultValue = '',
            placeholder = '',
            inputType = 'text'
        } = options;

        return new Promise((resolve) => {
            const dialog = this._createPromptDialog({
                title,
                message,
                defaultValue,
                placeholder,
                inputType,
                buttons: [
                    {
                        text: cancelText,
                        className: 'btn-secondary',
                        onClick: () => {
                            this._closeDialog(dialog);
                            resolve(null);
                        }
                    },
                    {
                        text: confirmText,
                        className: 'btn-primary',
                        onClick: () => {
                            const input = dialog.querySelector('.dialog-input');
                            const value = input ? input.value : '';
                            this._closeDialog(dialog);
                            resolve(value);
                        }
                    }
                ],
                onBackdropClick: () => {
                    this._closeDialog(dialog);
                    resolve(null);
                },
                onEscape: () => {
                    this._closeDialog(dialog);
                    resolve(null);
                }
            });
        });
    }

    /**
     * Create and show dialog DOM
     * @private
     */
    static _createDialog({ title, message, buttons, onBackdropClick, onEscape }) {
        // Create backdrop
        const backdrop = document.createElement('div');
        backdrop.className = 'dialog-backdrop';

        // Create dialog container
        const dialog = document.createElement('div');
        dialog.className = 'dialog-container';

        // Build dialog HTML
        dialog.innerHTML = `
            <div class="dialog-content">
                <div class="dialog-header">
                    <h3 class="dialog-title">${this._escapeHtml(title)}</h3>
                </div>
                <div class="dialog-body">
                    <p class="dialog-message">${message}</p>
                </div>
                <div class="dialog-footer">
                    ${buttons.map((btn, idx) => `
                        <button class="dialog-btn ${btn.className}" data-btn-index="${idx}">
                            ${this._escapeHtml(btn.text)}
                        </button>
                    `).join('')}
                </div>
            </div>
        `;

        // Add event listeners
        buttons.forEach((btn, idx) => {
            const btnEl = dialog.querySelector(`[data-btn-index="${idx}"]`);
            btnEl.addEventListener('click', btn.onClick);
        });

        // Backdrop click
        if (onBackdropClick) {
            backdrop.addEventListener('click', (e) => {
                if (e.target === backdrop) {
                    onBackdropClick();
                }
            });
        }

        // Keyboard events
        const handleKeyDown = (e) => {
            if (e.key === 'Escape' && onEscape) {
                onEscape();
                document.removeEventListener('keydown', handleKeyDown);
            } else if (e.key === 'Enter' && buttons.length > 0) {
                // Enter triggers the last button (primary action)
                buttons[buttons.length - 1].onClick();
                document.removeEventListener('keydown', handleKeyDown);
            }
        };
        document.addEventListener('keydown', handleKeyDown);

        // Append to body
        backdrop.appendChild(dialog);
        document.body.appendChild(backdrop);

        // Trigger animation
        requestAnimationFrame(() => {
            backdrop.classList.add('dialog-backdrop--visible');
            dialog.classList.add('dialog-container--visible');
        });

        return backdrop;
    }

    /**
     * Create and show prompt dialog with input field
     * @private
     */
    static _createPromptDialog({ title, message, defaultValue, placeholder, inputType, buttons, onBackdropClick, onEscape }) {
        // Create backdrop
        const backdrop = document.createElement('div');
        backdrop.className = 'dialog-backdrop';

        // Create dialog container
        const dialog = document.createElement('div');
        dialog.className = 'dialog-container';

        // Build dialog HTML with input field
        dialog.innerHTML = `
            <div class="dialog-content">
                <div class="dialog-header">
                    <h3 class="dialog-title">${this._escapeHtml(title)}</h3>
                </div>
                <div class="dialog-body">
                    <p class="dialog-message">${this._escapeHtml(message)}</p>
                    <input
                        type="${inputType}"
                        class="dialog-input"
                        value="${this._escapeHtml(defaultValue)}"
                        placeholder="${this._escapeHtml(placeholder)}"
                    />
                </div>
                <div class="dialog-footer">
                    ${buttons.map((btn, idx) => `
                        <button class="dialog-btn ${btn.className}" data-btn-index="${idx}">
                            ${this._escapeHtml(btn.text)}
                        </button>
                    `).join('')}
                </div>
            </div>
        `;

        // Add event listeners
        buttons.forEach((btn, idx) => {
            const btnEl = dialog.querySelector(`[data-btn-index="${idx}"]`);
            btnEl.addEventListener('click', btn.onClick);
        });

        // Backdrop click
        if (onBackdropClick) {
            backdrop.addEventListener('click', (e) => {
                if (e.target === backdrop) {
                    onBackdropClick();
                }
            });
        }

        // Keyboard events
        const input = dialog.querySelector('.dialog-input');
        const handleKeyDown = (e) => {
            if (e.key === 'Escape' && onEscape) {
                onEscape();
                document.removeEventListener('keydown', handleKeyDown);
            } else if (e.key === 'Enter' && buttons.length > 0) {
                // Enter triggers the last button (primary action)
                buttons[buttons.length - 1].onClick();
                document.removeEventListener('keydown', handleKeyDown);
            }
        };
        document.addEventListener('keydown', handleKeyDown);

        // Append to body
        backdrop.appendChild(dialog);
        document.body.appendChild(backdrop);

        // Trigger animation
        requestAnimationFrame(() => {
            backdrop.classList.add('dialog-backdrop--visible');
            dialog.classList.add('dialog-container--visible');
            // Focus input field after animation
            if (input) {
                setTimeout(() => input.focus(), 100);
            }
        });

        return backdrop;
    }

    /**
     * Close and remove dialog
     * @private
     */
    static _closeDialog(backdrop) {
        backdrop.classList.remove('dialog-backdrop--visible');
        const dialog = backdrop.querySelector('.dialog-container');
        if (dialog) {
            dialog.classList.remove('dialog-container--visible');
        }

        setTimeout(() => {
            backdrop.remove();
        }, 300); // Match CSS transition duration
    }

    /**
     * Escape HTML to prevent XSS (for title and button text)
     * @private
     */
    static _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Dialog;
}
