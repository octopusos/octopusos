/**
 * FilterBar - Generic filter bar component
 *
 * Features:
 * - Query input (search box)
 * - Time range selector
 * - Level/Status dropdown
 * - Custom filters
 * - Change callback
 *
 * v0.3.2 - WebUI 100% Coverage Sprint
 */

class FilterBar {
    constructor(container, options = {}) {
        this.container = typeof container === 'string'
            ? document.querySelector(container)
            : container;

        this.options = {
            filters: options.filters || [],
            onChange: options.onChange || null,
            debounceMs: options.debounceMs || 300,
            ...options,
        };

        this.state = {};
        this.debounceTimers = {};

        this.render();
    }

    /**
     * Render the filter bar
     */
    render() {
        this.container.innerHTML = '';
        this.container.className = 'filter-bar';

        this.options.filters.forEach(filter => {
            const filterEl = this.renderFilter(filter);
            this.container.appendChild(filterEl);
        });
    }

    /**
     * Render a single filter
     */
    renderFilter(filter) {
        const wrapper = document.createElement('div');
        wrapper.className = 'filter-item';

        // Label (optional)
        if (filter.label) {
            const label = document.createElement('label');
            label.textContent = filter.label;
            label.className = 'filter-label';
            wrapper.appendChild(label);
        }

        // Input element
        let input;

        switch (filter.type) {
            case 'text':
            case 'search':
                input = this.renderTextInput(filter);
                break;

            case 'select':
            case 'dropdown':
                input = this.renderSelect(filter);
                break;

            case 'date-range':
            case 'time-range':
                input = this.renderTimeRange(filter);
                break;

            case 'multi-select':
                input = this.renderMultiSelect(filter);
                break;

            case 'button':
                input = this.renderButton(filter);
                break;

            default:
                console.warn(`Unknown filter type: ${filter.type}`);
                return wrapper;
        }

        wrapper.appendChild(input);
        return wrapper;
    }

    /**
     * Render text input
     */
    renderTextInput(filter) {
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'filter-input';
        input.placeholder = filter.placeholder || 'Search...';

        if (filter.value) {
            input.value = filter.value;
            this.state[filter.key] = filter.value;
        }

        input.oninput = (e) => {
            this.state[filter.key] = e.target.value;
            this.debouncedOnChange(filter.key);
        };

        return input;
    }

    /**
     * Render select dropdown
     */
    renderSelect(filter) {
        const select = document.createElement('select');
        select.className = 'filter-select';

        // Options
        (filter.options || []).forEach(option => {
            const optEl = document.createElement('option');
            optEl.value = option.value;
            optEl.textContent = option.label || option.value;

            if (filter.value === option.value) {
                optEl.selected = true;
                this.state[filter.key] = option.value;
            }

            select.appendChild(optEl);
        });

        select.onchange = (e) => {
            this.state[filter.key] = e.target.value;
            this.triggerOnChange();
        };

        return select;
    }

    /**
     * Render time range selector
     */
    renderTimeRange(filter) {
        const container = document.createElement('div');
        container.className = 'filter-time-range';

        // Preset buttons
        const presets = filter.presets || [
            { label: 'Last 1h', value: 3600 },
            { label: 'Last 24h', value: 86400 },
            { label: 'Last 7d', value: 604800 },
            { label: 'Custom', value: 'custom' },
        ];

        const buttonGroup = document.createElement('div');
        buttonGroup.className = 'time-range-buttons';

        presets.forEach((preset, index) => {
            const btn = document.createElement('button');
            btn.className = 'time-range-btn';
            btn.textContent = preset.label;

            if (index === 0 && !filter.value) {
                btn.classList.add('active');
                this.state[filter.key] = preset.value;
            } else if (filter.value === preset.value) {
                btn.classList.add('active');
                this.state[filter.key] = preset.value;
            }

            btn.onclick = () => {
                // Remove active class from all buttons
                buttonGroup.querySelectorAll('.time-range-btn').forEach(b => {
                    b.classList.remove('active');
                });

                // Add active class to clicked button
                btn.classList.add('active');

                if (preset.value === 'custom') {
                    this.state[filter.key] = 'custom';
                    customInputs.style.display = 'flex';
                } else {
                    this.state[filter.key] = preset.value;
                    customInputs.style.display = 'none';
                    this.triggerOnChange();
                }
            };

            buttonGroup.appendChild(btn);
        });

        container.appendChild(buttonGroup);

        // Custom inputs (hidden by default)
        const customInputs = document.createElement('div');
        customInputs.className = 'time-range-custom';
        customInputs.style.display = 'none';

        const sinceInput = document.createElement('input');
        sinceInput.type = 'datetime-local';
        sinceInput.className = 'filter-input';

        const untilInput = document.createElement('input');
        untilInput.type = 'datetime-local';
        untilInput.className = 'filter-input';

        const applyBtn = document.createElement('button');
        applyBtn.textContent = 'Apply';
        applyBtn.className = 'time-range-apply';
        applyBtn.onclick = () => {
            this.state[filter.key] = {
                since: sinceInput.value,
                until: untilInput.value,
            };
            this.triggerOnChange();
        };

        customInputs.appendChild(sinceInput);
        customInputs.appendChild(document.createTextNode(' to '));
        customInputs.appendChild(untilInput);
        customInputs.appendChild(applyBtn);

        container.appendChild(customInputs);

        return container;
    }

    /**
     * Render multi-select
     */
    renderMultiSelect(filter) {
        const container = document.createElement('div');
        container.className = 'filter-multi-select';

        const selected = filter.value || [];
        this.state[filter.key] = selected;

        (filter.options || []).forEach(option => {
            const label = document.createElement('label');
            label.className = 'multi-select-option';

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.value = option.value;
            checkbox.checked = selected.includes(option.value);

            checkbox.onchange = (e) => {
                if (e.target.checked) {
                    if (!this.state[filter.key].includes(option.value)) {
                        this.state[filter.key].push(option.value);
                    }
                } else {
                    this.state[filter.key] = this.state[filter.key].filter(v => v !== option.value);
                }
                this.triggerOnChange();
            };

            label.appendChild(checkbox);
            label.appendChild(document.createTextNode(' ' + (option.label || option.value)));
            container.appendChild(label);
        });

        return container;
    }

    /**
     * Render button
     */
    renderButton(filter) {
        const button = document.createElement('button');
        button.className = 'filter-button';
        button.textContent = filter.label || 'Button';

        if (filter.onClick) {
            button.onclick = () => filter.onClick(this.state);
        }

        return button;
    }

    /**
     * Trigger onChange callback (debounced for text inputs)
     */
    debouncedOnChange(key) {
        if (this.debounceTimers[key]) {
            clearTimeout(this.debounceTimers[key]);
        }

        this.debounceTimers[key] = setTimeout(() => {
            this.triggerOnChange();
        }, this.options.debounceMs);
    }

    /**
     * Trigger onChange callback immediately
     */
    triggerOnChange() {
        if (this.options.onChange) {
            this.options.onChange(this.state);
        }
    }

    /**
     * Get current filter state
     */
    getState() {
        return { ...this.state };
    }

    /**
     * Set filter state
     */
    setState(state) {
        this.state = { ...state };
        this.render();
    }

    /**
     * Reset filters
     */
    reset() {
        this.state = {};
        this.render();
        this.triggerOnChange();
    }

    /**
     * Destroy component (cleanup)
     */
    destroy() {
        // Remove event listeners if any
        // Clear container
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// Export to window
window.FilterBar = FilterBar;
