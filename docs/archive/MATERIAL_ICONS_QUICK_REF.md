# Material Design Icons - Quick Reference

## Executive Summary

**Date**: 2026-01-30
**Project**: AgentOS WebUI
**Scope**: Complete scan of Material Design icons usage

### Key Metrics
- **Total Files**: 69 files
- **Total Occurrences**: 746
- **Unique Icons**: 125 different icon names
- **JavaScript Files**: 49 files (640 occurrences, 85.7%)
- **CSS Files**: 19 files (104 occurrences, 13.9%)
- **HTML Files**: 2 files (2 occurrences, 0.4%)

---

## Top 30 Most Used Icons (60%+ Coverage)

| Rank | Icon Name | Count | Category | Suggested Replacement |
|------|-----------|-------|----------|----------------------|
| 1 | `warning` | 54 | Status | ⚠️ (U+26A0) |
| 2 | `refresh` | 40 | Action | 🔄 (U+1F504) |
| 3 | `content_copy` | 30 | Action | 📋 (U+1F4CB) |
| 4 | `check` | 25 | Status | ✓ (U+2713) |
| 5 | `check_circle` | 22 | Status | ✅ (U+2705) |
| 6 | `cancel` | 21 | Status | ❌ (U+274C) |
| 7 | `info` | 19 | Status | ℹ️ (U+2139) |
| 8 | `search` | 18 | Action | 🔍 (U+1F50D) |
| 9 | `save` | 14 | Action | 💾 (U+1F4BE) |
| 10 | `add` | 14 | Action | ➕ (U+2795) |
| 11 | `download` | 12 | Action | ⬇️ (U+2B07) |
| 12 | `edit` | 12 | Action | ✏️ (U+270F) |
| 13 | `delete` | 12 | Action | 🗑️ (U+1F5D1) |
| 14 | `error` | 12 | Status | ⛔ (U+26D4) |
| 15 | `folder_open` | 11 | Files | 📂 (U+1F4C2) |
| 16 | `play_arrow` | 10 | Navigation | ▶️ (U+25B6) |
| 17 | `description` | 9 | Files | 📄 (U+1F4C4) |
| 18 | `close` | 9 | Action | ✖️ (U+2716) |
| 19 | `visibility` | 9 | Action | 👁️ (U+1F441) |
| 20 | `schedule` | 9 | Time | ⏰ (U+23F0) |
| 21 | `lock` | 7 | Security | 🔒 (U+1F512) |
| 22 | `done` | 7 | Status | ✔️ (U+2714) |
| 23 | `arrow_back` | 6 | Navigation | ⬅️ (U+2B05) |
| 24 | `hourglass_empty` | 6 | Time | ⏳ (U+23F3) |
| 25 | `timeline` | 6 | Data | 📊 (U+1F4CA) |
| 26 | `send` | 6 | Action | 📤 (U+1F4E4) |
| 27 | `arrow_forward` | 5 | Navigation | ➡️ (U+27A1) |
| 28 | `folder` | 5 | Files | 📁 (U+1F4C1) |
| 29 | `lightbulb` | 5 | Misc | 💡 (U+1F4A1) |
| 30 | `task` | 5 | Action | ☑️ (U+2611) |

**Coverage**: Top 30 icons = 462 occurrences (61.9% of total)

---

## High-Impact Files (Target for Phase 1)

### JavaScript Views (Top 10)
1. `static/js/views/TasksView.js` - 34+ occurrences
2. `static/js/views/ProvidersView.js` - 28+ occurrences
3. `static/js/main.js` - 17+ occurrences
4. `static/js/views/LeadScanHistoryView.js` - 15+ occurrences
5. `static/js/views/EventsView.js` - 13+ occurrences
6. `static/js/views/KnowledgeHealthView.js` - 10+ occurrences
7. `static/js/views/LogsView.js` - 9+ occurrences
8. `static/js/views/ProjectsView.js` - 8+ occurrences
9. `static/js/views/ContextView.js` - 7+ occurrences
10. `static/js/components/AuthReadOnlyCard.js` - 5+ occurrences

**Total**: ~150 occurrences (20% of total in just 10 files)

---

## Dynamic Generation Patterns

### Pattern Distribution
- **String Literals**: 214 occurrences (94.3%)
  ```javascript
  '<span class="material-icons md-18">warning</span>'
  ```

- **Template Literals**: 7 occurrences (3.1%)
  ```javascript
  `<span class="material-icons">${icon}</span>`
  ```

- **classList.add**: 4 occurrences (1.8%)
  ```javascript
  element.classList.add('material-icons');
  ```

- **innerHTML**: 2 occurrences (0.9%)
  ```javascript
  element.innerHTML = `<span class="material-icons">check</span>`;
  ```

### Critical Dynamic Generation Files
1. `static/js/views/TasksView.js` - 34 dynamic generations
2. `static/js/views/ProvidersView.js` - 28 dynamic generations
3. `static/js/main.js` - 17 dynamic generations

---

## CSS Dependencies

### Size Modifier Classes
- `.material-icons.md-14` - 14px
- `.material-icons.md-16` - 16px
- `.material-icons.md-18` - 18px (most common)
- `.material-icons.md-20` - 20px
- `.material-icons.md-24` - 24px
- `.material-icons.md-36` - 36px

