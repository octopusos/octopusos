# Task #15: Extension Wizard CSS - Quick Reference

## Quick Access

| Resource | Location |
|----------|----------|
| **CSS File** | `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/static/css/extension-wizard.css` |
| **JS Logic** | `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/static/js/views/ExtensionsView.js` |
| **HTML Template** | `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/templates/index.html` |
| **Full Report** | `TASK_15_EXTENSION_WIZARD_STYLE_FIX_REPORT.md` |
| **Visual Comparison** | `TASK_15_VISUAL_COMPARISON.md` |

---

## CSS Variables Cheat Sheet

### Spacing
```css
--wizard-space-xs: 4px;      /* Tiny gaps */
--wizard-space-sm: 8px;      /* Small spacing */
--wizard-space-md: 16px;     /* Medium spacing (default) */
--wizard-space-lg: 24px;     /* Large spacing */
--wizard-space-xl: 32px;     /* Extra large spacing */
```

**Usage Example**:
```css
.my-element {
    margin: var(--wizard-space-md);  /* 16px */
    padding: var(--wizard-space-sm); /* 8px */
}
```

### Component Heights
```css
--wizard-input-height: 40px;           /* All inputs & selects */
--wizard-btn-height: 40px;             /* All buttons */
--wizard-textarea-min-height: 80px;    /* Textareas minimum */
```

### Font Sizes
```css
--wizard-font-xs: 12px;     /* Hints, meta info */
--wizard-font-sm: 14px;     /* Body text, inputs */
--wizard-font-md: 16px;     /* Labels */
--wizard-font-lg: 20px;     /* Section headings */
```

### Colors

#### Primary
```css
--wizard-primary: #4F46E5;              /* Main brand color */
--wizard-primary-hover: #4338ca;        /* Darker on hover */
--wizard-primary-light: rgba(79, 70, 229, 0.1);  /* Light tint */
```

#### Semantic
```css
--wizard-danger: #ef4444;               /* Error, delete */
--wizard-danger-light: rgba(239, 68, 68, 0.1);
--wizard-success: #10b981;              /* Success states */
--wizard-info: #3b82f6;                 /* Info boxes */
--wizard-info-bg: #eff6ff;              /* Info background */
```

#### Text
```css
--wizard-text-primary: #111827;         /* Headings */
--wizard-text-secondary: #374151;       /* Labels */
--wizard-text-muted: #6b7280;           /* Hints, meta */
```

#### Borders
```css
--wizard-border-light: #e5e7eb;         /* Light borders */
--wizard-border-medium: #d1d5db;        /* Default borders */
--wizard-border-dark: #9ca3af;          /* Hover borders */
```

#### Backgrounds
```css
--wizard-bg-white: #ffffff;             /* White background */
--wizard-bg-light: #f9fafb;             /* Light gray background */
```

### Visual Effects
```css
--wizard-radius-sm: 4px;                /* Small radius */
--wizard-radius-md: 6px;                /* Standard radius */
--wizard-radius-lg: 8px;                /* Large radius */

--wizard-shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.05);
--wizard-shadow-md: 0 4px 12px rgba(0, 0, 0, 0.1);
--wizard-shadow-lg: 0 4px 12px rgba(102, 126, 234, 0.4);
--wizard-shadow-focus: 0 0 0 3px rgba(79, 70, 229, 0.1);

--wizard-transition: all 0.2s ease;     /* Standard transition */
```

---

## Common Patterns

### Creating a New Button
```css
.btn-my-action {
    height: var(--wizard-btn-height);
    padding: 0 var(--wizard-space-lg);
    border-radius: var(--wizard-radius-md);
    font-size: var(--wizard-font-sm);
    background: var(--wizard-primary);
    color: white;
    border: none;
    cursor: pointer;
    transition: var(--wizard-transition);
}

.btn-my-action:hover {
    background: var(--wizard-primary-hover);
}
```

### Creating a New Input
```css
.my-input {
    width: 100%;
    height: var(--wizard-input-height);
    padding: 0 var(--wizard-space-xs);
    border: 1px solid var(--wizard-border-medium);
    border-radius: var(--wizard-radius-md);
    font-size: var(--wizard-font-sm);
    transition: var(--wizard-transition);
}

.my-input:focus {
    outline: none;
    border-color: var(--wizard-primary);
    box-shadow: var(--wizard-shadow-focus);
}
```

### Creating a New Card/Panel
```css
.my-card {
    background: var(--wizard-bg-light);
    border: 1px solid var(--wizard-border-light);
    border-radius: var(--wizard-radius-md);
    padding: var(--wizard-space-md);
    margin-bottom: var(--wizard-space-md);
}

.my-card:hover {
    border-color: var(--wizard-border-medium);
    box-shadow: var(--wizard-shadow-sm);
}
```

