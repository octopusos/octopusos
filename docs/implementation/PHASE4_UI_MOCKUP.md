# Phase 4: RAG Health UI Mockup

## Visual Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Knowledge Health                                           [Refresh]    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐│
│  │ Index Lag    │  │ Fail Rate    │  │ Empty Hit    │  │ File         ││
│  │              │  │ (7d)         │  │ Rate         │  │ Coverage     ││
│  │              │  │              │  │              │  │              ││
│  │   2.5h       │  │   1.2%       │  │   5.3%       │  │   94.2%      ││
│  │              │  │              │  │              │  │              ││
│  │ Needs refresh│  │ Good         │  │ Good         │  │ Excellent    ││
│  │   (yellow)   │  │   (green)    │  │   (green)    │  │   (green)    ││
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘│
│                                                                           │
│  ┌──────────────┐  ┌──────────────┐                                     │
│  │ Total Chunks │  │ Total Files  │                                     │
│  │              │  │              │                                     │
│  │   1,250      │  │     85       │                                     │
│  │              │  │              │                                     │
│  │   Indexed    │  │   Tracked    │                                     │
│  │   (blue)     │  │   (blue)     │                                     │
│  └──────────────┘  └──────────────┘                                     │
│                                                                           │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│                                                                           │
│  Health Checks                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ ✓  FTS5 Available                                          [OK]     ││
│  │    Full-text search enabled                                         ││
│  ├─────────────────────────────────────────────────────────────────────┤│
│  │ ✓  Schema Version                                          [OK]     ││
│  │    Schema v1.0                                                      ││
│  ├─────────────────────────────────────────────────────────────────────┤│
│  │ ⚠  Index Staleness                                         [WARN]   ││
│  │    15 files modified since last index                               ││
│  ├─────────────────────────────────────────────────────────────────────┤│
│  │ ✓  Orphan Chunks                                           [OK]     ││
│  │    No orphan chunks found                                           ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                           │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│                                                                           │
│  Bad Smells                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ ⚠  Duplicate Content                              8 occurrences     ││
│  │                                                         [WARN]       ││
│  │    Details:                                                         ││
│  │    • docs/api.md                                                    ││
│  │    • docs/reference.md                                              ││
│  │    • src/utils/helpers.py                                           ││
│  │    • lib/common/utils.py                                            ││
│  │    • tests/fixtures/sample.json                                     ││
│  │                                                                     ││
│  │    💡 Consider consolidating duplicate content                      ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ ℹ  Oversized Files                                3 occurrences     ││
│  │                                                         [INFO]       ││
│  │    Details:                                                         ││
│  │    • docs/large_guide.md (15000 lines)                              ││
│  │    • src/core/processor.py (12500 lines)                            ││
│  │    • tests/integration/test_suite.py (11000 lines)                  ││
│  │                                                                     ││
│  │    💡 Split large files for better chunking                         ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

## Color Scheme

### Status Colors
- **Green (#d4edda / #155724)**: OK status - System healthy
- **Yellow (#fff3cd / #856404)**: WARN status - Attention needed
- **Red (#f8d7da / #721c24)**: ERROR status - Critical issue
- **Blue (#d1ecf1 / #0c5460)**: INFO status - Informational

### Component Colors
- **Metric Cards**: White background, gray border, hover shadow
- **Health Check Items**: White background, status-colored icon circle
- **Bad Smell Cards**: White background, colored left border matching severity

## Interactive Elements

### Hover States
- **Metric Cards**: Lift slightly with shadow increase
- **Health Check Items**: No interaction (read-only)
- **Bad Smell Cards**: No interaction (read-only)

### Refresh Button
- Icon: Circular refresh arrow
- Hover: Gray background highlight
- Click: Reloads health data from API

## Responsive Behavior

### Desktop (>1200px)
- Metrics: 3 columns × 2 rows grid
- Full-width health checks and bad smells

### Tablet (768px - 1200px)
- Metrics: 2 columns × 3 rows grid
- Full-width health checks and bad smells

### Mobile (<768px)
- Metrics: 1 column × 6 rows stack
- Full-width health checks and bad smells
- Reduced padding

## Empty States

### No Bad Smells
```
Bad Smells section is hidden completely when no issues detected
```

### No Health Checks
```
Health Checks
━━━━━━━━━━━━━━━━━━
No health checks available
```

### Loading State
```
┌─────────────────────────────────────┐
│         Loading health data...       │
│              [Spinner]              │
└─────────────────────────────────────┘
```

### Error State
```
┌─────────────────────────────────────┐
│              ⚠️                      │
│    Failed to load health data        │
│    Error: Connection timeout         │
└─────────────────────────────────────┘
```

## Typography

### Headings
- View Title: 18px, Semi-bold
- Section Titles: 16px, Semi-bold
- Metric Labels: 12px, Bold, Uppercase
- Health Check Names: 14px, Semi-bold

### Content
- Metric Values: 32px, Bold, Monospace
- Metric Status: 13px, Medium
- Health Check Messages: 13px, Regular
- Bad Smell Details: 13px, Regular
- Suggestions: 13px, Regular

## Icons

### Status Icons (Material Icons)
- OK: `check_circle` (green circle with checkmark)
- WARN: `warning` (yellow triangle with exclamation)
- ERROR: `error` (red circle with X)
- INFO: `info` (blue circle with i)

### Navigation Icon
- Checkmark in circle (for sidebar)

### Action Icons
- Refresh: Circular arrows

### Suggestion Icon
- Light bulb emoji: 💡

## Spacing

- **View Padding**: 24px
- **Metric Grid Gap**: 20px
- **Section Margin**: 32px between sections
- **Card Padding**: 20px
- **Card Margin**: 16px between cards
- **Item Padding**: 16px
- **Icon Gap**: 16px between icon and content

## Animation

- **Metric Card Hover**: Transform translateY(-2px), duration 0.2s
- **Metric Card Shadow**: Box-shadow increase on hover
- **All Transitions**: ease-in-out timing