### Affected CSS Files (19 files)
- `static/css/components.css` - Base styles
- `static/css/multi-repo.css` - Project cards
- `static/css/brain.css` - Dashboard
- `static/css/budget-indicator.css` - Budget UI
- ... and 15 more files

---

## Replacement Strategy

### Phase 1: High-Impact Icons (Target 40% coverage)
**Focus**: Top 10 icons
- `warning`, `refresh`, `content_copy`, `check`, `check_circle`
- `cancel`, `info`, `search`, `save`, `add`

**Files**: Start with top 5 JS views
- TasksView.js, ProvidersView.js, main.js, LeadScanHistoryView.js, EventsView.js

**Expected Impact**: ~255 occurrences replaced

### Phase 2: Medium-Frequency Icons (Target 70% coverage)
**Focus**: Icons 11-30 (next 207 occurrences)
- Download, edit, delete, error, folder_open, etc.

**Files**: Remaining JS views and components

### Phase 3: Long-Tail Icons (Target 100% coverage)
**Focus**: Remaining 95 icons (284 occurrences)
- One-off and specialized icons
- Edge cases and rare usage

**Files**: CSS styling, HTML templates, cleanup

---

## Testing Checklist

### Visual Regression
- [ ] Icon size consistency across views
- [ ] Alignment with text (vertical-align)
- [ ] Color inheritance (text color)
- [ ] Spacing and padding preserved

### Cross-Browser
- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari (macOS/iOS)
- [ ] Mobile browsers

### Accessibility
- [ ] Screen reader announcements
- [ ] High contrast mode
- [ ] Keyboard navigation
- [ ] ARIA labels preserved

### Functional
- [ ] Click handlers still work
- [ ] Hover states preserved
- [ ] Animation/transitions
- [ ] Dynamic generation works

---

## Technical Notes

### Current Implementation
- Material Icons loaded from: `/static/vendor/material-icons/material-icons.css`
- Font-based icons using ligatures
- Inline styles often used for sizing
- CSS classes for common sizes (md-14 through md-36)

### Replacement Considerations
1. **Font Size**: Emojis default to text size, may need explicit sizing
2. **Color**: Emojis have fixed colors, can't inherit text color
3. **Spacing**: Emoji spacing differs from icon fonts
4. **Fallback**: Not all emojis render consistently across platforms
5. **Accessibility**: May need ARIA labels added

### Alternative Approaches
1. **Unicode Characters**: ✓ ✗ ℹ ⚠ (monochrome, flexible)
2. **Emoji**: 🔍 ✅ ⚠️ 📁 (colorful, platform-dependent)
3. **SVG Icons**: Custom inline SVGs (most flexible, larger size)
4. **Icon Font Replacement**: Different icon font library

---

## Complete Icon List (All 125 Icons)

### A-C
`ac_unit`, `account_balance_wallet`, `account_tree`, `add`, `add_circle`, `add_comment`, `alt_route`, `analytics`, `apps`, `archive`, `arrow_back`, `arrow_downward`, `arrow_drop_down`, `arrow_forward`, `arrow_upward`, `assessment`, `attach_file`, `attachment`, `auto_fix_high`, `bar_chart`, `block`, `bolt`, `bug_report`, `build`, `cancel`, `chat`, `check`, `check_circle`, `chevron_left`, `chevron_right`, `circle`, `cleaning_services`, `close`, `cloud`, `code`, `commit`, `compare`, `compare_arrows`, `content_copy`, `content_cut`

### D-H
`delete`, `delete_sweep`, `description`, `dns`, `done`, `download`, `edit`, `edit_note`, `email`, `error`, `error_outline`, `event_busy`, `expand_more`, `favorite`, `fiber_manual_record`, `fiber_new`, `folder`, `folder_off`, `folder_open`, `grid_view`, `health_and_safety`, `help`, `help_outline`, `history`, `hourglass_empty`

### I-P
`inbox`, `info`, `input`, `lightbulb`, `link`, `link_off`, `list`, `list_alt`, `local_fire_department`, `lock`, `map`, `menu_book`, `merge`, `more_vert`, `new_releases`, `open_in_new`, `pause_circle`, `person`, `pets`, `play_arrow`, `playlist_add`, `power`, `preview`, `priority_high`, `psychology`, `push_pin`

### Q-Z
`question_answer`, `quiz`, `radio_button_unchecked`, `refresh`, `remove_circle`, `restart_alt`, `save`, `schedule`, `search`, `send`, `settings`, `shield`, `smart_toy`, `source`, `star`, `stop`, `stop_circle`, `storage`, `sync`, `task`, `task_alt`, `timeline`, `track_changes`, `tune`, `update`, `upgrade`, `upload`, `upload_file`, `verified`, `verified_user`, `view_list`, `visibility`, `visibility_off`, `warning`

---

## References

- Full detailed report: `MATERIAL_ICONS_INVENTORY.md`
- Material Icons documentation: https://fonts.google.com/icons
- Unicode emoji charts: https://unicode.org/emoji/charts/full-emoji-list.html
- WebUI directory: `/Users/pangge/PycharmProjects/AgentOS/agentos/webui`

---

**Generated**: 2026-01-30
**Scan Coverage**: 100% of webui directory
**Next Task**: Design icon mapping table (Task #2)