### Creating a Form Group
```css
.my-form-group {
    margin-bottom: var(--wizard-space-md);
}

.my-form-group label {
    display: block;
    font-size: var(--wizard-font-sm);
    font-weight: 600;
    color: var(--wizard-text-secondary);
    margin-bottom: var(--wizard-space-sm);
}

.my-form-group .hint {
    font-size: var(--wizard-font-xs);
    color: var(--wizard-text-muted);
    margin-top: var(--wizard-space-sm);
}
```

---

## Spacing Guidelines

### Hierarchy
```
4px  → Tiny gaps (icon spacing, checkbox margins)
8px  → Small spacing (label-to-input, hints)
16px → Default spacing (between form groups, card padding)
24px → Large spacing (between sections, button padding)
32px → Extra large (wizard step padding)
```

### Common Uses
```css
/* Between form fields */
.form-group { margin-bottom: var(--wizard-space-md); }  /* 16px */

/* Label to input gap */
label { margin-bottom: var(--wizard-space-sm); }  /* 8px */

/* Hint text top margin */
.hint { margin-top: var(--wizard-space-sm); }  /* 8px */

/* Section spacing */
.section { margin-bottom: var(--wizard-space-lg); }  /* 24px */

/* Card/panel padding */
.card { padding: var(--wizard-space-md); }  /* 16px */
```

---

## Color Usage Guidelines

### When to Use Each Color

#### Primary (`--wizard-primary`)
- Call-to-action buttons
- Links
- Active states
- Focus borders

#### Danger (`--wizard-danger`)
- Delete buttons
- Error messages
- Destructive actions

#### Success (`--wizard-success`)
- Success messages
- Confirmation states
- Completed items

#### Info (`--wizard-info`)
- Information boxes
- Help text backgrounds
- Neutral notifications

#### Text Colors
```css
/* Headings */
color: var(--wizard-text-primary);

/* Labels, body text */
color: var(--wizard-text-secondary);

/* Hints, meta info */
color: var(--wizard-text-muted);
```

---

## Component Classes

### Buttons
```css
.btn-wizard          /* Primary wizard button */
.btn-delete-capability  /* Delete capability button */
#btnAddCapability    /* Add capability button */
```

### Containers
```css
.wizard-step         /* Individual step container */
.wizard-progress     /* Progress bar container */
.form-group          /* Form field wrapper */
.capability-item     /* Capability card */
.review-section      /* Review step section */
.info-box            /* Information box */
```

### Inputs
```css
input[type="text"]
input[type="email"]
input[type="url"]
input[type="password"]
select
textarea
input.capability-name
input.capability-description
select.capability-type
```

---

## Responsive Breakpoints

### Mobile (< 768px)
```css
@media (max-width: 768px) {
    /* Tighter spacing */
    .wizard-progress {
        padding: var(--wizard-space-xs) var(--wizard-space-md);
    }

    .wizard-step {
        padding: var(--wizard-space-sm) 0;
    }

    .form-group {
        margin-bottom: var(--wizard-space-sm);
    }
}
```

---

## Customization Examples

### Example 1: Increase All Spacing by 25%
```css
:root {
    --wizard-space-xs: 5px;   /* Was 4px */
    --wizard-space-sm: 10px;  /* Was 8px */
    --wizard-space-md: 20px;  /* Was 16px */
    --wizard-space-lg: 30px;  /* Was 24px */
    --wizard-space-xl: 40px;  /* Was 32px */
}
```

### Example 2: Change Primary Color to Blue
```css
:root {
    --wizard-primary: #2563eb;
    --wizard-primary-hover: #1d4ed8;
    --wizard-primary-light: rgba(37, 99, 235, 0.1);
}
```

### Example 3: Larger Input Heights
```css
:root {
    --wizard-input-height: 48px;  /* Was 40px */
    --wizard-btn-height: 48px;    /* Was 40px */
}
```

### Example 4: Tighter Border Radius
```css
:root {
    --wizard-radius-sm: 2px;   /* Was 4px */
    --wizard-radius-md: 4px;   /* Was 6px */
    --wizard-radius-lg: 6px;   /* Was 8px */
}
```

---

## Troubleshooting

### Problem: Input Heights Not Consistent
**Solution**: Ensure all inputs use the unified class or have explicit height:
```css
.my-custom-input {
    height: var(--wizard-input-height);
    box-sizing: border-box;  /* Important! */
}
```

### Problem: Focus States Not Working
**Solution**: Add to the unified focus selector:
```css
.wizard-step .form-group input:focus,
/* ... existing selectors ... */
.my-custom-input:focus {
    outline: none;
    border-color: var(--wizard-primary);
    box-shadow: var(--wizard-shadow-focus);
}
```

