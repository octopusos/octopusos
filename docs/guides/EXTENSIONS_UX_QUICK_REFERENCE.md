# Extensions UI Quick Reference Guide

## 🎨 New Features Overview

### L-16: Drag and Drop Upload
```
┌─────────────────────────────────────┐
│   📤                                │
│   Drag and drop your extension here│
│                                     │
│   or                                │
│                                     │
│   [ Browse Files ]                  │
│                                     │
│   Supports .zip files only          │
└─────────────────────────────────────┘
```

**Usage**:
- Click "Upload Extension"
- Drag .zip file onto the area
- Watch for blue highlight
- Drop to select

---

### L-17: Screenshot Carousel
```
┌────────────────────────────────────────────┐
│  Screenshots                               │
│  ┌─────────────────────────────────────┐  │
│  │ ◀  [Screenshot 1] [Screenshot 2]  ▶ │  │
│  └─────────────────────────────────────┘  │
└────────────────────────────────────────────┘
```

**Usage**:
- Click extension name to view details
- Scroll through screenshots
- Click to view fullscreen
- Press Escape to close

---

### L-18: Rating System
```
Extension Card:
┌────────────────────────────┐
│ Extension Name             │
│ ★★★★☆ 4/5                 │
│ Description...             │
└────────────────────────────┘
```

**Usage**:
- Click stars to rate (1-5)
- Rating saves automatically
- Persists across sessions

**Storage**: localStorage
```json
{
  "extension_ratings": {
    "tools.test": 4,
    "tools.demo": 5
  }
}
```

---

### L-19: Bulk Operations
```
Normal Mode:
┌──────────────────────────────────────┐
│ [ Bulk Select ]                      │
└──────────────────────────────────────┘

Bulk Mode:
┌──────────────────────────────────────┐
│ [ Exit Bulk Mode ]                   │
├──────────────────────────────────────┤
│ 2 selected  [Select All] [Clear]     │
│ [Enable] [Disable] [Uninstall]       │
└──────────────────────────────────────┘

Extension Cards:
┌────────────────────────────┐
│ ☑ Extension Name           │
│ Description...             │
└────────────────────────────┘
```

**Usage**:
1. Click "Bulk Select"
2. Check extensions
3. Use toolbar buttons
4. Confirm actions

---

### L-20: Keyboard Shortcuts
```
⌨️  KEYBOARD SHORTCUTS

Ctrl+K  (⌘+K)   │ Focus search
────────────────┼──────────────────────
Escape          │ • Close modal
                │ • Clear search
────────────────┼──────────────────────
Ctrl+R  (⌘+R)   │ Refresh extensions
```

**Search Box**:
```
┌──────────────────────────────────────┐
│ 🔍 Search extensions... (Ctrl+K)     │
└──────────────────────────────────────┘
```

---

## 📋 Feature Comparison

| Feature | Before | After |
|---------|--------|-------|
| **Upload** | File picker only | Drag & drop + file picker |
| **Preview** | No screenshots | Screenshot carousel |
| **Rating** | None | 5-star system |
| **Bulk ops** | One at a time | Select multiple |
| **Search** | None | Real-time filter + Ctrl+K |

---

## 🎯 User Workflows

### Quick Install Workflow
```
1. Ctrl+K to open search
2. Type extension name
3. Click extension card
4. View screenshots & rating
5. Click Install
```

### Bulk Management Workflow
```
1. Click "Bulk Select"
2. Select multiple extensions
3. Choose action (Enable/Disable/Uninstall)
4. Confirm
5. Exit bulk mode
```

### Discovery Workflow
```
1. Browse extensions
2. Check ratings (★★★★☆)
3. Click to view details
4. See screenshots
5. Read description
6. Rate after using
```

---

## 🚀 Performance Tips

1. **Search**: Type-ahead is instant, no need to press Enter
2. **Bulk ops**: Select fewer at once for faster processing
3. **Screenshots**: Click to load fullscreen only when needed
4. **Ratings**: Save automatically, no manual save required

---

## ♿ Accessibility

- **Keyboard**: All features accessible via keyboard
- **Screen readers**: Proper ARIA labels
- **Focus**: Clear focus indicators
- **Contrast**: WCAG AA compliant

---

## 🐛 Troubleshooting

### Drag & Drop Not Working
- Check file is .zip format
- Try using "Browse Files" button
- Ensure JavaScript is enabled

### Ratings Not Saving
- Check localStorage is enabled
- Check browser storage quota
- Try clearing cache

### Keyboard Shortcuts Not Working
- Ensure no input field is focused
- Check browser doesn't override shortcuts
- Try Ctrl vs ⌘ (Mac)

### Search Not Filtering
- Check spelling
- Try clearing and retyping
- Refresh page (Ctrl+R)

---

## 📞 Support

For issues or questions:
- GitHub Issues: [agentos/issues]
- Documentation: See full report in EXTENSIONS_UX_ENHANCEMENTS_REPORT.md
- E2E Tests: tests/e2e/test_extensions_ux_enhancements.py

---

**Version**: v0.3.2
**Last Updated**: 2026-01-31
