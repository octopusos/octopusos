# 🎨 Autocomplete Visual Guide

## Visual Design Reference

This document shows the visual design and interaction patterns of the BrainOS Query Console Autocomplete feature.

---

## 🎯 Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│  Brain Query Console                                        │
├─────────────────────────────────────────────────────────────┤
│  [Why] [Impact] [Trace] [Map]                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────────────────────────────────┐ [Search]    │
│  │ Enter file:path, doc:name, term:keyword  │             │
│  └───────────────────────────────────────────┘             │
│  ▼ Autocomplete Dropdown (when typing)                     │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ ✅ FILE  task/manager.py                             │ │
│  │   Core task management module                        │ │
│  ├───────────────────────────────────────────────────────┤ │
│  │ ✅ FILE  task/models.py                              │ │
│  │   Task data models and schemas                       │ │
│  ├───────────────────────────────────────────────────────┤ │
│  │ ⚠️ CAPABILITY  task_retry                            │ │
│  │   Moderate risk: retry logic with backoff            │ │
│  ├───────────────────────────────────────────────────────┤ │
│  │ 🚨 TERM  governance                                   │ │
│  │   High risk: governance boundary entity              │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎨 Color Palette

### Safety Levels

**✅ SAFE (Green)**
```
Background (hover): #f0fdf4
Hint text: #15803d
Icon: ✅
```

**⚠️ WARNING (Orange)**
```
Background (hover): #fffbeb
Hint text: #b45309
Icon: ⚠️
```

**🚨 DANGEROUS (Red)**
```
Background (hover): #fef2f2
Hint text: #dc2626
Icon: 🚨
```

### General Colors

```
Entity type badge: #6366f1 (indigo)
Entity name: #1f2937 (dark gray)
Dropdown border: #d1d5db (light gray)
Dropdown shadow: rgba(0, 0, 0, 0.15)
```

---

## 📐 Dimensions

```
Dropdown:
  - Max height: 400px
  - Border: 1px solid #d1d5db
  - Border radius: 0 0 6px 6px
  - Box shadow: 0 4px 12px rgba(0, 0, 0, 0.15)

Autocomplete Item:
  - Padding: 12px 16px
  - Border bottom: 1px solid #f3f4f6

Item Icon:
  - Font size: 16px
  - Line height: 1

Item Type Badge:
  - Padding: 2px 8px
  - Border radius: 4px
  - Font size: 11px
  - Font weight: 600

Item Name:
  - Font size: 14px
  - Font weight: 600
  - Font family: 'Courier New', monospace

Item Hint:
  - Font size: 12px
  - Font style: italic
  - Margin left: 24px
```

---

## 🎬 Interaction States

### State 1: Input Focus (No Suggestions)

```
┌───────────────────────────────────────┐
│ ta█                                   │  ← User typing
└───────────────────────────────────────┘
```

**Behavior**:
- Border color changes to #6366f1 (indigo)
- Box shadow: 0 0 0 3px rgba(99, 102, 241, 0.1)
- Waiting for 300ms debounce

---

### State 2: Dropdown Visible

```
┌───────────────────────────────────────┐
│ task█                                 │
└───────────────────────────────────────┘
┌───────────────────────────────────────┐
│ ✅ FILE  task/manager.py             │
│   Core task management module         │
├───────────────────────────────────────┤
│ ✅ FILE  task/models.py              │
│   Task data models                    │
└───────────────────────────────────────┘
```

**Behavior**:
- Dropdown appears below input
- Border connects seamlessly
- Scrollbar if >10 items

---

### State 3: Item Hover

```
┌───────────────────────────────────────┐
│ task                                  │
└───────────────────────────────────────┘
┌───────────────────────────────────────┐
│ ✅ FILE  task/manager.py             │
│   Core task management module         │
├═══════════════════════════════════════┤ ← Highlighted
║ ✅ FILE  task/models.py              ║ ← Green background
║   Task data models                    ║ ← (#f0fdf4)
╚═══════════════════════════════════════╝
└───────────────────────────────────────┘
```

**Behavior**:
- Background changes to safety-level color
- Cursor: pointer
- Smooth transition (0.15s ease)

---

### State 4: Keyboard Selection

```
┌───────────────────────────────────────┐
│ task                                  │
└───────────────────────────────────────┘
┌───────────────────────────────────────┐
│ ✅ FILE  task/manager.py             │
│   Core task management module         │
├═══════════════════════════════════════┤ ← Selected
║ ✅ FILE  task/models.py     ←       ║ ← Indicator
║   Task data models                    ║
╚═══════════════════════════════════════╝
│ ⚠️ CAPABILITY  task_retry            │
│   Moderate risk: retry logic          │
└───────────────────────────────────────┘
```

**Behavior**:
- Selected item highlighted
- Arrow keys navigate
- Auto-scrolls to keep item visible

---

### State 5: Dangerous Entity Warning

```
┌───────────────────────────────────────┐
│ governance                            │
└───────────────────────────────────────┘
┌───────────────────────────────────────┐
│ 🚨 TERM  governance                  │ ← Red background
│   High risk: governance boundary      │ ← Red text
└───────────────────────────────────────┘
```