### Problem: Colors Not Updating
**Solution**: Check if hard-coded color is being used instead of variable:
```css
/* Bad */
color: #6b7280;

/* Good */
color: var(--wizard-text-muted);
```

### Problem: Spacing Looks Off
**Solution**: Use the spacing scale instead of custom values:
```css
/* Bad */
margin-bottom: 14px;

/* Good */
margin-bottom: var(--wizard-space-md);  /* 16px */
```

---

## Testing Checklist

### Visual Testing
- [ ] All buttons are 40px height
- [ ] All inputs are 40px height
- [ ] Textareas are minimum 80px height
- [ ] Spacing is consistent between form groups
- [ ] Focus states appear on all inputs
- [ ] Hover states work on interactive elements
- [ ] Colors match design system

### Functional Testing
- [ ] Tab navigation works properly
- [ ] Focus indicators visible
- [ ] All wizard steps navigate correctly
- [ ] Form submission works
- [ ] Responsive design works on mobile

### Browser Testing
- [ ] Chrome/Edge
- [ ] Firefox
- [ ] Safari
- [ ] Mobile Safari
- [ ] Chrome Mobile

---

## Performance Tips

### Do's ✅
- Use CSS variables for consistent values
- Limit transitions to necessary properties
- Use `box-sizing: border-box` for predictable sizing
- Leverage browser caching

### Don'ts ❌
- Don't use inline styles (defeats the purpose)
- Don't hard-code colors or spacing
- Don't animate expensive properties (width, height)
- Don't create duplicate variable names

---

## Maintenance

### When Adding New Components
1. Use existing CSS variables
2. Follow the spacing hierarchy
3. Match the color palette
4. Add consistent hover/focus states
5. Test on mobile
6. Document any new patterns

### When Modifying Variables
1. Search for all usages of the variable
2. Test all wizard steps
3. Check responsive behavior
4. Verify accessibility
5. Update this documentation

### Monthly Review
- [ ] Check for unused CSS rules
- [ ] Verify variable usage is consistent
- [ ] Review responsive breakpoints
- [ ] Test on latest browsers
- [ ] Update documentation

---

## File Structure
```
extension-wizard.css
├── :root (CSS Variables)
│   ├── Spacing
│   ├── Component Heights
│   ├── Font Sizes
│   ├── Colors
│   ├── Border Radius
│   ├── Shadows
│   └── Transitions
├── Wizard Button
├── Wizard Modal
├── Wizard Progress
├── Wizard Steps
├── Form Groups
│   ├── Labels
│   ├── Inputs
│   ├── Textareas
│   ├── Focus States
│   └── Hints
├── Capability Items
├── Permission Checkboxes
├── Review Section
├── Info Box
├── Animations
└── Responsive (@media queries)
```

---

## Common Tasks

### Change Spacing System
Edit `:root` variables at the top of `extension-wizard.css`

### Change Color Theme
Edit color variables in `:root` section

### Add New Input Type
Add to the unified input selector and focus state selector

### Adjust Mobile Layout
Edit the `@media (max-width: 768px)` section

### Add New Animation
Define `@keyframes` at bottom of file, use with `--wizard-transition`

---

## Resources

### Documentation
- [Full Task Report](TASK_15_EXTENSION_WIZARD_STYLE_FIX_REPORT.md)
- [Visual Comparison](TASK_15_VISUAL_COMPARISON.md)
- [CSS Variables on MDN](https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties)

### Related Files
- JavaScript: `/agentos/webui/static/js/views/ExtensionsView.js`
- HTML Template: `/agentos/webui/templates/index.html`
- API Backend: `/agentos/webui/api/extensions.py`

### Tools
- Browser DevTools for CSS debugging
- Lighthouse for performance testing
- axe for accessibility testing

---

## Quick Commands

### View CSS File
```bash
cat /Users/pangge/PycharmProjects/AgentOS/agentos/webui/static/css/extension-wizard.css
```

### Edit CSS File
```bash
vim /Users/pangge/PycharmProjects/AgentOS/agentos/webui/static/css/extension-wizard.css
```

### Start WebUI
```bash
cd /Users/pangge/PycharmProjects/AgentOS
python -m agentos.webui.app
```

### Access Extension Wizard
```
http://localhost:5000
→ Extensions Tab
→ "Create Extension Template" button
```

---

## Contact

For questions or issues related to the Extension Wizard CSS:
- Check the full documentation in `TASK_15_EXTENSION_WIZARD_STYLE_FIX_REPORT.md`
- Review visual comparisons in `TASK_15_VISUAL_COMPARISON.md`
- Refer to this quick reference for common patterns

---

**Last Updated**: 2026-01-30
**Version**: 1.0
**Status**: ✅ Production Ready
