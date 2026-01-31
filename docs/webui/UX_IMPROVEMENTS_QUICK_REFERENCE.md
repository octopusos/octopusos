# WebUI UX Improvements - Quick Reference Guide

**Version:** v0.3.2
**Last Updated:** 2026-01-31

This is a quick reference guide for developers working with the new UX improvement utilities.

---

## Table of Contents

1. [ViewStateManager](#viewstatemanager)
2. [FormValidator](#formvalidator)
3. [Enhanced Toast](#enhanced-toast)
4. [VirtualList](#virtuallist)
5. [Session Expiry Handling](#session-expiry-handling)
6. [Common Patterns](#common-patterns)

---

## ViewStateManager

**Purpose:** Persist view state across navigation (filters, scroll position, selections)

### Basic Usage

```javascript
// Create state manager
const stateManager = new ViewStateManager('myView');

// Save state
stateManager.saveState({
    filters: { status: 'active' },
    scrollTop: 100,
    selectedId: '123'
});

// Restore state
const state = stateManager.restoreState();
// Returns: { filters: { status: 'active' }, scrollTop: 100, selectedId: '123' }
```

### Advanced Options

```javascript
const stateManager = new ViewStateManager('myView', {
    useUrlParams: true,      // Sync to URL query params
    maxAge: 3600000,         // State expires after 1 hour
    deepMerge: true,         // Deep merge nested objects
    autoSave: false          // Auto-save on changes
});
```

### Common Patterns

```javascript
// In view constructor
constructor(container) {
    this.stateManager = new ViewStateManager('history');
    this.filters = this.stateManager.restoreState({ filters: {} }).filters;
}

// On filter change
handleFilterChange(key, value) {
    this.filters[key] = value;
    this.stateManager.updateState({ filters: this.filters });
    this.loadData();
}

// On view destroy
destroy() {
    const scrollTop = this.container.scrollTop;
    this.stateManager.updateState({ scrollTop });
}
```

### Utility Methods

```javascript
// Update partial state
stateManager.updateState({ scrollTop: 200 });

// Clear state
stateManager.clearState();

// Export state as JSON
const json = stateManager.exportState();

// Import state from JSON
stateManager.importState(json);

// Get all saved views
const views = ViewStateManager.getAllSavedViews();

// Clear all states
ViewStateManager.clearAllStates();
```

---

## FormValidator

**Purpose:** Real-time form validation with visual feedback

### Basic Usage

```javascript
const validator = new FormValidator(formElement, {
    fields: {
        email: {
            rules: ['required', 'email'],
            message: 'Please enter a valid email'
        },
        password: {
            rules: ['required', 'minLength:8']
        }
    }
});
```

### Built-in Validators

| Validator | Usage | Description |
|-----------|-------|-------------|
| `required` | `['required']` | Field must have value |
| `email` | `['email']` | Valid email format |
| `url` | `['url']` | Valid URL format |
| `minLength:N` | `['minLength:8']` | Minimum length |
| `maxLength:N` | `['maxLength:100']` | Maximum length |
| `min:N` | `['min:18']` | Minimum number |
| `max:N` | `['max:120']` | Maximum number |
| `pattern:regex` | `['pattern:^[A-Z]']` | Custom regex |
| `match:field` | `['match:password']` | Match another field |
| `number` | `['number']` | Valid number |
| `integer` | `['integer']` | Whole number |
| `alpha` | `['alpha']` | Letters only |
| `alphanum` | `['alphanum']` | Letters and numbers |

### Custom Validators

```javascript
const validator = new FormValidator(form, {
    fields: {
        username: {
            rules: ['required', 'checkAvailable']
        }
    },
    customValidators: {
        checkAvailable: async (value) => {
            const response = await fetch(`/api/check?name=${value}`);
            const data = await response.json();
            if (!data.available) {
                return 'Username is already taken';
            }
            return null; // No error
        }
    }
});
```

### Options

```javascript
const validator = new FormValidator(form, {
    debounceDelay: 300,      // Delay before validation (ms)
    validateOnBlur: true,    // Validate on blur
    validateOnInput: true,   // Validate on input
    showSuccess: true,       // Show success state
    onChange: (isValid, errors) => {
        submitButton.disabled = !isValid;
    }
});
```

### Methods

```javascript
// Validate all fields
const isValid = await validator.validateAll();

// Validate single field
await validator.validateField('email');

// Get errors
const errors = validator.getErrors();
// Returns: { email: 'Please enter a valid email' }

// Check if form is valid
if (validator.isFormValid()) {
    submitForm();
}

// Reset validation
validator.reset();

// Add field dynamically
validator.addField('phone', {
    rules: ['required', 'pattern:^\\+?[0-9]{10,}$']
});

// Remove field
validator.removeField('phone');

// Destroy validator
validator.destroy();
```

---

## Enhanced Toast

**Purpose:** Unified error and success notifications

### Basic Usage

```javascript
// Success
Toast.success('Changes saved successfully');

// Error
Toast.error('Failed to save changes');

// Warning
Toast.warning('This action cannot be undone');

// Info
Toast.info('New version available');
```

### With Options

```javascript
Toast.error('Failed to save', 5000, {
    details: 'Network connection timed out',
    action: {
        label: 'Retry',
        onClick: () => saveChanges(),
        dismiss: true  // Dismiss toast after action
    }
});
```

### API Error Handling

```javascript
// Automatic error categorization and retry button
const response = await apiClient.get('/api/data');
if (!response.ok) {
    Toast.showApiError(response, () => loadData());
    return;
}
```

### Error with Retry

```javascript
Toast.showErrorWithRetry(
    'Failed to load data',
    () => loadData(),        // Retry callback
    'Server returned 500'    // Details
);
```

### Advanced Usage

```javascript
// Object parameter
Toast.show({
    message: 'Operation completed',
    type: 'success',
    duration: 3000,
    details: 'All records updated',
    action: {
        label: 'View Details',
        onClick: () => showDetails(),
        dismiss: false
    }
});

// No auto-dismiss
Toast.error('Critical error', 0);  // 0 = stay until manual dismiss

// Custom duration
Toast.success('Saved', 1000);  // 1 second
```

### Methods

```javascript
// Clear all toasts
Toast.clear();

// Remove specific toast
const toast = Toast.info('Loading...');
Toast.remove(toast);
```

---

## VirtualList

**Purpose:** High-performance rendering for large lists (1000+ items)

### Basic Usage

```javascript
const virtualList = new VirtualList({
    container: document.getElementById('list-container'),
    itemHeight: 80,
    renderItem: (item, index) => {
        return `<div class="item">${item.name}</div>`;
    }
});

virtualList.setItems(largeDataArray);
```

### Options

```javascript
const virtualList = new VirtualList({
    container: element,
    itemHeight: 80,          // Fixed height per item
    overscan: 5,             // Extra items to render above/below
    renderItem: (item, index) => {
        return `<div>...</div>`;
    },
    onScroll: (startIndex, endIndex) => {
        console.log(`Visible: ${startIndex}-${endIndex}`);
    }
});
```

### Methods

```javascript
// Set items
virtualList.setItems(items);

// Append items
virtualList.appendItems(newItems);

// Update specific item
virtualList.updateItem(5, newItemData);

// Scroll to index
virtualList.scrollToIndex(100, true);  // true = smooth scroll

// Scroll to top
virtualList.scrollToTop();

// Scroll to bottom
virtualList.scrollToBottom();

// Get scroll info
const info = virtualList.getScrollInfo();
// Returns: { startIndex, endIndex, scrollTop, scrollPercentage }

// Check if near bottom
if (virtualList.isNearBottom(100)) {
    loadMoreItems();
}

// Clear all items
virtualList.clear();

// Destroy
virtualList.destroy();
```

### Integration Example

```javascript
class MyView {
    constructor(container) {
        this.container = container;
        this.virtualList = null;
    }

    render() {
        const listContainer = this.container.querySelector('.list');

        this.virtualList = new VirtualList({
            container: listContainer,
            itemHeight: 80,
            renderItem: (item, index) => this.renderItem(item, index),
            onScroll: (start, end) => {
                // Save scroll position for state management
                this.stateManager.updateState({
                    scrollTop: this.virtualList.scrollContainer.scrollTop
                });
            }
        });

        this.loadData();
    }

    async loadData() {
        const response = await apiClient.get('/api/data');
        if (response.ok) {
            this.virtualList.setItems(response.data.items);
        }
    }

    renderItem(item, index) {
        return `
            <div class="item" onclick="myView.selectItem(${index})">
                <h3>${item.title}</h3>
                <p>${item.description}</p>
            </div>
        `;
    }

    destroy() {
        if (this.virtualList) {
            this.virtualList.destroy();
        }
    }
}
```

---

## Session Expiry Handling

**Purpose:** Friendly handling of 401 errors

### Automatic Handling

```javascript
// ApiClient automatically handles 401 errors
// No code changes needed in most cases

const response = await apiClient.get('/api/data');
// If 401, shows session expired dialog automatically
```

### Custom Handler

```javascript
// Set custom handler
apiClient.onSessionExpired(() => {
    // Custom logic (e.g., refresh token)
    refreshToken().then(() => {
        apiClient.resetSessionExpired();
        retryLastRequest();
    });
});
```

### Skip Session Expiry Check

```javascript
// For specific requests (e.g., health checks)
apiClient.get('/api/health', {
    skipSessionExpiry: true
});
```

### Manual Trigger

```javascript
// Manually trigger session expired dialog
apiClient.handleSessionExpired();

// Reset flag (allow showing again)
apiClient.resetSessionExpired();
```

---

## Common Patterns

### Pattern 1: Stateful View with Virtual Scrolling

```javascript
class MyView {
    constructor(container) {
        this.container = container;
        this.stateManager = new ViewStateManager('myView');
        this.virtualList = null;
        this.filters = this.stateManager.restoreState({ filters: {} }).filters;

        this.init();
    }

    async init() {
        this.render();
        await this.loadData();

        // Restore scroll position
        const state = this.stateManager.getCurrentState();
        if (state.scrollTop) {
            setTimeout(() => {
                this.virtualList.scrollContainer.scrollTop = state.scrollTop;
            }, 100);
        }
    }

    render() {
        this.container.innerHTML = `
            <div class="filters">
                <input id="filter-name" value="${this.filters.name || ''}">
            </div>
            <div id="list-container" style="height: 500px;"></div>
        `;

        // Setup virtual list
        this.virtualList = new VirtualList({
            container: document.getElementById('list-container'),
            itemHeight: 80,
            renderItem: (item) => this.renderItem(item),
            onScroll: () => {
                this.stateManager.updateState({
                    scrollTop: this.virtualList.scrollContainer.scrollTop
                });
            }
        });

        // Setup filter
        document.getElementById('filter-name').addEventListener('input', (e) => {
            this.filters.name = e.target.value;
            this.stateManager.updateState({ filters: this.filters });
            this.loadData();
        });
    }

    async loadData() {
        const response = await apiClient.get('/api/data', {
            params: this.filters
        });

        if (!response.ok) {
            Toast.showApiError(response, () => this.loadData());
            return;
        }

        this.virtualList.setItems(response.data.items);
    }

    renderItem(item) {
        return `<div class="item">${item.name}</div>`;
    }

    destroy() {
        if (this.virtualList) {
            this.virtualList.destroy();
        }
    }
}
```

### Pattern 2: Form with Validation

```javascript
class FormView {
    constructor(container) {
        this.container = container;
        this.validator = null;
        this.init();
    }

    init() {
        this.render();
        this.setupValidation();
    }

    render() {
        this.container.innerHTML = `
            <form id="myForm">
                <div class="form-field-wrapper">
                    <label for="email">Email</label>
                    <input type="text" id="email" name="email">
                </div>
                <div class="form-field-wrapper">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password">
                </div>
                <button type="submit" id="submitBtn">Submit</button>
            </form>
        `;
    }

    setupValidation() {
        const form = document.getElementById('myForm');
        const submitBtn = document.getElementById('submitBtn');

        this.validator = new FormValidator(form, {
            fields: {
                email: {
                    rules: ['required', 'email']
                },
                password: {
                    rules: ['required', 'minLength:8']
                }
            },
            onChange: (isValid) => {
                submitBtn.disabled = !isValid;
            }
        });

        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            if (!await this.validator.validateAll()) {
                Toast.error('Please fix form errors');
                return;
            }

            this.submitForm();
        });
    }

    async submitForm() {
        const formData = new FormData(document.getElementById('myForm'));
        const data = Object.fromEntries(formData);

        const response = await apiClient.post('/api/submit', data);

        if (!response.ok) {
            Toast.showApiError(response, () => this.submitForm());
            return;
        }

        Toast.success('Form submitted successfully');
    }

    destroy() {
        if (this.validator) {
            this.validator.destroy();
        }
    }
}
```

### Pattern 3: Error Handling with Retry

```javascript
class DataView {
    constructor() {
        this.retryCount = 0;
        this.maxRetries = 3;
    }

    async loadData() {
        const response = await apiClient.get('/api/data');

        if (!response.ok) {
            // Check if should retry
            if (this.retryCount < this.maxRetries &&
                Toast.isRetryableError(response.error)) {

                this.retryCount++;
                Toast.showErrorWithRetry(
                    `Failed to load data (attempt ${this.retryCount}/${this.maxRetries})`,
                    () => this.loadData(),
                    response.message
                );
            } else {
                // Max retries reached or non-retryable error
                Toast.error('Failed to load data. Please try again later.', 0);
            }
            return;
        }

        this.retryCount = 0;  // Reset on success
        this.renderData(response.data);
    }
}
```

---

## Best Practices

### 1. Always Use State Management for Stateful Views

```javascript
// ✅ Good
class MyView {
    constructor() {
        this.stateManager = new ViewStateManager('myView');
        this.state = this.stateManager.restoreState();
    }
}

// ❌ Bad
class MyView {
    constructor() {
        this.state = {};  // Lost on navigation
    }
}
```

### 2. Use Virtual Scrolling for Large Lists

```javascript
// ✅ Good (1000+ items)
this.virtualList = new VirtualList({
    container: container,
    itemHeight: 80,
    renderItem: (item) => renderItem(item)
});

// ❌ Bad (slow with large lists)
container.innerHTML = items.map(item => renderItem(item)).join('');
```

### 3. Validate Forms in Real-time

```javascript
// ✅ Good
const validator = new FormValidator(form, {
    fields: { email: { rules: ['required', 'email'] } },
    validateOnInput: true
});

// ❌ Bad
form.addEventListener('submit', (e) => {
    if (!validateForm()) {  // Too late!
        alert('Please fix errors');
    }
});
```

### 4. Use Toast for All User Feedback

```javascript
// ✅ Good
Toast.success('Changes saved');
Toast.showApiError(response, () => retry());

// ❌ Bad
alert('Changes saved');
console.error('Error:', error);
```

### 5. Clean Up on Destroy

```javascript
// ✅ Good
destroy() {
    if (this.virtualList) this.virtualList.destroy();
    if (this.validator) this.validator.destroy();
    if (this.stateManager) {
        this.stateManager.saveState(this.state);
    }
}

// ❌ Bad
destroy() {
    // Memory leaks!
}
```

---

## Performance Tips

1. **Debounce Expensive Operations**
   ```javascript
   let debounceTimer;
   input.addEventListener('input', (e) => {
       clearTimeout(debounceTimer);
       debounceTimer = setTimeout(() => {
           expensiveOperation(e.target.value);
       }, 300);
   });
   ```

2. **Use Virtual Scrolling for Lists > 100 Items**
   - Dramatically reduces DOM nodes
   - Maintains 60fps scrolling
   - Lower memory usage

3. **Save State Strategically**
   ```javascript
   // ✅ Good: Save on significant changes
   onFilterChange() {
       this.stateManager.updateState({ filters: this.filters });
   }

   // ❌ Bad: Save on every keystroke
   onKeyPress() {
       this.stateManager.saveState({ ... });  // Too frequent!
   }
   ```

4. **Batch Toast Notifications**
   ```javascript
   // ✅ Good
   Toast.error('3 items failed to save', 0, {
       details: 'Click to view details',
       action: { label: 'View', onClick: showDetails }
   });

   // ❌ Bad
   items.forEach(item => {
       Toast.error(`Failed: ${item.name}`);  // Toast spam!
   });
   ```

---

## Troubleshooting

### State Not Persisting

```javascript
// Check if state manager is properly initialized
console.log(ViewStateManager.getAllSavedViews());

// Check browser storage
console.log(sessionStorage.getItem('agentos_view_state_myView'));

// Verify state is being saved
stateManager.saveState({ test: 'value' });
console.log(stateManager.restoreState());
```

### Virtual List Not Rendering

```javascript
// Check container has height
console.log(container.clientHeight);  // Should be > 0

// Check items are set
console.log(virtualList.items.length);

// Check itemHeight matches actual items
console.log(virtualList.itemHeight);
```

### Form Validation Not Working

```javascript
// Check form has novalidate attribute
console.log(form.getAttribute('novalidate'));  // Should be 'novalidate'

// Check field names match
console.log(form.querySelector('[name="email"]'));  // Should exist

// Check validator is initialized
console.log(validator.fields);
```

### Toast Not Showing

```javascript
// Check toast manager is initialized
console.log(window.Toast);  // Should be defined

// Check container exists
console.log(document.querySelector('.toast-container'));

// Manually show toast
Toast.info('Test toast');
```

---

## Migration Checklist

When updating an existing view to use the new utilities:

- [ ] Add ViewStateManager for state persistence
- [ ] Replace large list rendering with VirtualList
- [ ] Update error handling to use Toast.showApiError()
- [ ] Add FormValidator to forms
- [ ] Update fetch calls to use apiClient
- [ ] Add destroy() method for cleanup
- [ ] Test state persistence across navigation
- [ ] Test with large datasets (1000+ items)
- [ ] Test form validation edge cases
- [ ] Test error handling and retry
- [ ] Update E2E tests

---

## Getting Help

- **Documentation:** `/docs/webui/UX_IMPROVEMENTS_QUICK_REFERENCE.md`
- **Full Report:** `/tmp/WEBUI_STABILITY_UX_REPORT.md`
- **Examples:** `/agentos/webui/static/js/views/HistoryViewEnhanced.js`
- **Tests:** `/tests/e2e/test_webui_ux_improvements.py`

---

**Last Updated:** 2026-01-31
**Version:** v0.3.2