**Behavior**:
- Red hint text (#dc2626)
- 🚨 emoji prominent
- Hover: light red background (#fef2f2)
- **Cognitive guardrail engaged!**

---

## 🎯 Typography

### Font Stack

```css
body {
    font-family: -apple-system, BlinkMacSystemFont,
                 'Segoe UI', Roboto, 'Helvetica Neue',
                 Arial, sans-serif;
}

.item-name {
    font-family: 'Courier New', monospace;
}
```

### Font Sizes

```
Item Name:       14px (Bold, Monospace)
Item Type Badge: 11px (Bold, Uppercase)
Item Hint:       12px (Italic)
Item Icon:       16px
```

### Font Weights

```
Item Name:       600 (Semi-bold)
Item Type Badge: 600 (Semi-bold)
Item Hint:       400 (Normal)
```

---

## 🎭 Animation & Transitions

### Transition Properties

```css
.autocomplete-item {
    transition: background 0.15s ease;
}

.autocomplete-item.selected {
    /* Smooth background change */
    background: #f9fafb;
}

.autocomplete-dropdown {
    /* No transition on show/hide for instant response */
}
```

### Scroll Behavior

```javascript
scrollIntoView({
    block: 'nearest',
    behavior: 'smooth'
})
```

**Effect**: Selected item smoothly scrolls into view

---

## 🖱️ Cursor States

```
Input field: text
Autocomplete item: pointer
Item (disabled): not-allowed (future)
Scrollbar thumb: pointer
```

---

## 📱 Responsive Design

### Desktop (≥1200px)

```
Dropdown width: 100% of input
Max height: 400px
Item padding: 12px 16px
Font sizes: As specified
```

### Tablet (768px - 1199px)

```
Dropdown width: 100% of input
Max height: 300px
Item padding: 10px 14px
Font sizes: Same
```

### Mobile (<768px)

```
Dropdown width: 100% of input
Max height: 250px
Item padding: 12px 16px (touch-friendly)
Font sizes: Same
Increased touch targets (48px min height)
```

---

## 🎨 Visual Hierarchy

### Priority Order

```
1. Safety Icon (🚨 ⚠️ ✅)  ← Most prominent
2. Entity Name             ← Bold, monospace
3. Entity Type Badge       ← Blue badge
4. Hint Text              ← Italic, smaller
```

### Visual Weight

```
Heavy:   Safety icon, Entity name
Medium:  Entity type badge
Light:   Hint text, borders
```

---

## 🖼️ Example Scenarios

### Scenario A: Safe File Search

```
Input: "task/"

┌─────────────────────────────────────────────────────┐
│ ✅ FILE  task/manager.py                           │
│   Core task management and lifecycle                │
├─────────────────────────────────────────────────────┤
│ ✅ FILE  task/models.py                            │
│   Data models for task representation               │
├─────────────────────────────────────────────────────┤
│ ✅ FILE  task/service.py                           │
│   Task service layer and business logic             │
└─────────────────────────────────────────────────────┘

Cognitive Effect: User feels SAFE, proceeds confidently
```

---

### Scenario B: Warning on Capability

```
Input: "exec"

┌─────────────────────────────────────────────────────┐
│ ⚠️ CAPABILITY  executor                            │
│   Moderate risk: executes external commands         │
├─────────────────────────────────────────────────────┤
│ ⚠️ CAPABILITY  execution_guard                     │
│   Moderate risk: guards execution boundaries        │
└─────────────────────────────────────────────────────┘

Cognitive Effect: User proceeds with CAUTION
```

---

### Scenario C: Danger Warning

```
Input: "gov"

┌─────────────────────────────────────────────────────┐
│ 🚨 TERM  governance                                 │
│   High risk: governance boundary entity             │
├─────────────────────────────────────────────────────┤
│ 🚨 FILE  governance/dashboard.py                    │
│   High risk: critical governance component          │
└─────────────────────────────────────────────────────┘

Cognitive Effect: User STOPS, reconsiders, or proceeds
                  with full awareness of risks
```

---

## 🎮 Keyboard Shortcuts

```
Type 2+ chars     → Trigger autocomplete (300ms delay)
ArrowDown         → Navigate down
ArrowUp           → Navigate up
Enter             → Select highlighted item
ESC               → Close dropdown
Tab               → Focus next element, close dropdown
Click outside     → Close dropdown (200ms delay)
```

---

## 🎯 Cognitive Guardrail Effectiveness

### Visual Indicators Summary

| Safety Level | Icon | Background | Text Color | Cognitive Effect |
|-------------|------|------------|-----------|-----------------|
| SAFE | ✅ | #f0fdf4 | #15803d | Confidence ↑ |
| WARNING | ⚠️ | #fffbeb | #b45309 | Caution ↑ |
| DANGEROUS | 🚨 | #fef2f2 | #dc2626 | **STOP** Signal |

### User Flow

```
1. User types → 2. See suggestions → 3. Notice safety indicator
                                            ↓
4a. ✅ → Feel safe → Select confidently
4b. ⚠️ → Feel cautious → Proceed carefully
4c. 🚨 → Feel warned → Reconsider OR proceed with awareness
```

---

## 🔍 Accessibility

### Screen Reader Support

```html
<!-- Future enhancement -->
<div role="listbox" aria-label="Entity suggestions">
    <div role="option" aria-selected="false">
        <span class="sr-only">Safe entity</span>
        FILE task/manager.py
    </div>
</div>
```

### Keyboard Only Navigation

✅ All functionality accessible via keyboard
✅ Visual focus indicators
✅ Logical tab order
✅ No mouse-only features

---

## 🎉 Success Indicators

### Visual Feedback

- ✅ Dropdown appears smoothly
- ✅ Items highlight on hover/selection
- ✅ Scrolling is smooth
- ✅ Safety colors are distinct
- ✅ Icons are clear and prominent

### Interaction Feedback

- ✅ Input feels responsive (300ms acceptable)
- ✅ Selection is instant
- ✅ Navigation is intuitive
- ✅ Closing is smooth

---

**Last Updated**: 2026-01-30
**Status**: Visual Design Documented
**Next**: User Testing & Feedback Collection

---

_"Great design is invisible—it just works."_
